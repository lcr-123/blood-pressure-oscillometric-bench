"""Read-only diagnostics for Standard BP envelope coverage and beat gates.

The adaptive candidate and this diagnostic consume the same unrounded
extraction and envelope gates. No SBP/DBP is estimated; extraction failures
are reported explicitly rather than processing an invalid signal.
"""

import argparse
import hashlib
import json
from pathlib import Path

from bp_capture import decode
from bp_standard_envelope import assess_stability, bin_beats, extract, summarize_bins


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data/reports/standard_bp_development_manifest_20261101.json"
DEFAULT_OUTPUT = ROOT / "data/reports/standard_bp_diagnostics_20261105.json"


def diagnose_capture(capture):
    """Inspect exactly the beats and bins used by the adaptive candidate."""
    extraction = extract(capture)
    beats = extraction.pop("beats")
    rows = bin_beats(beats)
    baseline = summarize_bins(rows)
    result = {**extraction,
              "extraction_status": extraction["status"],
              "extraction_reason": extraction["reason"],
              "occupied_bins": rows,
              "qualified_bin_count": baseline["qualified_bin_count"],
              "height_envelope": baseline["envelopes"]["height"],
              "area_envelope": baseline["envelopes"]["area"],
              "baseline_status": baseline["status"],
              "baseline_reason": baseline["reason"],
              "stability": assess_stability(beats) if extraction["status"] == "ready" else None}
    return result


def diagnose_file(path):
    content = path.read_bytes()
    capture = decode(content.decode("utf-8-sig").splitlines())
    return {
        "source": str(path),
        "source_sha256": hashlib.sha256(content).hexdigest(),
        **diagnose_capture(capture),
    }


def audit(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    rows = []
    for run in manifest["runs"]:
        row = {"run_id": run["run_id"],
               "panel_setting_mmhg": run["panel_setting_mmhg"],
               "outcome": run["outcome"]}
        if run["outcome"] != "export_received":
            row["status"] = "capture_incomplete"
        else:
            source = ROOT / run["verified_path"]
            content = source.read_bytes()
            if hashlib.sha256(content).hexdigest() != run["verified_sha256"]:
                raise ValueError(f"verified hash mismatch: {run['run_id']}")
            row.update(diagnose_file(source))
        rows.append(row)
    return {
        "schema": "bp.standard_adaptive_diagnostics/2",
        "scope": "read-only development diagnostics; no SBP/DBP inference",
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "runs": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--capture", type=Path)
    args = parser.parse_args()
    if args.capture:
        report = {"schema": "bp.standard_adaptive_capture_diagnostics/2",
                  **diagnose_file(args.capture)}
    else:
        report = audit(args.manifest)
    if args.output.resolve() in {args.manifest.resolve(),
                                 args.capture.resolve() if args.capture else Path("!").resolve()}:
        parser.error("output must not overwrite an input")
    if args.output.suffix.lower() != ".json":
        parser.error("output must be a JSON report")
    if (ROOT / "data/raw").resolve() in args.output.resolve().parents:
        parser.error("output must not be inside raw data")
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({"output": str(args.output),
                      "status": "capture_diagnosed" if args.capture else "audit_complete",
                      "run_count": 1 if args.capture else len(report["runs"])},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
