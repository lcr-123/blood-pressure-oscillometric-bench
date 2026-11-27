"""Envelope integrity and sensitivity regressions, not BP accuracy tests."""

import copy
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bp_capture import decode
from bp_standard_adaptive import infer
from bp_standard_diagnostics import diagnose_capture
from bp_standard_envelope import bin_beats, extract, summarize_bins
from test_standard_adaptive import bits, capture


ROOT = Path(__file__).resolve().parents[2]


class StandardEnvelopeTests(unittest.TestCase):
    def test_invalid_capture_cannot_produce_plausible_diagnostics(self):
        for state in (0, 1, 4):
            sample = capture(93)
            sample["header"]["calc"] = state
            diagnostic = diagnose_capture(sample)
            self.assertEqual(diagnostic["extraction_reason"],
                             "incomplete_calculation_or_capture")
            self.assertFalse(diagnostic["height_envelope"]["qualified"])
            self.assertIsNone(diagnostic["stability"])
        sample = capture(93, irregular=True)
        self.assertEqual(diagnose_capture(sample)["extraction_reason"],
                         "irregular_mcu_ticks")
        sample = capture(93, pulse=False)
        self.assertEqual(diagnose_capture(sample)["extraction_reason"],
                         "weak_periodic_signal")

    def test_never_concatenates_short_separated_windows(self):
        sample = capture(93)
        for index in (900, 1800):
            sample["points"][index]["p"] = bits(400)
        diagnostic = diagnose_capture(sample)
        self.assertEqual(diagnostic["extraction_reason"], "fragmented_pressure_window")
        self.assertGreater(diagnostic["eligible_window_count"], 1)
        self.assertIsNone(infer(sample)["envelope_peak_mmhg"])

    def test_edge_reentry_uses_one_contiguous_window(self):
        sample = capture(93)
        # A late, otherwise disconnected eligible point must not join the PSD.
        sample["points"][-30]["p"] = bits(21)
        diagnostic = diagnose_capture(sample)
        self.assertEqual(diagnostic["extraction_status"], "ready")
        self.assertEqual(diagnostic["eligible_window_count"], 2)
        self.assertEqual(diagnostic["discarded_eligible_samples"], 1)
        first, last = diagnostic["selected_window_indices"]
        self.assertGreaterEqual(first, 80)
        self.assertLess(last, len(sample["points"]) - 30)
        self.assertEqual(infer(sample)["status"], "envelope_candidate")

    def test_single_valve_step_does_not_define_peak(self):
        sample = capture(93)
        point = sample["points"][600]
        point["p"] = bits(130)
        point["v"] = bits(2.0)
        diagnostic = diagnose_capture(sample)
        self.assertEqual(diagnostic["pressure_step_count_ge_5mmhg"], 2)
        self.assertGreater(diagnostic["rejection_counts"]["pressure_step_padding"], 0)
        result = infer(sample)
        self.assertEqual(result["status"], "envelope_candidate", result)
        self.assertAlmostEqual(result["envelope_peak_mmhg"], 93, delta=12)

    def test_two_separated_equal_peaks_are_ambiguous(self):
        beats = []
        for pressure in range(25, 195, 10):
            amplitude = (0.002 + 0.025 * math.exp(-((pressure - 75) / 9) ** 2) +
                         0.025 * math.exp(-((pressure - 135) / 9) ** 2))
            beats.extend((pressure + delta, amplitude, amplitude * 0.3)
                         for delta in (-1, 0, 1))
        result = summarize_bins(bin_beats(beats))
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "ambiguous_envelope_peak")

    def test_labels_and_firmware_envelopes_do_not_affect_inference(self):
        sample = capture(83)
        expected = infer(sample)
        modified = copy.deepcopy(sample)
        modified["header"].update(sbp=255, dbp=195, map=215, firmware="fake")
        modified["panel_setting_mmhg"] = [255, 195]
        for point in modified["points"]:
            point.update(e=bits(9999), s=bits(9999))
        self.assertEqual(infer(modified), expected)

    def test_diagnostic_and_inference_use_identical_unrounded_features(self):
        sample = capture(83)
        extraction = extract(sample)
        result = infer(sample)
        diagnostic = diagnose_capture(sample)
        self.assertEqual(diagnostic["occupied_bins"], bin_beats(extraction["beats"]))
        self.assertEqual(result["clean_beats"], diagnostic["rejection_counts"]["accepted"])
        self.assertEqual(result["stability"], diagnostic["stability"])
        self.assertEqual(result["height_area_peaks_mmhg"], [
            diagnostic["height_envelope"]["peak_center_mmhg"],
            diagnostic["area_envelope"]["peak_center_mmhg"]])

    def test_target275_real_peak_is_withheld_when_origin_changes_it(self):
        path = ROOT / ("data/reports/standard255_195_target275_capacity4200_"
                       "20261105-111540.verified.ndjson")
        sample = decode(path.read_text(encoding="utf-8-sig").splitlines())
        diagnostic = diagnose_capture(sample)
        result = infer(sample)
        self.assertEqual(diagnostic["height_envelope"]["peak_center_mmhg"], 215)
        self.assertEqual(diagnostic["stability"]["peak_range_mmhg"], [212.5, 230.0])
        self.assertEqual(diagnostic["stability"]["peak_span_mmhg"], 17.5)
        self.assertEqual(result["reason"], "bin_origin_peak_unstable")
        self.assertEqual(result["baseline_envelope_peak_mmhg"], 215)
        self.assertIsNone(result["envelope_peak_mmhg"])
        self.assertIsNone(result["sbp_mmhg"])
        self.assertIsNone(result["dbp_mmhg"])
        self.assertFalse(result["bp_output_allowed"])


if __name__ == "__main__":
    unittest.main()
