"""Read-only pressure-step and beat-coverage audit of verified captures."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from bp_capture import decode, float32
from bp_oscillogram_study import analyze


PADDINGS = (0, 20, 40, 60)
STEP_MMHG = 5.0
NEIGHBORHOOD_SAMPLES = 40


def audit(path, upper_pressure):
    raw = path.read_bytes()
    capture = decode(raw.decode("utf-8-sig").splitlines())
    points = capture["points"]
    pressure = np.array([float32(row["p"]) for row in points])
    voltage = np.array([float32(row["v"]) for row in points])
    steps = np.flatnonzero(np.abs(np.diff(pressure)) >= STEP_MMHG) + 1
    eligible = (pressure >= 50) & (pressure < upper_pressure)
    near_step = np.zeros(len(points), dtype=bool)
    for index in steps:
        near_step[max(0, index - NEIGHBORHOOD_SAMPLES):
                  min(len(points), index + NEIGHBORHOOD_SAMPLES + 1)] = True

    header = capture["header"]
    slope = float32(header["slope"])
    intercept = float32(header["intercept"])
    sensitivity = []
    for padding in PADDINGS:
        study = analyze(capture, padding, upper_pressure)
        height = study.get("height", {})
        sensitivity.append({
            "padding_samples": padding,
            "status": study["status"],
            "clean_beats": study.get("clean_beats"),
            "occupied_bins": len(height.get("bins", [])),
            "screen": height.get("robustness", {}).get("screen"),
            "fitted_peak_mmhg": height.get("gaussian", {}).get("peak_mmhg"),
        })

    step_rows = []
    for index in steps:
        previous = float(pressure[index - 1])
        row = {
            "index": int(index),
            "elapsed_s": round(((points[int(index)]["t"] - points[0]["t"])
                                 & 0xFFFFFFFF) / 1000, 3),
            "pressure_before_mmhg": round(previous, 2),
            "pressure_at_mmhg": round(float(pressure[index]), 2),
            "delta_mmhg": round(float(pressure[index]) - previous, 2),
        }
        if index + 1 < len(points):
            row["net_after_25ms_mmhg"] = round(float(pressure[index + 1]) - previous, 2)
        if index + 4 < len(points):
            row["net_after_100ms_mmhg"] = round(float(pressure[index + 4]) - previous, 2)
        step_rows.append(row)

    return {
        "source": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "n": len(points),
        "raw_kind": header["raw_kind"],
        "calibration_slope_mmhg_per_v": slope,
        "calibration_intercept_mmhg": intercept,
        "max_pressure_voltage_affine_residual_mmhg": round(
            float(np.max(np.abs(pressure - (slope * voltage + intercept)))), 5),
        "pressure_band_mmhg": [50, upper_pressure],
        "band_samples": int(np.count_nonzero(eligible)),
        "samples_within_40_of_step_in_band": int(np.count_nonzero(eligible & near_step)),
        "steps": step_rows,
        "sensitivity": sensitivity,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--upper-pressure", type=int, default=130, choices=(130, 170))
    args = parser.parse_args()
    print(json.dumps([audit(path, args.upper_pressure) for path in args.captures],
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
