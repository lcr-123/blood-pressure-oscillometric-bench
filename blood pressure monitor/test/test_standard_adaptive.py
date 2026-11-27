"""Range and abstention tests for the offline Standard BP candidate."""

import math
import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from bp_standard_adaptive import PRESETS, analyze_path, audit, infer


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


def capture(map_value, pulse=True, start=None, irregular=False, bpm=80):
    start = float(start if start is not None else map_value + 50)
    count = 3000
    points = []
    width = 18.0
    for i in range(count):
        pressure = start + (12 - start) * i / (count - 1)
        amplitude = (0.001 + 0.026 * math.exp(-0.5 *
                     ((pressure - map_value) / width) ** 2)) if pulse else 0.0
        voltage = (0.55 + 0.004 * pressure +
                   amplitude * math.sin(2 * math.pi * i * bpm / 2400) +
                   0.0003 * math.sin(2 * math.pi * i / 7))
        points.append({"t": i * 25 + (1 if irregular and i >= 500 else 0),
                       "p": bits(pressure), "v": bits(voltage)})
    return {"header": {"calc": 2}, "points": points}


class StandardAdaptiveTests(unittest.TestCase):
    def test_supported_pressure_ranges_without_bp_labels(self):
        profiles = [row[2] for row in PRESETS if row[2] != 40] + [83]
        for map_value in profiles:
            with self.subTest(peak=map_value):
                result = infer(capture(map_value))
                self.assertEqual(result["status"], "envelope_candidate", result)
                self.assertAlmostEqual(result["envelope_peak_mmhg"], map_value, delta=12)
                self.assertIsNone(result["sbp_mmhg"])
                self.assertIsNone(result["dbp_mmhg"])
                self.assertFalse(result["bp_output_allowed"])
                self.assertIn("height", result["exploratory_ratio_crossings_mmhg"])
                self.assertIn("area", result["exploratory_ratio_crossings_mmhg"])
                self.assertAlmostEqual(result["pulse_bpm"], 80, delta=3)

    def test_missing_high_tail_abstains(self):
        result = infer(capture(166, start=178))
        self.assertEqual(result["status"], "abstain")
        self.assertIn(result["reason"], ("insufficient_occupied_bins",
                                         "incomplete_or_weak_peak",
                                         "incomplete_envelope_tails"))
        self.assertIsNone(result["sbp_mmhg"])

    def test_no_pulse_and_irregular_ticks_abstain(self):
        self.assertEqual(infer(capture(93, pulse=False))["status"], "abstain")
        self.assertEqual(infer(capture(93, irregular=True))["reason"],
                         "irregular_mcu_ticks")

    def test_lowest_preset_peak_abstains_without_low_tail(self):
        result = infer(capture(40))
        self.assertEqual(result["status"], "abstain")
        self.assertIsNone(result["envelope_peak_mmhg"])
        self.assertFalse(result["bp_output_allowed"])

    def test_user_defined_cadence_range(self):
        for bpm in (60, 120, 140):
            with self.subTest(bpm=bpm):
                result = infer(capture(83, bpm=bpm))
                self.assertEqual(result["status"], "envelope_candidate", result)
                self.assertAlmostEqual(result["pulse_bpm"], bpm, delta=4)
        for bpm in (50, 160):
            with self.subTest(unsupported_bpm=bpm):
                result = infer(capture(83, bpm=bpm))
                self.assertEqual(result["status"], "abstain")

    def test_real_manifest_keeps_high_preset_unqualified(self):
        root = Path(__file__).resolve().parents[2]
        report = audit(root / "data/reports/standard_bp_development_manifest_20261101.json")
        self.assertEqual(len(report["profiles"]), 8)
        self.assertEqual(report["profiles"][-1]["name"], "user_defined")
        rows = report["runs"]
        self.assertEqual(sum(row["status"] == "envelope_candidate" for row in rows), 5)
        self.assertTrue(all(row["status"] == "abstain" for row in rows
                            if row["panel_setting_mmhg"] == [200, 150]))
        source = root / "data/reports/standard120_80_20261101-152030.verified.ndjson"
        direct = analyze_path(source)
        matching = next(row for row in rows if row["run_id"].endswith("152030"))
        self.assertEqual(direct["status"], matching["status"])
        self.assertEqual(direct["envelope_peak_mmhg"], matching["envelope_peak_mmhg"])
        self.assertIsNone(direct["exploratory_ratio_crossings_mmhg"]["height"]["high_50pct"])
        self.assertIsNone(direct["exploratory_ratio_crossings_mmhg"]["area"]["high_50pct"])
        self.assertFalse(direct["bp_output_allowed"])


if __name__ == "__main__":
    unittest.main()
