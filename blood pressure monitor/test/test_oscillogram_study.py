"""Synthetic checks for the offline oscillogram study, not clinical validation."""

import math
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bp_oscillogram_study import _feature_curve, analyze


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def capture(map_pressure, start_pressure, pulse=True, pressure_glitch=False):
    points = []
    for i in range(2400):
        pressure = start_pressure - i * 0.05
        amplitude = (0.003 + 0.020 * math.exp(-0.5 *
                     ((pressure - map_pressure) / 15.0) ** 2)) if pulse else 0.0
        voltage = (1.0 + 0.005 * pressure +
                   amplitude * math.sin(2 * math.pi * i / 30) +
                   0.003 * math.sin(2 * math.pi * 5 * i / 40))
        if pressure_glitch and i == 550:
            pressure -= 7.0
            voltage -= 0.035
        points.append({"t": i * 25, "p": bits(pressure), "v": bits(voltage)})
    return {"header": {"calc": 2}, "points": points}


class OscillogramStudyTests(unittest.TestCase):
    def test_robustness_screen_rejects_sparse_peak_and_pressure_gap(self):
        beats = []
        for low in range(50, 170, 5):
            height = 0.005 + 0.030 * math.exp(-0.5 * ((low + 2.5 - 122.5) / 18) ** 2)
            count = 2 if low == 120 else 3
            beats.extend({"pressure": low + 2.5, "height": height}
                         for _ in range(count))
        weak = _feature_curve(beats, "height", 170)
        self.assertEqual(weak["status"], "diagnostic_only")
        self.assertEqual(weak["robustness"]["screen"], "reject")
        self.assertIn("weak_peak_support", weak["robustness"]["reasons"])
        self.assertEqual(weak["robustness"]["peak_bin_beats"], 2)

        gap = _feature_curve([beat for beat in beats
                              if not 75 <= beat["pressure"] < 110], "height", 170)
        self.assertEqual(gap["robustness"]["screen"], "reject")
        self.assertIn("pressure_coverage_gap", gap["robustness"]["reasons"])
        self.assertGreater(gap["robustness"]["max_occupied_gap_mmhg"], 15)

        supported = _feature_curve(beats + [{"pressure": 122.5,
                                             "height": 0.035}], "height", 170)
        self.assertEqual(supported["robustness"]["screen"], "pass")
        self.assertEqual(supported["robustness"]["reasons"], [])

    def test_jackknife_rejects_saved_high_target_bin_shape(self):
        # Rounded medians from the verified 170426 export at 40-sample padding.
        bins = [(52.5, .0090760), (57.5, .0138737), (67.5, .0134680),
                (72.5, .0122440), (112.5, .0286242), (127.5, .0247072),
                (132.5, .0251478), (137.5, .0206766), (142.5, .0288289),
                (147.5, .0263072), (152.5, .0139104), (157.5, .0155889)]
        beats = [{"pressure": pressure, "height": height}
                 for pressure, height in bins for _ in range(3)]
        report = _feature_curve(beats, "height", 170)
        self.assertEqual(report["robustness"]["peak_bin_beats"], 3)
        self.assertEqual(report["robustness"]["max_occupied_gap_mmhg"], 40)
        self.assertIn("jackknife_unstable", report["robustness"]["reasons"])
        self.assertGreater(report["robustness"]["jackknife_max_shift_mmhg"], 15)

    def test_label_free_map_tracks_two_pressure_settings_with_valve_noise(self):
        low = analyze(capture(75, 130, pressure_glitch=True))
        high = analyze(capture(115, 145, pressure_glitch=True))
        self.assertEqual(low["status"], "diagnostic_only")
        self.assertEqual(high["status"], "diagnostic_only")
        self.assertAlmostEqual(low["height"]["gaussian"]["peak_mmhg"], 75, delta=10)
        self.assertAlmostEqual(high["height"]["gaussian"]["peak_mmhg"], 115, delta=10)
        self.assertGreater(high["height"]["gaussian"]["peak_mmhg"] -
                           low["height"]["gaussian"]["peak_mmhg"], 25)
        self.assertGreaterEqual(low["pressure_steps"], 2)

    def test_valve_only_signal_has_no_map_candidate(self):
        report = analyze(capture(75, 130, pulse=False))
        self.assertEqual(report["status"], "pulse_unreliable")
        self.assertNotIn("height", report)

    def test_missing_upper_oscillogram_tail_is_reported(self):
        report = analyze(capture(115, 123))
        self.assertEqual(report["status"], "incomplete_oscillogram")
        self.assertGreaterEqual(report["height"]["high_tail_ratio"], 0.8)

    def test_incomplete_calculation_is_not_analyzed(self):
        sample = capture(75, 130)
        sample["header"]["calc"] = 0
        self.assertEqual(analyze(sample), {"status": "calculation_incomplete",
                                           "bin_width_mmhg": 5})

    def test_step_padding_has_bounded_research_range(self):
        with self.assertRaisesRegex(ValueError, "0..80"):
            analyze(capture(75, 130), 81)

    def test_upper_pressure_changes_only_research_search_range(self):
        sample = capture(115, 165)
        wide = analyze(sample, upper_pressure=170)
        self.assertEqual(wide["upper_pressure_mmhg"], 170)
        self.assertEqual(wide["status"], "diagnostic_only")
        self.assertAlmostEqual(wide["height"]["gaussian"]["peak_mmhg"], 115, delta=10)
        with self.assertRaisesRegex(ValueError, "130 or 170"):
            analyze(sample, upper_pressure=180)

    def test_bin_width_is_explicit_and_bounded(self):
        sample = capture(115, 165)
        default = analyze(sample, upper_pressure=170)
        five = analyze(sample, upper_pressure=170, bin_width_mmhg=5)
        ten = analyze(sample, upper_pressure=170, bin_width_mmhg=10)
        self.assertEqual(default, five)
        self.assertEqual(ten["bin_width_mmhg"], 10)
        self.assertEqual(ten["height"]["bins"][0]["pressure_mmhg"] % 10, 5)
        with self.assertRaisesRegex(ValueError, "5 or 10"):
            analyze(sample, upper_pressure=170, bin_width_mmhg=20)


if __name__ == "__main__":
    unittest.main()
