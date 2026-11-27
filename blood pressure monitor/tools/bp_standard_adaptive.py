"""Offline, label-blind Standard BP envelope candidate and preset audit.

This is a development diagnostic, not a firmware or clinical BP result.
The seven fixed presets are evaluation labels only. User Defined is optional.
"""

import argparse
import hashlib
import json
from pathlib import Path

from bp_capture import decode
from bp_standard_envelope import (BIN, FS, assess_stability, bin_beats, extract,
                                  summarize_bins)


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data/reports/standard_bp_development_manifest_20261101.json"
DEFAULT_OUTPUT = ROOT / "data/reports/standard_bp_adaptive_20261105.json"
PRESETS = ((120, 80, 93, 80, 0.68), (150, 100, 116, 80, 0.65),
           (200, 150, 166, 80, 0.60), (255, 195, 215, 80, 0.55),
           (60, 30, 40, 80, 0.75), (80, 50, 60, 80, 0.71),
           (100, 65, 76, 80, 0.69))


def _abstain(reason, **details):
    return {"status": "abstain", "reason": reason, "envelope_peak_mmhg": None,
            "sbp_mmhg": None, "dbp_mmhg": None, "pulse_bpm": None,
            "bp_output_allowed": False, "exploratory_ratio_crossings_mmhg": None,
            **details}


def infer(capture):
    """Find a stable diagnostic envelope peak without estimating BP."""
    extraction = extract(capture)
    if extraction["status"] != "ready":
        return _abstain(extraction["reason"],
                        clean_beats=len(extraction["beats"]))
    beats = extraction["beats"]
    rows = bin_beats(beats)
    baseline = summarize_bins(rows)
    if baseline["status"] != "envelope_candidate":
        return _abstain(baseline["reason"], clean_beats=len(beats))
    stability = assess_stability(beats)
    if stability["status"] != "pass":
        return _abstain(stability["reason"], clean_beats=len(beats),
                        baseline_envelope_peak_mmhg=baseline["candidate_peak_mmhg"],
                        stability=stability)
    qualified = [row for row in rows if row["used_for_envelope"]]
    exploratory = {name: {"high_50pct": detail["high_50pct"],
                          "low_60pct": detail["low_60pct"]}
                   for name, detail in baseline["envelopes"].items()}
    return {"status": "envelope_candidate", "reason": None,
            "envelope_peak_mmhg": round(baseline["candidate_peak_mmhg"], 2),
            "sbp_mmhg": None, "dbp_mmhg": None, "bp_output_allowed": False,
            "pulse_bpm": round(extraction["dominant_pulse_bpm"], 1),
            "clean_beats": len(beats), "occupied_bins": len(qualified),
            "pressure_range_mmhg": [qualified[0]["center_mmhg"],
                                     qualified[-1]["center_mmhg"]],
            "height_area_peaks_mmhg": baseline["height_area_peaks_mmhg"],
            "exploratory_ratio_crossings_mmhg": exploratory,
            "stability": stability}


def audit(manifest_path, user_defined=None):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    profiles = [{"name": f"preset_{i}", "sbp": row[0], "dbp": row[1],
                 "map": row[2], "bpm": row[3], "pulse_volume_cc": row[4]}
                for i, row in enumerate(PRESETS, 1)]
    profiles.append({"name": "user_defined", "setting": user_defined,
                     "note": "separate manual mode; no fixed eighth Standard BP preset"})
    rows = []
    for run in manifest["runs"]:
        row = {"run_id": run["run_id"], "panel_setting_mmhg": run["panel_setting_mmhg"],
               "outcome": run["outcome"]}
        if run["outcome"] != "export_received":
            row.update(_abstain("capture_incomplete"))
        else:
            source = ROOT / run["verified_path"]
            content = source.read_bytes()
            if hashlib.sha256(content).hexdigest() != run["verified_sha256"]:
                raise ValueError(f"verified hash mismatch: {run['run_id']}")
            capture = decode(content.decode("utf-8-sig").splitlines())
            row.update(infer(capture))
        setting = next((p for p in profiles[:7] if
                        [p["sbp"], p["dbp"]] == run["panel_setting_mmhg"]), None)
        if setting is None and user_defined and [user_defined["sbp"], user_defined["dbp"]] == run["panel_setting_mmhg"]:
            setting = user_defined
        if setting and row["status"] == "envelope_candidate":
            row["envelope_peak_minus_panel_map_mmhg"] = round(
                row["envelope_peak_mmhg"] - setting["map"], 2)
        rows.append(row)
    return {"schema": "bp.standard_adaptive/3", "scope": "development-only; BP outputs withheld; labels held out of inference",
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "profiles": profiles, "runs": rows, "firmware_changed": False}


def analyze_path(path):
    """Strictly decode one complete transfer without needing a preset label."""
    content = path.read_bytes()
    capture = decode(content.decode("utf-8-sig").splitlines())
    return {"schema": "bp.standard_adaptive_capture/3", "source": str(path),
            "source_sha256": hashlib.sha256(content).hexdigest(),
            **infer(capture)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--capture", type=Path, help="one complete verified capture; output path required")
    parser.add_argument("--user-defined", type=str, help="optional SBP/DBP/MAP/BPM profile for audit metadata")
    args = parser.parse_args()
    if args.capture and (args.output is None or args.user_defined):
        parser.error("--capture requires --output and cannot use --user-defined")
    if args.capture and args.output.resolve() == args.capture.resolve():
        parser.error("output must not overwrite capture input")
    if args.output and args.output.suffix.lower() != ".json":
        parser.error("output must be a JSON report")
    if args.output and args.output.resolve() == args.manifest.resolve():
        parser.error("output must not overwrite manifest input")
    if args.output and (ROOT / "data/raw").resolve() in args.output.resolve().parents:
        parser.error("output must not be inside raw data")
    user_defined = None
    if args.user_defined:
        parts = args.user_defined.split("/")
        if len(parts) != 4 or not all(part.isdecimal() for part in parts):
            parser.error("user-defined must be SBP/DBP/MAP/BPM integers")
        sbp, dbp, map_value, bpm = map(int, parts)
        if not (30 <= dbp < map_value < sbp <= 300 and 60 <= bpm <= 140):
            parser.error("user-defined pressure order or BPM out of range")
        user_defined = {"sbp": sbp, "dbp": dbp, "map": map_value, "bpm": bpm}
    report = analyze_path(args.capture) if args.capture else audit(args.manifest, user_defined)
    output = args.output or DEFAULT_OUTPUT
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output),
                      "status": report["status"] if args.capture else "audit_complete",
                      "candidate_count": None if args.capture else
                          sum(row["status"] == "envelope_candidate" for row in report["runs"]),
                      "abstain_count": None if args.capture else
                          sum(row["status"] == "abstain" for row in report["runs"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
