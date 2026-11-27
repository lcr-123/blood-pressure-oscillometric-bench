"""Report the covered-estimator score pool split by provenance tier.

Why this exists
    2026-11-25 the pre-registered cross-day batch (`crosstday`, 266 rounds) landed in
    data/raw/, and `tools/covered_bp.py --score` uses a glob, not a tier filter, so its
    default run now sweeps those rounds into the same pooled statistics as the older
    development rounds. The cross-day batch is judged by the T0..T4 rules in
    data/protocols/reference_bp_batch_crosstday_v1.md, and that protocol forbids folding
    it into a frozen statistic. Reporting one number for "the pool" would quietly mix two
    things that must stay apart, so this script prints them separately and refuses to
    print a single combined coverage figure.

    It runs no estimator of its own: it either reads an existing `covered_bp --score`
    JSON or asks `covered_bp.score()` for one, then partitions the rows by the tier map
    that `tools/dataset_tiers.py` derives. Nothing here can change a frozen constant.

Usage
    python tools\\covered_bp.py --score --json tmp\\covered.json
    python tools\\score_by_tier.py --score-json tmp\\covered.json
    python tools\\score_by_tier.py                        # score from scratch (slow)
    python tools\\score_by_tier.py --score-json tmp\\covered.json --json tmp\\by_tier.json
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dataset_tiers  # noqa: E402

FIELDS = ("map_mmhg", "sbp_mmhg", "dbp_mmhg")
AAMI_MEAN = 5.0
AAMI_SD = 8.0


def stats(values):
    if not values:
        return None
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
    }


def report(label, rows, note):
    print(f"\n== {label}: {len(rows)} scored round(s)")
    print(f"   {note}")
    pooled = {}
    for field in FIELDS:
        pooled[field] = stats([r["error_mmhg"][field] for r in rows])
        entry = pooled[field]
        if entry is None:
            continue
        flag = "PASS" if abs(entry["mean"]) <= AAMI_MEAN and entry["sd"] <= AAMI_SD else "fail"
        print(f"   {field:10} n={entry['n']:4d}  mean {entry['mean']:+6.2f}  "
              f"sd {entry['sd']:5.2f}  {flag}")
    by_preset = {}
    for row in rows:
        by_preset.setdefault(str(row["preset"]), []).append(row)
    passing = []
    per_preset = {}
    for preset in sorted(by_preset):
        members = by_preset[preset]
        cells = {}
        ok = True
        for field in FIELDS:
            entry = stats([r["error_mmhg"][field] for r in members])
            good = (entry is not None and abs(entry["mean"]) <= AAMI_MEAN
                    and entry["sd"] <= AAMI_SD)
            ok = ok and good
            cells[field] = {**(entry or {}), "aami_pass": good}
        if ok:
            passing.append(preset)
        per_preset[preset] = {"rounds": len(members), "cells": cells, "all_pass": ok}
        print(f"   P{preset} n={len(members):3d}  " + "  ".join(
            f"{f[:3].upper()} {cells[f]['mean']:+5.2f}/{cells[f]['sd']:5.2f} "
            f"{'P' if cells[f]['aami_pass'] else 'f'}" for f in FIELDS))
    print(f"   presets passing all three: {len(passing)}/7 {passing}")
    return {"label": label, "note": note, "rounds": len(rows), "pooled": pooled,
            "per_preset": per_preset, "presets_all_pass": passing}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--score-json", help="reuse an existing covered_bp --score JSON")
    parser.add_argument("--json", help="write the split as JSON here")
    parser.add_argument("--tier", action="append", choices=dataset_tiers.TIER_ORDER,
                        help="restrict the report to these tiers (repeatable)")
    args = parser.parse_args(argv)

    tiers = dataset_tiers.collect()
    tier_of = {row["run_id"]: row["tier"] for row in tiers}
    tainted = [row["run_id"] for row in tiers if row["run_id"] not in tier_of]
    if tainted:  # defensive: collect() derives the tier for every round it walks
        raise SystemExit(f"{len(tainted)} round(s) have no tier")

    if args.score_json:
        score = json.loads(Path(args.score_json).read_text(encoding="utf-8"))
        if "rows" not in score:
            raise SystemExit(f"{args.score_json} is not a covered_bp --score JSON "
                             f"(no 'rows' key)")
    else:
        import covered_bp  # noqa: E402 - imported late so --score-json stays fast
        pattern = str(covered_bp.RAW / "standard*_target275*.export.ndjson")
        score = covered_bp.score(sorted(glob.glob(pattern)))

    rows = [r for r in score["rows"] if r["status"] == "ok" and "error_mmhg" in r]
    unknown = [r["run_id"] for r in rows if r["run_id"] not in tier_of]
    if unknown:
        print(f"warning: {len(unknown)} scored round(s) are not in the tier map "
              f"(e.g. {unknown[:3]})", file=sys.stderr)

    groups = {}
    for row in rows:
        groups.setdefault(tier_of.get(row["run_id"], "unknown"), []).append(row)

    want = args.tier or dataset_tiers.TIER_ORDER
    print(f"scored ok rows: {len(rows)}; tiers present: "
          f"{ {k: len(v) for k, v in sorted(groups.items())} }")

    blocks = []
    cross = sum(len(v) for k, v in groups.items() if k == "crosstday")
    rest = [r for k, v in groups.items() if k != "crosstday" for r in v]
    if "crosstday" in want and cross:
        blocks.append(report(
            "cross-day batch alone", groups["crosstday"],
            "judged by the T0..T4 rules, never folded into a frozen statistic"))
    if cross and rest:
        blocks.append(report(
            "everything except the cross-day batch", rest,
            "the pool the pre-2026-11-16 reports were computed on"))
    for tier in want:
        if tier == "crosstday" or tier not in groups:
            continue
        if cross:
            continue
        blocks.append(report(f"tier {tier}", groups[tier], ""))

    if cross:
        print("\nNOTE: the combined pool is deliberately not reported. The cross-day "
              "batch and the development rounds answer different questions and "
              "data/protocols/reference_bp_batch_crosstday_v1.md forbids merging them. "
              "Quote one of the two blocks above, with its round count.")

    if args.json:
        payload = {"corpus": str(dataset_tiers.RAW), "scored_ok": len(rows),
                   "tiers_in_score": {k: len(v) for k, v in sorted(groups.items())},
                   "blocks": blocks}
        out = Path(args.json)
        if not out.is_absolute():
            out = ROOT / out
        data = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        out.write_bytes(data.encode("utf-8"))
        print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
