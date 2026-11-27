#!/usr/bin/env python3
"""Fit and verify a pressure-sensor calibration without touching hardware.

The normalized input contract intentionally does not know whether samples came
from EK-OmniProbe, a CSV export, or the deterministic simulator.  Hardware
adapters must produce ``Sample`` records and are kept outside this module.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


REPORT_SCHEMA = "pressure-calibration-report/v1"
MMHG_PER_KPA = 7.50062
VALID_STAGES = frozenset({"calibration", "verification"})


@dataclass(frozen=True)
class Sample:
    stage: str
    reference_mmhg: float
    sensor_value: float


@dataclass(frozen=True)
class LinearModel:
    slope_mmhg_per_unit: float
    intercept_mmhg: float
    calibration_rmse_mmhg: float
    calibration_r_squared: float
    zero_voltage_v: float | None
    sensitivity_v_per_kpa: float | None

    def predict(self, sensor_value: float) -> float:
        return self.slope_mmhg_per_unit * sensor_value + self.intercept_mmhg


@dataclass(frozen=True)
class PointResult:
    stage: str
    reference_mmhg: float
    sample_count: int
    sensor_mean: float
    sensor_stdev: float
    predicted_mmhg: float
    error_mmhg: float
    absolute_error_mmhg: float
    passed: bool | None


@dataclass(frozen=True)
class AnalysisResult:
    model: LinearModel
    calibration_points: tuple[PointResult, ...]
    verification_points: tuple[PointResult, ...]
    tolerance_mmhg: float
    verification_rmse_mmhg: float
    verification_max_abs_error_mmhg: float
    passed: bool


def _require_finite(value: float, field_name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite, got {value!r}")


def validate_samples(samples: Sequence[Sample]) -> None:
    if not samples:
        raise ValueError("at least one sample is required")

    stages = set()
    for sample in samples:
        if sample.stage not in VALID_STAGES:
            raise ValueError(
                f"stage must be one of {sorted(VALID_STAGES)}, got {sample.stage!r}"
            )
        _require_finite(sample.reference_mmhg, "reference_mmhg")
        _require_finite(sample.sensor_value, "sensor_value")
        stages.add(sample.stage)

    missing_stages = VALID_STAGES - stages
    if missing_stages:
        raise ValueError(f"missing sample stage(s): {sorted(missing_stages)}")


def _group_samples(samples: Iterable[Sample], stage: str) -> list[tuple[float, list[float]]]:
    grouped: dict[float, list[float]] = {}
    for sample in samples:
        if sample.stage == stage:
            grouped.setdefault(sample.reference_mmhg, []).append(sample.sensor_value)
    return sorted(grouped.items(), key=lambda item: item[0])


def fit_linear_model(samples: Sequence[Sample], sensor_unit: str) -> LinearModel:
    validate_samples(samples)
    calibration_groups = _group_samples(samples, "calibration")
    if len(calibration_groups) < 2:
        raise ValueError("at least two distinct calibration pressures are required")

    x_values = [statistics.fmean(values) for _, values in calibration_groups]
    y_values = [reference for reference, _ in calibration_groups]
    x_mean = statistics.fmean(x_values)
    y_mean = statistics.fmean(y_values)
    denominator = sum((value - x_mean) ** 2 for value in x_values)
    if denominator <= 0.0:
        raise ValueError("calibration sensor values have zero span")

    slope = sum(
        (x_value - x_mean) * (y_value - y_mean)
        for x_value, y_value in zip(x_values, y_values)
    ) / denominator
    if slope <= 0.0:
        raise ValueError(f"calibration slope must be positive, got {slope}")

    intercept = y_mean - slope * x_mean
    residuals = [
        slope * x_value + intercept - y_value
        for x_value, y_value in zip(x_values, y_values)
    ]
    calibration_rmse = math.sqrt(statistics.fmean(error**2 for error in residuals))
    total_sum_squares = sum((value - y_mean) ** 2 for value in y_values)
    residual_sum_squares = sum(error**2 for error in residuals)
    r_squared = (
        1.0 - residual_sum_squares / total_sum_squares
        if total_sum_squares > 0.0
        else 1.0
    )

    unit_is_voltage = sensor_unit.strip().lower() in {"v", "volt", "volts"}
    zero_voltage = -intercept / slope if unit_is_voltage else None
    sensitivity = MMHG_PER_KPA / slope if unit_is_voltage else None

    return LinearModel(
        slope_mmhg_per_unit=slope,
        intercept_mmhg=intercept,
        calibration_rmse_mmhg=calibration_rmse,
        calibration_r_squared=r_squared,
        zero_voltage_v=zero_voltage,
        sensitivity_v_per_kpa=sensitivity,
    )


def _summarize_points(
    samples: Sequence[Sample],
    stage: str,
    model: LinearModel,
    tolerance_mmhg: float,
) -> tuple[PointResult, ...]:
    results: list[PointResult] = []
    for reference, values in _group_samples(samples, stage):
        sensor_mean = statistics.fmean(values)
        sensor_stdev = statistics.stdev(values) if len(values) > 1 else 0.0
        predicted = model.predict(sensor_mean)
        error = predicted - reference
        results.append(
            PointResult(
                stage=stage,
                reference_mmhg=reference,
                sample_count=len(values),
                sensor_mean=sensor_mean,
                sensor_stdev=sensor_stdev,
                predicted_mmhg=predicted,
                error_mmhg=error,
                absolute_error_mmhg=abs(error),
                passed=(abs(error) <= tolerance_mmhg) if stage == "verification" else None,
            )
        )
    return tuple(results)


def analyze_samples(
    samples: Sequence[Sample],
    *,
    sensor_unit: str,
    tolerance_mmhg: float,
) -> AnalysisResult:
    _require_finite(tolerance_mmhg, "tolerance_mmhg")
    if tolerance_mmhg <= 0.0:
        raise ValueError("tolerance_mmhg must be greater than zero")

    model = fit_linear_model(samples, sensor_unit)
    calibration_points = _summarize_points(
        samples, "calibration", model, tolerance_mmhg
    )
    verification_points = _summarize_points(
        samples, "verification", model, tolerance_mmhg
    )
    if not verification_points:
        raise ValueError("at least one verification pressure is required")

    verification_rmse = math.sqrt(
        statistics.fmean(point.error_mmhg**2 for point in verification_points)
    )
    verification_max_error = max(
        point.absolute_error_mmhg for point in verification_points
    )
    passed = all(point.passed is True for point in verification_points)

    return AnalysisResult(
        model=model,
        calibration_points=calibration_points,
        verification_points=verification_points,
        tolerance_mmhg=tolerance_mmhg,
        verification_rmse_mmhg=verification_rmse,
        verification_max_abs_error_mmhg=verification_max_error,
        passed=passed,
    )


def generate_simulated_samples(
    *,
    seed: int,
    samples_per_calibration_point: int = 20,
    samples_per_verification_point: int = 12,
) -> list[Sample]:
    if samples_per_calibration_point < 1 or samples_per_verification_point < 1:
        raise ValueError("sample counts must be positive")

    generator = random.Random(seed)
    references = (0.0, 50.0, 100.0, 150.0, 200.0, 250.0, 300.0)
    true_zero_voltage_v = 0.5
    true_sensitivity_v_per_kpa = 0.1
    noise_stdev_v = 0.0015
    samples: list[Sample] = []

    for stage, sample_count in (
        ("calibration", samples_per_calibration_point),
        ("verification", samples_per_verification_point),
    ):
        for reference in references:
            ideal_voltage = (
                true_zero_voltage_v
                + (reference / MMHG_PER_KPA) * true_sensitivity_v_per_kpa
            )
            for _ in range(sample_count):
                samples.append(
                    Sample(
                        stage=stage,
                        reference_mmhg=reference,
                        sensor_value=ideal_voltage
                        + generator.gauss(0.0, noise_stdev_v),
                    )
                )
    return samples


def read_samples_csv(path: Path) -> list[Sample]:
    if not path.is_file():
        raise FileNotFoundError(f"input CSV not found: {path}")

    samples: list[Sample] = []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"stage", "reference_mmhg", "sensor_value"}
        missing = required - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"input CSV is missing columns: {sorted(missing)}")
        for row_number, row in enumerate(reader, start=2):
            try:
                samples.append(
                    Sample(
                        stage=row["stage"].strip().lower(),
                        reference_mmhg=float(row["reference_mmhg"]),
                        sensor_value=float(row["sensor_value"]),
                    )
                )
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError(f"invalid CSV row {row_number}: {error}") from error
    validate_samples(samples)
    return samples


def write_reports(
    output_directory: Path,
    result: AnalysisResult,
    *,
    mode: str,
    sensor_unit: str,
) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / "calibration_report.json"
    csv_path = output_directory / "calibration_points.csv"

    report = {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "hardware_operated": False if mode == "simulation" else None,
        "sensor_unit": sensor_unit,
        "model": asdict(result.model),
        "verification": {
            "tolerance_mmhg": result.tolerance_mmhg,
            "rmse_mmhg": result.verification_rmse_mmhg,
            "max_abs_error_mmhg": result.verification_max_abs_error_mmhg,
            "passed": result.passed,
        },
        "calibration_points": [asdict(point) for point in result.calibration_points],
        "verification_points": [asdict(point) for point in result.verification_points],
    }
    with json_path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    field_names = list(asdict(result.calibration_points[0]).keys())
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=field_names)
        writer.writeheader()
        for point in (*result.calibration_points, *result.verification_points):
            writer.writerow(asdict(point))

    return json_path, csv_path


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    simulate = subparsers.add_parser(
        "simulate", help="run a deterministic dry run without opening hardware"
    )
    simulate.add_argument("--seed", type=int, default=20260917)
    simulate.add_argument("--tolerance-mmhg", type=float, default=1.0)
    simulate.add_argument("--sensor-unit", default="V")
    simulate.add_argument(
        "--output-dir", type=Path, default=Path("output/calibration/dry-run")
    )

    analyze = subparsers.add_parser("analyze", help="analyze a normalized sample CSV")
    analyze.add_argument("--input", type=Path, required=True)
    analyze.add_argument("--tolerance-mmhg", type=float, default=2.0)
    analyze.add_argument("--sensor-unit", default="V")
    analyze.add_argument(
        "--output-dir", type=Path, default=Path("output/calibration/analyzed")
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args(argv)

    if arguments.command == "simulate":
        samples = generate_simulated_samples(seed=arguments.seed)
        mode = "simulation"
    elif arguments.command == "analyze":
        samples = read_samples_csv(arguments.input)
        mode = "csv"
    else:  # pragma: no cover - argparse enforces the choices.
        parser.error(f"unsupported command: {arguments.command}")

    result = analyze_samples(
        samples,
        sensor_unit=arguments.sensor_unit,
        tolerance_mmhg=arguments.tolerance_mmhg,
    )
    json_path, csv_path = write_reports(
        arguments.output_dir,
        result,
        mode=mode,
        sensor_unit=arguments.sensor_unit,
    )
    summary = {
        "mode": mode,
        "hardware_operated": False if mode == "simulation" else None,
        "passed": result.passed,
        "verification_rmse_mmhg": result.verification_rmse_mmhg,
        "verification_max_abs_error_mmhg": result.verification_max_abs_error_mmhg,
        "json_report": str(json_path.resolve()),
        "csv_report": str(csv_path.resolve()),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
