"""Host-only diagnostics; synthetic tests do not validate clinical BP accuracy."""

import math
import sys
import struct
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bp_beat_analysis import (CAPACITY_BY_FIRMWARE, beat_candidates,
                              capacity_projection, estimate_pulse, raw_cadence)


class BeatAnalysisTests(unittest.TestCase):
    @staticmethod
    def bits(value):
        return struct.unpack("<I", struct.pack("<f", value))[0]

    def test_capacity_uses_observed_rate_and_reports_overflow(self):
        capture = {"points": [{"p": 0}] * 2300, "duration_ms": 57500}
        capture["points"][0] = {"p": self.bits(135.0)}
        capture["points"][-1] = {"p": self.bits(15.0)}
        report = capacity_projection(capture, 150, [170, 180, 190])
        self.assertAlmostEqual(report["mean_rate_mmhg_s"], 2.087, places=3)
        self.assertEqual([item["projected_samples"] for item in report["projections"]],
                         [2683, 2875, 3067])
        self.assertLess(report["projections"][1]["remaining_samples"], 0)
        self.assertEqual(CAPACITY_BY_FIRMWARE["STACK_WATERMARK_20261027"], 2800)
        self.assertEqual(CAPACITY_BY_FIRMWARE["CAPTURE_COMPACT_20261028"], 3300)
        self.assertEqual(CAPACITY_BY_FIRMWARE["CAPTURE4200_20261105"], 4200)
        self.assertEqual(capacity_projection(capture, 150, [190], 3300)["capture_capacity"], 3300)
        with self.assertRaisesRegex(ValueError, "finite"):
            capacity_projection(capture, 150, [float("nan")])

    def test_regular_synthetic_beats_can_form_diagnostic_candidates(self):
        points = []
        for i in range(1800):
            pressure = 135.0 - i * 120.0 / 1800
            amplitude = 0.002 + 0.018 * math.exp(-((pressure - 80.0) / 23.0) ** 2)
            phase = (i % 30) - 15
            smooth = 0.0005 + amplitude * math.exp(-(phase / 5.0) ** 2)
            points.append({"p": self.bits(pressure), "s": self.bits(smooth)})
        report = beat_candidates({"header": {"calc": 2}, "points": points}, 80)
        self.assertEqual(report["status"], "diagnostic_only")
        self.assertGreater(report["cadence_fraction"], 0.95)
        self.assertAlmostEqual(report["map_candidate"]["pressure_mmhg"], 80, delta=4)
        self.assertIsNotNone(report["sbp_candidate_mmhg"])
        self.assertIsNotNone(report["dbp_candidate_mmhg"])

    def test_wrong_cadence_suppresses_bp_candidates(self):
        points = []
        for i in range(1200):
            pressure = 130.0 - i * 100.0 / 1200
            phase = (i % 60) - 30
            smooth = 0.0005 + 0.012 * math.exp(-(phase / 5.0) ** 2)
            points.append({"p": self.bits(pressure), "s": self.bits(smooth)})
        report = beat_candidates({"header": {"calc": 2}, "points": points}, 80)
        self.assertEqual(report["status"], "cadence_unreliable")
        self.assertEqual(report["median_interpeak_ms"], 1500)
        self.assertNotIn("map_candidate", report)

    def synthetic_raw_capture(self, period, pressure_start=135.0):
        points = []
        for i in range(1800):
            pressure = pressure_start - i * 120.0 / 1800
            amplitude = 0.003 + 0.018 * math.exp(-((pressure - 80.0) / 30.0) ** 2)
            voltage = (1.8 + 0.0005 * i / 1800 +
                       amplitude * math.sin(2 * math.pi * i / period) +
                       0.003 * math.sin(2 * math.pi * 5 * i / 40))
            points.append({"p": self.bits(pressure), "v": self.bits(voltage),
                           "t": i * 25})
        return {"points": points}

    def test_raw_voltage_detects_80_bpm_despite_valve_frequency(self):
        report = raw_cadence(self.synthetic_raw_capture(30), 80)
        self.assertEqual(report["status"], "cadence_detected")
        self.assertAlmostEqual(report["dominant_hz"], 80 / 60, delta=0.08)
        self.assertGreater(report["cadence_fraction"], 0.9)

    def test_raw_voltage_rejects_wrong_cadence(self):
        report = raw_cadence(self.synthetic_raw_capture(40), 80)
        self.assertEqual(report["status"], "cadence_unreliable")
        self.assertNotIn("map_candidate", report)

    def test_valve_frequency_alone_is_not_detected_as_80_bpm(self):
        capture = self.synthetic_raw_capture(30)
        for i, point in enumerate(capture["points"]):
            point["v"] = self.bits(1.8 + 0.003 * math.sin(2 * math.pi * 5 * i / 40))
        report = raw_cadence(capture, 80)
        self.assertNotEqual(report["status"], "cadence_detected")

    def test_irregular_ticks_do_not_claim_raw_cadence(self):
        capture = self.synthetic_raw_capture(30)
        capture["points"][100]["t"] += 1
        self.assertEqual(raw_cadence(capture, 80)["status"], "irregular_sampling")

    def test_raw_voltage_needs_pressure_window(self):
        report = raw_cadence(self.synthetic_raw_capture(30, pressure_start=30.0), 80)
        self.assertEqual(report["status"], "insufficient_samples")

    def test_unlabeled_pulse_estimates_multiple_rates(self):
        for bpm, period in ((60, 40), (80, 30), (100, 24)):
            with self.subTest(bpm=bpm):
                report = estimate_pulse(self.synthetic_raw_capture(period))
                self.assertEqual(report["status"], "estimated")
                self.assertAlmostEqual(report["pulse_bpm"], bpm, delta=5)

    def test_unlabeled_pulse_rejects_valve_only_and_low_noise(self):
        capture = self.synthetic_raw_capture(30)
        for i, point in enumerate(capture["points"]):
            point["v"] = self.bits(1.8 + 0.003 * math.sin(2 * math.pi * 5 * i / 40))
        self.assertNotIn("pulse_bpm", estimate_pulse(capture))

        rng = np.random.default_rng(42)
        for point, noise in zip(capture["points"], rng.normal(0, 0.0002, len(capture["points"]))):
            point["v"] = self.bits(1.8 + noise)
        self.assertNotIn("pulse_bpm", estimate_pulse(capture))

    def test_unlabeled_pulse_rejects_unstable_and_irregular_series(self):
        capture = self.synthetic_raw_capture(30)
        for i in range(900, len(capture["points"])):
            point = capture["points"][i]
            point["v"] = self.bits(1.8 + 0.018 * math.sin(2 * math.pi * i / 40))
        self.assertNotIn("pulse_bpm", estimate_pulse(capture))

        capture = self.synthetic_raw_capture(30)
        capture["points"][100]["t"] += 1
        self.assertEqual(estimate_pulse(capture)["status"], "irregular_sampling")

    def test_unlabeled_pulse_requires_pressure_span(self):
        report = estimate_pulse(self.synthetic_raw_capture(30, pressure_start=30.0))
        self.assertEqual(report["status"], "insufficient_samples")


if __name__ == "__main__":
    unittest.main()
