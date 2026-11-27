import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.pressure_calibration import (  # noqa: E402
    Sample,
    analyze_samples,
    generate_simulated_samples,
    read_samples_csv,
    write_reports,
)


class PressureCalibrationTests(unittest.TestCase):
    def test_exact_fit_uses_independent_verification_points(self):
        samples = [
            Sample("calibration", 0.0, 0.5),
            Sample("calibration", 100.0, 1.5),
            Sample("calibration", 200.0, 2.5),
            Sample("verification", 50.0, 1.0),
            Sample("verification", 150.0, 2.0),
        ]

        result = analyze_samples(samples, sensor_unit="V", tolerance_mmhg=0.01)

        self.assertTrue(result.passed)
        self.assertAlmostEqual(result.model.slope_mmhg_per_unit, 100.0)
        self.assertAlmostEqual(result.model.intercept_mmhg, -50.0)
        self.assertAlmostEqual(result.model.zero_voltage_v, 0.5)
        self.assertAlmostEqual(result.verification_max_abs_error_mmhg, 0.0)

    def test_deterministic_simulation_passes(self):
        samples = generate_simulated_samples(seed=20260917)

        result = analyze_samples(samples, sensor_unit="V", tolerance_mmhg=1.0)

        self.assertTrue(result.passed)
        self.assertEqual(len(result.calibration_points), 7)
        self.assertEqual(len(result.verification_points), 7)
        self.assertLess(result.verification_max_abs_error_mmhg, 1.0)
        self.assertAlmostEqual(result.model.zero_voltage_v, 0.5, places=2)
        self.assertAlmostEqual(result.model.sensitivity_v_per_kpa, 0.1, places=3)

    def test_rejects_calibration_without_pressure_span(self):
        samples = [
            Sample("calibration", 0.0, 0.5),
            Sample("calibration", 100.0, 0.5),
            Sample("verification", 50.0, 0.5),
        ]

        with self.assertRaisesRegex(ValueError, "zero span"):
            analyze_samples(samples, sensor_unit="V", tolerance_mmhg=1.0)

    def test_csv_round_trip_and_reports(self):
        samples = generate_simulated_samples(
            seed=7,
            samples_per_calibration_point=2,
            samples_per_verification_point=2,
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)
            input_path = temporary_path / "samples.csv"
            with input_path.open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=("stage", "reference_mmhg", "sensor_value"),
                )
                writer.writeheader()
                for sample in samples:
                    writer.writerow(
                        {
                            "stage": sample.stage,
                            "reference_mmhg": sample.reference_mmhg,
                            "sensor_value": sample.sensor_value,
                        }
                    )

            loaded = read_samples_csv(input_path)
            result = analyze_samples(loaded, sensor_unit="V", tolerance_mmhg=1.0)
            json_path, csv_path = write_reports(
                temporary_path / "report",
                result,
                mode="csv",
                sensor_unit="V",
            )

            self.assertTrue(json_path.is_file())
            self.assertTrue(csv_path.is_file())
            report = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(report["schema"], "pressure-calibration-report/v1")
            self.assertTrue(report["verification"]["passed"])
            self.assertEqual(len(report["verification_points"]), 7)


if __name__ == "__main__":
    unittest.main()
