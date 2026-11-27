"""Classify every captured round into a provenance tier.

The raw directory now holds several very different kinds of round, and until now
nothing in the repository said which was which:

  frozen_baseline_v2   18 rounds used to choose the frozen constants
  prospective_v1       20 rounds, first prospective batch (presets 1 and 2)
  prospective_v2       20 rounds, second prospective batch (presets 3 and 4)
  v3_acceptance        40 rounds, the pre-registered acceptance test for v3
  crosstday            266 rounds, the pre-registered 10 day x 7 preset cross-day batch
  supplementary        extra rounds on the current firmware, in no protocol
  legacy_firmware      rounds captured before PEAK_WINDOW_20261105

Tier membership is derived from the frozen records, the score reports and the
batch tags the orchestrator stamps into each round's metadata, never typed in by
hand, so a new capture cannot silently join a tier that has already been used
for scoring. Anything not named by a protocol falls into supplementary or
legacy_firmware by firmware generation.

There is a second, narrower set that also has to be derivable: the 62 rounds the
published tables are computed from. Those are the three protocol tiers plus the
supplementary rounds captured before the v3 pre-registration, which is the moment
the corpus stopped being open. `published_corpus` marks exactly that set; it is
what `data/README.md` and `data/reports/dataset_scope_statement.md` quote.

Usage:
    python tools\\dataset_tiers.py                       # table
    python tools\\dataset_tiers.py --json out.json       # machine readable
    python tools\\dataset_tiers.py --write-metadata       # stamp dataset_tier
    python tools\\dataset_tiers.py --tier v3_acceptance --list
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "data" / "reports"
PROTOCOLS = ROOT / "data" / "protocols"

FIRMWARE = "PEAK_WINDOW_20261105"

# The instant the v3 acceptance test was pre-registered. Every round captured after
# this belongs to the test batch and may not be counted inside a published table.
PUBLISHED_AT = "2026-11-11T09:49:47"
PUBLISHED_SOURCE = "the commit that froze v3 (5066fc5)"

TIER_ORDER = [
    "frozen_baseline_v2",
    "prospective_v1",
    "prospective_v2",
    "v3_acceptance",
    "crosstday",
    "supplementary",
    "legacy_firmware",
]

TIER_NOTES = {
    "frozen_baseline_v2": "development set; the frozen constants were chosen on these, "
                          "so they can never validate them",
    "prospective_v1": "one-shot prospective batch scored against freeze v1",
    "prospective_v2": "one-shot prospective batch scored against freeze v2",
    "v3_acceptance": "the 40 pre-registered rounds that decided against v3",
    "crosstday": "the pre-registered 10 day x 7 preset cross-day batch "
                 "(data/protocols/reference_bp_batch_crosstday_v1.md); judged by "
                 "tools/validity_v2.py + the T0..T4 rules, never inside a frozen statistic",
    "supplementary": "captured on the current firmware outside any protocol; "
                     "reported separately, never inside a frozen statistic",
    "legacy_firmware": "captured before PEAK_WINDOW_20261105; different firmware, "
                       "different BP algorithm, not comparable",
}

# Tiers that a frozen statistic is allowed to be computed from. The cross-day batch
# is a protocol too, but its verdict is produced by the T0..T4 rules on top of
# tools/validity_v2.py, not by freezing constants on it, so it stays out of this set
# and out of `published_corpus`.
PROTOCOL_TIERS = ("frozen_baseline_v2", "prospective_v1", "prospective_v2")
SCORED_TIERS = ("prospective_v1", "prospective_v2")

# The batch tag the cross-day orchestrator stamps into every round it keeps.
CROSSTDAY_TAG = "crosstday"

# Preset columns shown in the summary table. Presets 5, 6 and 7 were only captured
# on 2026-11-13, so the columns appear once a row has one.
PRESET_COLUMNS = (1, 2, 3, 4, 5, 6, 7)


def _strip(name: str) -> str:
    return name[: -len(".export.ndjson")] if name.endswith(".export.ndjson") else name


def _baseline_runs() -> set[str]:
    path = PROTOCOLS / "reference_bp_freeze_v2.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    out = set()
    for item in record["baseline_rounds"]:
        out.add(item["run"] if isinstance(item, dict) else item)
    return out


def _prospective_v1_runs() -> set[str]:
    path = REPORTS / "reference_bp_prospective_v1.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {_strip(Path(item["export"]).name) for item in data if item.get("export")}


def _prospective_v2_runs() -> set[str]:
    path = REPORTS / "reference_bp_prospective_v2.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["run"] for item in data["rounds"] if item.get("run")}


def _v3_runs() -> set[str]:
    path = REPORTS / "reference_bp_v3_validation.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["run_id"] for item in data["rows"] if item.get("run_id")}


def _declared() -> dict[str, str]:
    """run_id -> tier, from the four authoritative records."""
    out: dict[str, str] = {}
    for tier, getter in (
        ("frozen_baseline_v2", _baseline_runs),
        ("prospective_v1", _prospective_v1_runs),
        ("prospective_v2", _prospective_v2_runs),
        ("v3_acceptance", _v3_runs),
    ):
        for run in getter():
            if run in out:
                raise SystemExit(f"{run} is declared in two tiers: {out[run]} and {tier}")
            out[run] = tier
    return out


def preset_of(run_id: str) -> int | None:
    """standard120_080_... -> 1.  The diastolic field is zero padded to three."""
    head = run_id.split("_")
    if len(head) < 2 or not head[0].startswith("standard"):
        return None
    key = f"{head[0][len('standard'):]}_{head[1]}"
    return {
        "120_080": 1, "150_100": 2, "200_150": 3, "255_195": 4,
        "060_030": 5, "080_050": 6, "100_065": 7,
    }.get(key)


def captured_at(run_id: str) -> datetime | None:
    """Every run id ends with _YYYYMMDD-HHMMSS in local time.

    The underscore split has to be the last one: `standard255_195_target275_
    peakwindow_20261111-101458` -> `20261111-101458`. Splitting on the hyphen
    instead yields `101458` and silently loses the date.
    """
    tail = str(run_id).rsplit("_", 1)[-1]
    if "-" not in tail:
        return None
    day, clock = tail.split("-", 1)
    try:
        return datetime.strptime(day + clock, "%Y%m%d%H%M%S")
    except ValueError:
        return None


def in_published_corpus(row: dict) -> bool:
    """True for the rounds the published tables are allowed to quote.

    Three protocol tiers plus the supplementary rounds captured before v3 was
    pre-registered. A supplementary round after that instant is part of the test
    batch and cannot be used to describe the corpus.
    """
    tier = row["tier"]
    if tier in PROTOCOL_TIERS:
        return True
    if tier != "supplementary":
        return False
    stamp = captured_at(row["run_id"])
    return stamp is not None and stamp < datetime.fromisoformat(PUBLISHED_AT)


def collect() -> list[dict]:
    declared = _declared()
    rows = []
    for path in sorted(RAW.rglob("*.export.ndjson")):
        run = _strip(path.name)
        with path.open(encoding="utf-8") as handle:
            begin = json.loads(handle.readline())
        meta_path = path.with_name(run + ".metadata.json")
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        firmware = begin.get("firmware")
        batch_tag = meta.get("batch_tag") or ""

        tier = declared.get(run)
        reason = "declared by a frozen protocol or score report"
        if tier is None:
            if firmware != FIRMWARE:
                tier = "legacy_firmware"
                reason = f"firmware {firmware} predates {FIRMWARE}"
            elif batch_tag == CROSSTDAY_TAG:
                tier = "crosstday"
                reason = ("declared by data/protocols/reference_bp_batch_crosstday_v1.md "
                          "via the batch_tag the orchestrator stamps into the metadata")
            else:
                tier = "supplementary"
                reason = "current firmware round not named by any protocol"

        row = {
            "run_id": run,
            "tier": tier,
            "tier_reason": reason,
            "preset": preset_of(run),
            "captured_at": (captured_at(run).isoformat() if captured_at(run) else None),
            "firmware": firmware,
            "batch_tag": batch_tag,
            "n": begin.get("n"),
            "interval_ms": begin.get("interval_ms"),
            "dropped": begin.get("dropped"),
            "cal_valid": begin.get("cal_valid"),
            "dataset_role": meta.get("dataset_role"),
            "batch_day": meta.get("batch_day"),
            "wrap_block": meta.get("wrap_block"),
            "outcome": meta.get("outcome"),
            "panel_sbp_mmhg": meta.get("panel_sbp_mmhg"),
            "panel_dbp_mmhg": meta.get("panel_dbp_mmhg"),
            "panel_map_mmhg": meta.get("panel_map_mmhg"),
            "export": str(path.relative_to(ROOT)),
        }
        row["published_corpus"] = in_published_corpus(row)
        rows.append(row)
    rows.sort(key=lambda r: (TIER_ORDER.index(r["tier"]), r["preset"] or 99, r["run_id"]))
    return rows


def summarise(rows: list[dict]) -> dict:
    out = {}
    for tier in TIER_ORDER:
        members = [r for r in rows if r["tier"] == tier]
        by_preset = {}
        for r in members:
            key = str(r["preset"]) if r["preset"] else "unknown"
            by_preset[key] = by_preset.get(key, 0) + 1
        out[tier] = {
            "rounds": len(members),
            "by_preset": dict(sorted(by_preset.items())),
            "firmware": sorted({r["firmware"] for r in members if r["firmware"]}),
            "note": TIER_NOTES[tier],
        }
    return out


def published_summary(rows: list[dict]) -> dict:
    """The narrower set the published tables quote, plus what was left out."""
    inside = [r for r in rows if r.get("published_corpus")]
    by_preset = {}
    for r in inside:
        key = str(r["preset"]) if r["preset"] else "unknown"
        by_preset[key] = by_preset.get(key, 0) + 1
    outside = [r for r in rows if not r.get("published_corpus")]
    return {
        "rounds": len(inside),
        "by_preset": dict(sorted(by_preset.items())),
        "source": f"three protocol tiers plus supplementary rounds captured before "
                  f"{PUBLISHED_AT} ({PUBLISHED_SOURCE})",
        "excluded_rounds": len(outside),
        "excluded_by_tier": {
            tier: sum(1 for r in outside if r["tier"] == tier)
            for tier in TIER_ORDER
            if any(r["tier"] == tier for r in outside)
        },
    }


def table(rows: list[dict]) -> str:
    summary = summarise(rows)
    presets = [p for p in PRESET_COLUMNS
               if any(summary[t]["by_preset"].get(str(p), 0) for t in TIER_ORDER)]
    header = "| tier | rounds | " + " | ".join(f"p{p}" for p in presets)
    lines = [
        header + " | in published tables | what it is for |",
        "|---" * (len(presets) + 4) + "|",
    ]
    for tier in TIER_ORDER:
        info = summary[tier]
        cells = [str(info["by_preset"].get(str(p), 0)) for p in presets]
        inside = sum(1 for r in rows if r["tier"] == tier and r.get("published_corpus"))
        lines.append(
            f"| `{tier}` | {info['rounds']} | " + " | ".join(cells)
            + f" | {inside} | {info['note']} |"
        )
    total = sum(summary[t]["rounds"] for t in TIER_ORDER)
    inside_total = sum(1 for r in rows if r.get("published_corpus"))
    lines.append(f"| **total** | **{total}** | " + " | ".join("" for _ in presets)
                 + f" | **{inside_total}** | |")
    return "\n".join(lines)


def stamp_metadata(rows: list[dict]) -> int:
    changed = 0
    for row in rows:
        path = ROOT / row["export"]
        meta_path = path.with_name(row["run_id"] + ".metadata.json")
        if not meta_path.exists():
            continue
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("dataset_tier") == row["tier"]:
            continue
        meta["dataset_tier"] = row["tier"]
        meta["dataset_tier_reason"] = row["tier_reason"]
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
            encoding="utf-8", newline="\n",
        )
        changed += 1
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", help="write the full manifest here")
    parser.add_argument("--write-metadata", action="store_true",
                        help="stamp dataset_tier into every metadata file")
    parser.add_argument("--tier", action="append", choices=TIER_ORDER,
                        help="restrict output to these tiers (repeatable)")
    parser.add_argument("--list", action="store_true", help="list rounds, not just counts")
    args = parser.parse_args(argv)

    rows = collect()
    published = published_summary(rows)
    if args.tier:
        rows = [r for r in rows if r["tier"] in args.tier]

    print(table(rows))
    print()

    print(f"published corpus: {published['rounds']} round(s) "
          f"({published['source']})")
    print(f"  excluded: {published['excluded_rounds']} round(s) "
          f"{published['excluded_by_tier']}")
    print()

    if args.list:
        for row in rows:
            mark = "*" if row.get("published_corpus") else " "
            print(f"{mark} {row['tier']:20} P{row['preset']}  {row['run_id']}")
        print()

    if args.write_metadata:
        print(f"stamped {stamp_metadata(rows)} metadata file(s)")

    if args.json:
        out = Path(args.json)
        if not out.is_absolute():
            out = ROOT / out
        payload = {
            "firmware_current": FIRMWARE,
            "protocol_tiers": list(PROTOCOL_TIERS),
            "scored_tiers": list(SCORED_TIERS),
            "tier_notes": TIER_NOTES,
            "published_at": PUBLISHED_AT,
            "published_at_source": PUBLISHED_SOURCE,
            "published_corpus": published,
            "summary": summarise(rows),
            "rounds": rows,
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
        print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
