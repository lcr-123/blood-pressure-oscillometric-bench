"""Turn a v4 batch manifest into k-capture medians and judge acceptance criteria C1..C4.

The measurement unit being tested (data/protocols/reference_bp_freeze_v4_candidate.md §2):

    one measurement := the median of k = 4 consecutive captures in the same session,
                       computed separately for SBP, DBP and MAP.

This tool reads the manifest written by tmp/run_v4_batch.py, scores each capture with
the frozen estimator (tools/reference_bp.py, unchanged) after the frozen gate
(tools/validity_v2.py, unchanged), assembles non-overlapping groups of k in recording
order, and prints:

  * the k = 1 numbers on the SAME captures, which is what C2 and C3 compare against;
  * the k-capture median numbers, then C1..C4 verdicts.

Two rules are applied exactly as pre-registered:

  * a capture refused by the estimator is still a capture: it contributes no value for
    the quantity it refused, so the group takes its median from the remaining values
    (the pre-registration's "fill from the next qualifying capture" rule is applied by
    the batch runner, which keeps capturing until enough good rounds exist);
  * a capture excluded by the gate (or by decode) is dropped before grouping, and the
    group is assembled from the rest in order.

Usage:
    python tools/median_groups.py --manifest tmp/omniprobe/v4_p1_manifest.json --k 4
    python tools/median_groups.py --manifest ... --k 4 --json data/reports/v4_p1_groups.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import reference_bp  # noqa: E402
import validity_v2  # noqa: E402
from measurement_precision import upper_bound  # noqa: E402

QUANTITIES = (("sbp", "SBP", "panel_sbp"), ("dbp", "DBP", "panel_dbp"), ("map", "MAP", "panel_map"))
AAMI_SD_LIMIT = 8.0
C2_MIN_IMPROVEMENT = 1.0
C3_MAX_DRIFT = 1.0
C4_MIN_RATE = 0.9


def _fmt(values: list[float]) -> str:
    return " ".join(f"{value:+.1f}" for value in values)


def summarise(values: list[float]) -> dict:
    if len(values) < 2:
        return {"n": len(values)}
    sd = statistics.stdev(values)
    return {"n": len(values), "mean": statistics.fmean(values), "sd": sd,
            "median": statistics.median(values), "upper95": upper_bound(sd, len(values)),
            "min": min(values), "max": max(values)}


def load_rows(manifest_path: Path) -> tuple[dict, list[dict], list[dict]]:
    """Score every kept capture; return (manifest, scored rows, dropped rows)."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scored, dropped = [], []
    for entry in manifest["rounds"]:
        run_id = entry.get("run_id")
        if not run_id:
            dropped.append(dict(entry, drop_reason=entry.get("outcome", "no run_id")))
            continue
        export = ROOT / "data" / "raw" / "development_20261101" / f"{run_id}.export.ndjson"
        if not export.is_file():
            dropped.append(dict(entry, drop_reason="export missing"))
            continue
        gate = validity_v2.check(str(export))
        if not gate["usable"]:
            dropped.append(dict(entry, drop_reason="gate: " + ", ".join(gate["reasons"])))
            continue
        result = reference_bp.estimate(reference_bp.load(export))
        row = {"run_id": run_id, "status": result["status"], "gate": "USABLE",
               "peak_slope": gate.get("peak_window_slope_mmhg_s")}
        for key, _label, panel_key in QUANTITIES:
            panel = manifest[panel_key]
            if key == "map":
                value = None if result["status"].startswith("unresolved_map") else result["map_mmhg"] - panel
            else:
                ok = result["status"] == "ok"
                value = (result[f"{key}_mmhg"] - panel) if ok else None
            row[key] = value
        scored.append(row)
    return manifest, scored, dropped


def load_batches(manifest_paths: list[Path]) -> tuple[dict, list[dict], list[dict], list[str]]:
    """Score several manifests in the order given and concatenate their captures.

    A batch that was interrupted (bad zero, unplugged cable) and restarted under a new
    tag keeps the same panel preset and the same session, so the pre-registration's
    "k consecutive captures" rule can span the two manifests. The tags are returned so
    the report can state exactly which sessions the number came from -- a reader must
    be able to see that the groups did not silently cross a panel change.
    """
    if len(manifest_paths) == 1:
        manifest, scored, dropped = load_rows(manifest_paths[0])
        return manifest, scored, dropped, [manifest.get("tag")]
    scored, dropped, tags = [], [], []
    first = None
    for path in manifest_paths:
        manifest, part_scored, part_dropped = load_rows(path)
        if first is None:
            first = manifest
        elif (manifest.get("preset"), manifest.get("panel_sbp"), manifest.get("panel_dbp"),
              manifest.get("panel_map")) != (first.get("preset"), first.get("panel_sbp"),
                                             first.get("panel_dbp"), first.get("panel_map")):
            raise SystemExit(f"{path} has a different panel setting than {manifest_paths[0]}; "
                             "k-capture groups must not span a panel change")
        tags.append(manifest.get("tag"))
        scored.extend(part_scored)
        dropped.extend(part_dropped)
    return first, scored, dropped, tags


def group(values: list[float], k: int) -> list[float]:
    """Non-overlapping groups of k consecutive values; each group becomes its median."""
    out = []
    for start in range(0, len(values) - k + 1, k):
        out.append(statistics.median(values[start:start + k]))
    return out


def analyse(manifest: dict, scored: list[dict], dropped: list[dict], k: int,
            tags: list[str] | None = None) -> dict:
    report = {"manifest": manifest.get("tag"), "manifests": tags or [manifest.get("tag")],
              "preset": manifest.get("preset"),
              "k": k, "captures_scored": len(scored), "captures_dropped": len(dropped),
              "dropped": [{"attempt": row.get("attempt"), "run_id": row.get("run_id"),
                           "reason": row.get("drop_reason")}
                          for row in dropped],
              "criteria": {}, "quantities": {}}

    for key, label, _panel in QUANTITIES:
        single = [row[key] for row in scored if row[key] is not None]
        grouped = group(single, k)
        single_stats = summarise(single)
        group_stats = summarise(grouped)
        report["quantities"][label] = {"k1": single_stats, "kgroup": group_stats,
                                       "groups": [round(v, 2) for v in grouped]}

        if "sd" not in group_stats or "sd" not in single_stats:
            report["criteria"][f"{label}_C1"] = "NOT EVALUABLE (fewer than 2 groups)"
            continue
        report["criteria"][f"{label}_C1"] = (
            "PASS" if group_stats["upper95"] <= AAMI_SD_LIMIT else
            f"FAIL (upper95 {group_stats['upper95']:.2f} > {AAMI_SD_LIMIT})")
        improvement = single_stats["sd"] - group_stats["sd"]
        report["criteria"][f"{label}_C2"] = (
            "PASS" if improvement >= C2_MIN_IMPROVEMENT else
            f"FAIL (sd only {improvement:+.2f} lower, need >= {C2_MIN_IMPROVEMENT})")
        drift = abs(group_stats["mean"]) - abs(single_stats["mean"])
        report["criteria"][f"{label}_C3"] = (
            "PASS" if drift <= C3_MAX_DRIFT else
            f"FAIL (|mean| worse by {drift:+.2f}, limit {C3_MAX_DRIFT})")

    participating = len(scored)
    published = sum(1 for row in scored if row["status"] == "ok")
    rate = (published / participating) if participating else 0.0
    report["criteria"]["C4"] = (
        "PASS" if rate >= C4_MIN_RATE else
        f"FAIL (only {published}/{participating} = {rate:.2f} published, need >= {C4_MIN_RATE})")
    report["published_rate"] = {"published": published, "participating": participating,
                                "rate": round(rate, 3)}

    verdicts = [value for value in report["criteria"].values()]
    report["verdict"] = ("PASS: k-capture median meets C1..C4" if all(v == "PASS" for v in verdicts)
                         else "FAIL: " + "; ".join(f"{k_}={v}" for k_, v in report["criteria"].items()
                                                   if v != "PASS"))
    return report


def print_report(report: dict) -> None:
    k = report["k"]
    print(f"== {report['manifest']}  preset {report['preset']}  k={k}")
    if len(report.get("manifests") or []) > 1:
        print(f"   manifests merged in this order: {', '.join(report['manifests'])}")
    print(f"   scored {report['captures_scored']} capture(s), dropped {report['captures_dropped']}")
    for item in report["dropped"]:
        who = item.get("run_id") or f"attempt {item.get('attempt')}"
        print(f"   dropped {who}: {item['reason']}")
    print()
    print(f"   {'qty':4s} {'':6s} {'n':>4s} {'mean':>8s} {'sd':>7s} {'upper95':>8s} {'median':>8s}")
    for label, data in report["quantities"].items():
        for which, title in (("k1", "k=1"), ("kgroup", f"k={k}")):
            stats = data[which]
            if "sd" not in stats:
                print(f"   {label:4s} {title:6s} {stats['n']:>4d}   (too few)")
                continue
            print(f"   {label:4s} {title:6s} {stats['n']:>4d} {stats['mean']:>+8.2f} "
                  f"{stats['sd']:>7.2f} {stats['upper95']:>8.2f} {stats['median']:>+8.2f}")
    print()
    for name, verdict in report["criteria"].items():
        print(f"   {name:8s} {verdict}")
    print()
    print("   " + report["verdict"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True, action="append",
                        help="repeat to merge several batches of the same panel preset, in order")
    parser.add_argument("--k", type=int, default=4)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    manifest, scored, dropped, tags = load_batches([RESOLVE(p) for p in args.manifest])
    report = analyse(manifest, scored, dropped, args.k, tags)
    print_report(report)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")
        print(f"\n   wrote {args.json}")
    return 0 if report["verdict"].startswith("PASS") else 1


def RESOLVE(path: Path) -> Path:
    return path if path.is_absolute() else (ROOT / path)


if __name__ == "__main__":
    sys.exit(main())
