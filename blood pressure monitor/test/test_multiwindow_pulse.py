"""Host-only checks for label-free multiwindow pulse diagnostics."""

import math
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bp_multiwindow_pulse import analyze_capture, window_fft


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def capture_at(bpm, disturbance=False):
    points = []
    for i in range(2200):
        pressure = 140 - 110 * i / 2200
        amp = 0.003 + 0.015 * math.exp(-((pressure - 85) / 35) ** 2)
        voltage = 1.8 + 0.0002 * i / 2200 + amp * math.sin(2 * math.pi * bpm * i / 2400)
        if disturbance and i < 256:
            voltage += 0.02 * math.sin(2 * math.pi * i / 43)
        points.append({"i": i, "t": 25 * i, "p": bits(pressure), "v": bits(voltage)})
    return {"points": points}


class MultiwindowPulseTests(unittest.TestCase):
    def test_half_bpm_bin_uses_firmware_rounding(self):
        signal = [1.8 + 0.01 * math.sin(2 * math.pi * 12 * i / 256)
                  for i in range(256)]
        self.assertEqual(window_fft(signal)["bpm"], 113)

    def test_three_rates_with_disturbed_first_window(self):
        for bpm in (60, 80, 100):
            with self.subTest(bpm=bpm):
                for stride in (128, 256):
                    report = analyze_capture(capture_at(bpm, disturbance=True), stride)
                    self.assertEqual(report["status"], "candidate")
                    self.assertAlmostEqual(report["candidate_bpm"], bpm, delta=10)
                    self.assertGreaterEqual(report["passing_windows"], 3)

    def test_irregular_ticks_and_insufficient_pressure_coverage(self):
        capture = capture_at(80)
        capture["points"][200]["t"] += 1
        self.assertEqual(analyze_capture(capture)["status"], "irregular_sampling")
        capture = capture_at(80)
        for point in capture["points"]:
            point["p"] = bits(20)
        self.assertEqual(analyze_capture(capture)["status"], "no_consensus")
        self.assertIsNone(analyze_capture(capture)["candidate_bpm"])

    def test_invalid_stride(self):
        with self.assertRaises(ValueError):
            analyze_capture(capture_at(80), 64)

    def test_valve_only_and_low_noise_do_not_claim_pulse(self):
        for kind in ("valve", "noise"):
            with self.subTest(kind=kind):
                capture = capture_at(80)
                for i, point in enumerate(capture["points"]):
                    if kind == "valve":
                        value = 1.8 + 0.003 * math.sin(2 * math.pi * 5 * i / 40)
                    else:
                        value = 1.8 + 0.00002 * math.sin(2 * math.pi * i / 30)
                    point["v"] = bits(value)
                for stride in (128, 256):
                    report = analyze_capture(capture, stride)
                    self.assertIsNone(report["candidate_bpm"])


if __name__ == "__main__":
    unittest.main()
