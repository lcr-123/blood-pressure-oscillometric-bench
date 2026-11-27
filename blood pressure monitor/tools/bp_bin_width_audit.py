"""Read-only 5/10 mmHg pressure-bin sensitivity audit of retained captures."""

import argparse
import hashlib
import json
from pathlib import Path

from bp_capture import decode, float32
from bp_oscillogram_study import analyze


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CATALOG = ROOT / "data/reports/capture_catalog_20261031.json"
DEFAULT_OUTPUT = ROOT / "data/reports/offline_bin_width_20261101.json"


def summarize_feature(result, key):
    feature = result.get(key, {})
    robustness = feature.get("robustness", {})
    fit = feature.get("gaussian", {})
    return {"status": feature.get("status"), "screen": robustness.get("screen"),
            "reasons": robustness.get("reasons", []),
            "peak_bin_beats": robustness.get("peak_bin_beats"),
            "peak_mmhg": fit.get("peak_mmhg"), "r2": fit.get("r2")}


def audit(catalog_path, selection_paths):
    catalog_bytes = catalog_path.read_bytes()
    catalog = json.loads(catalog_bytes.decode("utf-8-sig"))
    historical = [(ROOT / row["path"], "historical_development")
                  for row in catalog["files"]
                  if row["status"] == "decode_valid" and row["duplicate_of"] is None]
    inputs = historical + [(path, "rule_selection_20261101") for path in selection_paths]
    rows = []
    for path, group in inputs:
        raw = path.read_bytes()
        capture = decode(raw.decode("utf-8-sig").splitlines())
        upper = 170 if float32(capture["points"][0]["p"]) >= 150 else 130
        try:
            display_path = path.relative_to(ROOT).as_posix()
        except ValueError:
            display_path = path.as_posix()
        row = {"path": display_path, "group": group,
               "sha256": hashlib.sha256(raw).hexdigest(),
               "n": len(capture["points"]), "upper_pressure_mmhg": upper,
               "results": {}}
        for width in (5, 10):
            result = analyze(capture, upper_pressure=upper, bin_width_mmhg=width)
            row["results"][str(width)] = {
                "status": result["status"], "clean_beats": result.get("clean_beats"),
                "height": summarize_feature(result, "height"),
                "area": summarize_feature(result, "area")}
        rows.append(row)
    summary = {}
    for group in ("historical_development", "rule_selection_20261101"):
        subset = [row for row in rows if row["group"] == group]
        summary[group] = {"total": len(subset)}
        for width in ("5", "10"):
            summary[group][width] = {
                key: sum(row["results"][width][key]["screen"] == "pass" and
                         row["results"][width][key]["status"] == "diagnostic_only"
                         for row in subset) for key in ("height", "area")}
    return {"schema": "bp.bin_width_sensitivity/1",
            "catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
            "method": "strict decode; unchanged beat extraction; compare only bin_width_mmhg 5 versus 10",
            "historical_set_is_independent": False,
            "selection_set_is_independent": False,
            "summary": summary, "runs": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("captures", nargs="+", type=Path,
                        help="explicit rule-selection captures; do not infer settings from names")
    args = parser.parse_args()
    report = audit(args.catalog, args.captures)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": report["summary"]},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
