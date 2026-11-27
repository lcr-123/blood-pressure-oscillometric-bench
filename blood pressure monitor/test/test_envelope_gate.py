"""Regression checks for read-only abstention, not BP accuracy."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "blood pressure monitor" / "tools"))
from bp_envelope_gate import DEFAULT_MANIFEST, audit, decision
from bp_oscillogram_study import analyze
from test_oscillogram_study import capture


class EnvelopeGateTests(unittest.TestCase):
    def test_complete_synthetic_curve_only_returns_envelope_candidate(self):
        result = decision(analyze(capture(75, 130), bin_width_mmhg=5))
        self.assertEqual(result["envelope_decision"], "analyzable_candidate")
        self.assertFalse(result["bp_output_allowed"])
        self.assertIsNone(result["bp_estimate_mmhg"])

    def test_missing_high_pressure_tail_abstains(self):
        result = decision(analyze(capture(115, 123), bin_width_mmhg=5))
        self.assertEqual(result["envelope_decision"], "abstain")
        self.assertIn("height:incomplete_oscillogram", result["reasons"])

    def test_no_pulse_abstains_without_feature_data(self):
        result = decision(analyze(capture(75, 130, pulse=False)))
        self.assertEqual(result["envelope_decision"], "abstain")
        self.assertIn("height:pulse_unreliable", result["reasons"])

    def test_rejected_robustness_without_reason_cannot_pass(self):
        result = {"status": "diagnostic_only", "height": {"status": "diagnostic_only",
                  "robustness": {"screen": "reject", "reasons": []}},
                  "area": {"status": "diagnostic_only",
                  "robustness": {"screen": "pass", "reasons": []}}}
        self.assertEqual(decision(result)["reasons"], ["height:robustness_unavailable"])

    def test_retained_runs_keep_failed_and_preset3_abstentions(self):
        report = audit(DEFAULT_MANIFEST)
        rows = {row["run_id"]: row for row in report["runs"]}
        self.assertEqual(len(rows), 7)
        self.assertEqual(sum(row["envelope_decision"] == "abstain"
                             for row in rows.values()), 2)
        self.assertEqual(rows["standard200_150_20261101-133011"]["reasons"],
                         ["capture_incomplete"])
        high = rows["standard200_150_20261101-134453"]
        self.assertIn("upper_bound_not_declared_for_preset3", high["reasons"])
        self.assertEqual(high["assessments"]["10"]["envelope_decision"], "abstain")
        self.assertEqual(rows["standard120_80_20261101-152030"]["envelope_decision"],
                         "analyzable_candidate")
        self.assertTrue(all(row["bp_estimate_mmhg"] is None for row in rows.values()))


if __name__ == "__main__":
    unittest.main()
