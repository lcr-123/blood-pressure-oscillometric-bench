"""Sensitivity diagnostics must preserve abstentions and causal boundaries."""

import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bp_capture import decode
import bp_peak_instability
from bp_peak_instability import (checked_bytes, deletion_sensitivity, diagnose,
                                 valve_observability, variants)
from bp_standard_adaptive import infer
from test_standard_adaptive import capture


ROOT = Path(__file__).resolve().parents[2]


def fixed_beats(amplitudes):
    return [(25 + 10 * i + offset, value, value * 0.35)
            for i, value in enumerate(amplitudes) for offset in (-0.3, -0.1, 0.1, 0.3)]


class PeakInstabilityTests(unittest.TestCase):
    def test_flat_top_has_smaller_margin_than_sharp_peak(self):
        sharp = fixed_beats([.001, .003, .007, .014, .035, .014, .007, .003, .001])
        flat = fixed_beats([.001, .003, .010, .030, .030, .030, .010, .003, .001])
        sharp_result = variants(sharp)[0]
        flat_result = variants(flat)[0]
        self.assertGreater(sharp_result["features"]["height"]["top_two_relative_margin"],
                           flat_result["features"]["height"]["top_two_relative_margin"])
        self.assertEqual(sharp_result["features"]["height"]["top_bins"][0]["center_mmhg"], 65)
        for feature, key in (("height", "height_median_v"), ("area", "area_median_v_s")):
            for top in sharp_result["features"][feature]["top_bins"]:
                reconstructed = sum(row["weight"] * row[key] for row in top["contributions"])
                self.assertAlmostEqual(top["smoothed"], reconstructed)
                self.assertTrue(all(len(row["beat_indices"]) == row["count"]
                                    for row in top["contributions"]))

    def test_single_beat_can_move_peak_and_failed_trial_is_retained(self):
        beats = fixed_beats([.001, .003, .008, .018, .026, .030, .029, .020, .010, .003, .001])
        beats = [beat for beat in beats if not 84 < beat[0] < 86]
        beats.extend([(84.8, .020, .007), (85, .029, .01015), (85.2, .050, .0175)])
        before = variants(beats)
        result = deletion_sensitivity(beats, before)
        self.assertEqual(result["trial_count"], len(beats))
        trial = result["trials"][-3]  # Remove the low beat in the neighboring bin.
        self.assertIn(0, trial["changed_origins_mmhg"])
        self.assertEqual(before[0]["summary"]["height_area_peaks_mmhg"], [75, 75])
        self.assertEqual(trial["variants"][0]["peaks_mmhg"], [85, 85])
        self.assertEqual(trial["variants"][0]["reason"], "incomplete_or_weak_peak")
        self.assertEqual(sum(result["outcome_counts"].values()), len(beats))

    def test_aggregate_and_threshold_events_do_not_imply_valve_phase(self):
        result = valve_observability({"valve": {"period_min": 200, "period_max": 200,
                                               "pulses": 392, "steps": 0},
                                      "steps": [{"i": 100}]})
        self.assertFalse(result["phase_alignment_possible"])
        self.assertFalse(result["full_pulse_event_timestamps_available"])
        self.assertEqual(result["physical_cause"], "unresolved")

    def test_invalid_extraction_has_no_deletion_result(self):
        result = diagnose(capture(83, irregular=True))
        self.assertEqual(result["reason"], "irregular_mcu_ticks")
        self.assertEqual(result["variants"], [])
        self.assertIsNone(result["deletions"])
        self.assertFalse(result["bp_output_allowed"])

    def test_diagnostic_does_not_change_input_or_inference(self):
        sample = capture(83)
        frozen = copy.deepcopy(sample)
        before = infer(sample)
        diagnostic = diagnose(sample)
        self.assertEqual(sample, frozen)
        self.assertEqual(infer(sample), before)
        self.assertEqual(diagnostic["stability"], before["stability"])
        self.assertFalse(diagnostic["bp_output_allowed"])

    def test_sha_mismatch_fails_instead_of_using_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.ndjson"
            path.write_bytes(b"original")
            expected = hashlib.sha256(b"original").hexdigest()
            self.assertEqual(checked_bytes(path, expected), b"original")
            path.write_bytes(b"modified")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                checked_bytes(path, expected)

    def test_cli_refuses_to_overwrite_retained_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "data/reports"
            reports.mkdir(parents=True)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({"runs": []}), encoding="utf-8")
            prefix = reports / "retained"
            output = prefix.with_suffix(".json")
            output.write_bytes(b"retained evidence")
            argv = ["bp_peak_instability.py", "--manifest", str(manifest),
                    "--output-prefix", str(prefix)]
            with patch.object(bp_peak_instability, "ROOT", root), patch.object(sys, "argv", argv), \
                    patch("sys.stderr", new_callable=io.StringIO) as stderr:
                with self.assertRaises(SystemExit) as error:
                    bp_peak_instability.main()
                self.assertEqual(error.exception.code, 2)
                self.assertIn("output already exists", stderr.getvalue())
            self.assertEqual(output.read_bytes(), b"retained evidence")

    def test_real_target275_retains_close_peaks_and_every_deletion(self):
        path = ROOT / ("data/reports/standard255_195_target275_capacity4200_"
                       "20261105-111540.verified.ndjson")
        sample = decode(path.read_text(encoding="utf-8-sig").splitlines())
        result = diagnose(sample)
        self.assertEqual(len(result["beats"]), 73)
        self.assertEqual(result["stability"]["reason"], "bin_origin_peak_unstable")
        self.assertEqual(result["stability"]["peak_span_mmhg"], 17.5)
        self.assertEqual(result["deletions"]["trial_count"], 73)
        for variant in result["variants"]:
            self.assertLess(variant["features"]["height"]["top_two_relative_margin"], .03)
        self.assertEqual(result["variants"][0]["features"]["height"]["top_bins"][0]["count"], 3)
        self.assertFalse(result["valve"]["phase_alignment_possible"])


if __name__ == "__main__":
    unittest.main()
