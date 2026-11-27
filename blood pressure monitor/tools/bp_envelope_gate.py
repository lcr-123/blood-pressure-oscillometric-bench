"""Read-only envelope quality decisions for retained non-human captures.

This gate never reports SBP/DBP or claims simulator/clinical accuracy. The
2026-11-01 development runs helped select the 10 mmHg candidate rule.
"""

import argparse
import hashlib
import json
from pathlib import Path

from bp_capture import decode
from bp_oscillogram_study import analyze


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = ROOT / "data/reports/standard_bp_development_manifest_20261101.json"
DEFAULT_OUTPUT = ROOT / "data/reports/standard_bp_envelope_gate_20261101.json"


def decision(analysis):
    """Return a diagnostic quality decision without calculating blood pressure."""
    reasons = []
    for key in ("height", "area"):
        feature = analysis.get(key)
        if not feature:
            reasons.append(f"{key}:{analysis['status']}")
            continue
        if feature["status"] != "diagnostic_only":
            reasons.append(f"{key}:{feature['status']}")
        robustness = feature.get("robustness", {})
        if robustness and robustness.get("screen") != "pass":
            failures = robustness.get("reasons") or ["robustness_unavailable"]
            reasons.extend(f"{key}:{reason}" for reason in failures)
        elif not robustness and feature["status"] == "diagnostic_only":
            reasons.append(f"{key}:robustness_unavailable")
    return {"envelope_decision": "abstain" if reasons else "analyzable_candidate",
            "reasons": reasons, "bp_output_allowed": False,
            "bp_estimate_mmhg": None}


def audit(manifest_path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    rows = []
    for run in manifest["runs"]:
        row = {"run_id": run["run_id"], "dataset_role": run["dataset_role"],
               "outcome": run["outcome"], "bp_output_allowed": False,
               "bp_estimate_mmhg": None}
        if run["outcome"] != "export_received":
            row.update(envelope_decision="abstain", reasons=["capture_incomplete"])
            rows.append(row)
            continue
        source = ROOT / run["verified_path"]
        content = source.read_bytes()
        if hashlib.sha256(content).hexdigest() != run["verified_sha256"]:
            raise ValueError(f"verified source hash mismatch: {run['run_id']}")
        capture = decode(content.decode("utf-8-sig").splitlines())
        setting = run["panel_setting_mmhg"]
        upper = {(120, 80): 130, (150, 100): 170, (200, 150): 170}.get(tuple(setting))
        if upper is None:
            raise ValueError(f"undeclared analysis range: {run['run_id']}")
        assessments = {}
        for width in (5, 10):
            analysis = analyze(capture, upper_pressure=upper, bin_width_mmhg=width)
            assessments[str(width)] = {"study_status": analysis["status"],
                                       "clean_beats": analysis.get("clean_beats"),
                                       **decision(analysis)}
        row.update(verified_path=run["verified_path"],
                   verified_sha256=run["verified_sha256"],
                   upper_pressure_mmhg=upper, assessments=assessments)
        row.update({key: assessments["10"][key] for key in
                    ("envelope_decision", "reasons")})
        if setting == [200, 150]:
            row["reasons"] = ["upper_bound_not_declared_for_preset3", *row["reasons"]]
            row["envelope_decision"] = "abstain"
            row["upper_pressure_role"] = "150/100 bound reused for diagnosis only"
        else:
            row["upper_pressure_role"] = "existing development study setting"
        rows.append(row)
    return {"schema": "bp.envelope_gate/1",
            "manifest_path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "scope": "development data; 10 mmHg rule selected using seen runs",
            "bp_output_allowed": False, "runs": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    report = audit(args.manifest)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output),
                      "decisions": {row["run_id"]: row["envelope_decision"]
                                    for row in report["runs"]}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
