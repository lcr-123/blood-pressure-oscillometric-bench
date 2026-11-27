"""Reproducible, read-only audit of retained verified BP captures."""

import argparse
import hashlib
from pathlib import Path
import re

from bp_capture import decode, float32
from bp_oscillogram_study import analyze


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GLOB = "tmp/capture_export_*.verified.ndjson"


def dbp_crossing(capture):
    """Locate the production C first three-point 60% crossing after MAP."""
    if capture["header"]["calc"] not in (2, 3):
        return None
    points = capture["points"]
    features = capture["features"]
    if not features["dbp_found"]:
        return None
    map_i = features["map_i"]
    peak = float32(points[map_i]["s"])
    tail_skip = 15 if len(points) > 30 else 0
    for i in range(map_i + 1, len(points) - tail_skip):
        pressure = float32(points[i]["p"])
        if pressure < 12.0:
            break
        if i + 2 < len(points) and all(
            float32(points[j]["s"]) <= 0.6 * peak for j in range(i, i + 3)
        ):
            if points[i]["p"] != features["dbp_p"]:
                raise ValueError("DBP crossing disagrees with exported feature")
            return i
    raise ValueError("exported DBP feature has no matching crossing")


def inspect(path):
    raw = path.read_bytes()
    capture = decode(raw.decode("utf-8-sig").splitlines())
    header = capture["header"]
    features = capture["features"]
    upper = 170 if float32(capture["points"][0]["p"]) >= 150 else 130
    study = analyze(capture, 40, upper)
    height = study.get("height", {})
    robustness = height.get("robustness", {})
    dbp_i = dbp_crossing(capture)
    map_i = features["map_i"] if header["calc"] in (2, 3) else None
    return {
        "id": path.stem.split("_")[-1].split(".")[0],
        "sha256": hashlib.sha256(raw).hexdigest(),
        "n": header["n"],
        "calc": header["calc"],
        "upper": upper,
        "map": float32(features["map_p"]) if map_i is not None else None,
        "dbp": float32(features["dbp_p"]) if dbp_i is not None else None,
        "gap_s": ((capture["points"][dbp_i]["t"] -
                   capture["points"][map_i]["t"]) & 0xFFFFFFFF) / 1000
        if dbp_i is not None else None,
        "study": study["status"],
        "screen": robustness.get("screen"),
        "reasons": robustness.get("reasons", []),
        "peak": height.get("gaussian", {}).get("peak_mmhg"),
    }


def cell(value, digits=None):
    if value is None:
        return "-"
    return f"{value:.{digits}f}" if digits is not None else str(value)


def report(rows, through=None):
    complete = [row for row in rows if row["gap_s"] is not None]
    near = [row for row in complete if row["gap_s"] <= 0.75]
    valid = [row for row in complete if row["calc"] == 2]
    invalid = [row for row in complete if row["calc"] == 3]
    calculated = [row for row in rows if row["calc"] in (2, 3)]
    lines = [
        "# Retained BP capture batch audit",
        "",
        "This is a retrospective, simulator-only exploration. These captures were used",
        "during method development and are **not** an independent held-out set.",
        "Panel settings are not encoded in the export; do not infer labels from filenames.",
        "Fitted peaks are diagnostic candidates, not reference MAP or clinical BP.",
        "",
        "Run from the repository root:",
        "",
        "```powershell",
        "python 'blood pressure monitor/tools/bp_capture_batch_report.py' " +
        (f"--through {through} " if through else "") +
        "--output '.trellis/tasks/06-19-bp-firmware-bringup/capture-batch-audit.md'",
        "```",
        "",
        "Inputs: `tmp/capture_export_*.verified.ndjson`, sorted by path" +
        (f", through `{through}` inclusive." if through else "."),
        "Each input passes the strict `bp_capture.decode` count/order/FNV check.",
        "SHA-256 below identifies the exact input bytes. `upper=170` when the first cuff pressure",
        "is >=150 mmHg, otherwise 130; step padding=40 samples (1 s). The study",
        "uses the existing exploratory beat-height and robustness settings.",
        "MAP/DBP values are raw firmware features before fixed output offsets.",
        "DBP time is the first three-sample <=60% smoothed-envelope crossing",
        "after MAP, using MCU ticks. `calc=2` means firmware valid, `3` invalid,",
        "and `0` uncalculated; it is independent of the study screen.",
        "",
        f"Total: {len(rows)} complete verified exports; calculated {len(calculated)} "
        f"(valid {sum(row['calc'] == 2 for row in calculated)}, "
        f"invalid {sum(row['calc'] == 3 for row in calculated)}), "
        f"uncalculated {sum(row['calc'] == 0 for row in rows)}.",
        f"MAP-to-DBP <=0.75 s: {len(near)}/{len(complete)} with DBP found; "
        f"firmware valid {sum(row['calc'] == 2 for row in near)}/{len(valid)}, "
        f"invalid with DBP {sum(row['calc'] == 3 for row in near)}/{len(invalid)}.",
        f"DBP raw pressure > MAP: {sum(row['dbp'] > row['map'] for row in complete)} "
        "captures. These counts describe this selected archive only; 0.75 s",
        "is one beat at 80 BPM, not a validated rejection threshold.",
        "",
        "| Export | SHA-256 | n | calc | upper | MAP | DBP | gap s | study | screen | fitted peak | reasons |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |",
    ]
    for row in rows:
        lines.append("| " + " | ".join((
            row["id"], row["sha256"], str(row["n"]), str(row["calc"]),
            str(row["upper"]), cell(row["map"], 2), cell(row["dbp"], 2),
            cell(row["gap_s"], 3), row["study"], cell(row["screen"]),
            cell(row["peak"], 2), ", ".join(row["reasons"]) or "-",
        )) + " |")
    lines += [
        "",
        "## Interpretation",
        "",
        "A near-immediate DBP threshold crossing appears in both firmware-valid and",
        "firmware-invalid captures. The production `DBP > MAP` gate explains the",
        "invalid flags where pressure ripples reverse the raw feature ordering,",
        "but passing that gate does not establish a multi-beat falling envelope.",
        "The independent beat-height screen and firmware validity answer different",
        "questions; neither supplies a reference pressure trace or clinical truth.",
        "Do not fit firmware MAP bounds, ratios, or offsets to this archive.",
        "A separately collected and frozen set with known panel settings and",
        "independent pressure evidence is needed before selecting a new algorithm.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write deterministic Markdown report")
    parser.add_argument("--through", help="inclusive export ID YYYYMMDD-HHMMSS")
    args = parser.parse_args()
    if args.through and not re.fullmatch(r"\d{8}-\d{6}", args.through):
        parser.error("--through must be an export ID YYYYMMDD-HHMMSS")
    paths = sorted(ROOT.glob(DEFAULT_GLOB))
    if args.through:
        paths = [path for path in paths if path.stem.split("_")[-1].split(".")[0] <= args.through]
    if not paths:
        parser.error(f"no inputs match {DEFAULT_GLOB}")
    rows = [inspect(path) for path in paths]
    result = report(rows, args.through)
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
