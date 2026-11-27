"""Research-only beat height/area oscillograms from verified cuff captures.

The per-beat height and area features are inspired by DOI
10.3389/fphys.2025.1611096. That study used 250 Hz patient data and invasive
references; this 40 Hz simulator diagnostic does not reproduce its BP model.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.signal import butter, find_peaks, sosfiltfilt

from bp_beat_analysis import estimate_pulse
from bp_capture import decode, float32


SAMPLE_RATE_HZ = 40
PRESSURE_STEP_MMHG = 5.0
STEP_PADDING_SAMPLES = 40
BIN_WIDTH_MMHG = 5
MIN_PEAK_BIN_BEATS = 3
MAX_OCCUPIED_GAP_MMHG = 15.0
MAX_JACKKNIFE_SHIFT_MMHG = 7.5


def _fit_gaussian(pressure, amplitude, scale, upper_pressure):
    def model(params):
        floor, height, center, width = params
        return floor + height * np.exp(-0.5 * ((pressure - center) / width) ** 2)

    start = [max(0.0, float(np.min(amplitude)) * 0.4),
             float(np.max(amplitude)), float(pressure[np.argmax(amplitude)]), 20.0]
    fit = least_squares(lambda params: (model(params) - amplitude) * scale,
                        start, bounds=([0, 0, 45, 5], [np.inf, np.inf, upper_pressure, 65]),
                        loss="soft_l1", f_scale=2.0)
    residual = float(np.sum((model(fit.x) - amplitude) ** 2))
    total = float(np.sum((amplitude - np.mean(amplitude)) ** 2))
    return {"peak_mmhg": round(float(fit.x[2]), 2),
            "r2": round(1.0 - residual / total, 3) if total > 0 else None,
            "at_upper_bound": bool(fit.x[2] >= upper_pressure - 0.5)}


def _feature_curve(beats, key, upper_pressure, bin_width_mmhg=BIN_WIDTH_MMHG):
    bins = []
    for low in range(50, upper_pressure, bin_width_mmhg):
        values = [beat[key] for beat in beats if low <= beat["pressure"] < low + bin_width_mmhg]
        if len(values) >= 2:
            bins.append({"pressure_mmhg": low + bin_width_mmhg / 2,
                         "count": len(values), "median": float(np.median(values))})
    if len(bins) < 8:
        return {"status": "insufficient_bins", "bins": bins}

    pressure = np.array([item["pressure_mmhg"] for item in bins])
    amplitude = np.array([item["median"] for item in bins])
    peak_idx = int(np.argmax(amplitude))
    peak = float(pressure[peak_idx])
    scale = 1000 if key == "height" else 10000
    fit = _fit_gaussian(pressure, amplitude, scale, upper_pressure)
    jackknife_centers = [
        _fit_gaussian(np.delete(pressure, i), np.delete(amplitude, i),
                      scale, upper_pressure)["peak_mmhg"]
        for i in range(len(bins))
    ]
    peak_bin_beats = bins[peak_idx]["count"]
    max_occupied_gap = float(np.max(np.diff(pressure)))
    max_jackknife_shift = max(abs(center - fit["peak_mmhg"])
                              for center in jackknife_centers)
    rejection_reasons = []
    if peak_bin_beats < MIN_PEAK_BIN_BEATS:
        rejection_reasons.append("weak_peak_support")
    if max_occupied_gap > MAX_OCCUPIED_GAP_MMHG:
        rejection_reasons.append("pressure_coverage_gap")
    if max_jackknife_shift > MAX_JACKKNIFE_SHIFT_MMHG:
        rejection_reasons.append("jackknife_unstable")
    low_ratio = float(amplitude[0] / amplitude[peak_idx])
    high_ratio = float(amplitude[-1] / amplitude[peak_idx])
    lower_bins = peak_idx
    upper_bins = len(bins) - peak_idx - 1
    complete = (lower_bins >= 2 and upper_bins >= 2 and
                pressure[-1] - peak >= 10 and peak - pressure[0] >= 10 and
                low_ratio < 0.8 and high_ratio < 0.8)
    peak_spread = abs(peak - fit["peak_mmhg"])
    model_consistent = (not fit["at_upper_bound"] and fit["r2"] is not None and
                        fit["r2"] >= 0.7 and peak_spread <= 7.5)
    status = ("incomplete_oscillogram" if not complete else
              "diagnostic_only" if model_consistent else "unstable_peak")
    return {"status": status,
            "bin_peak_mmhg": peak, "gaussian": fit,
            "robustness": {
                "screen": "reject" if rejection_reasons else "pass",
                "reasons": rejection_reasons,
                "peak_bin_beats": peak_bin_beats,
                "max_occupied_gap_mmhg": round(max_occupied_gap, 2),
                "jackknife_fit_range_mmhg": [min(jackknife_centers),
                                             max(jackknife_centers)],
                "jackknife_max_shift_mmhg": round(max_jackknife_shift, 2),
            },
            "peak_spread_mmhg": round(peak_spread, 2),
            "low_tail_ratio": round(low_ratio, 3),
            "high_tail_ratio": round(high_ratio, 3),
            "lower_bins": lower_bins, "upper_bins": upper_bins,
            "bins": [{"pressure_mmhg": item["pressure_mmhg"],
                      "count": item["count"], "median": round(item["median"], 7)}
                     for item in bins]}


def analyze(capture, step_padding_samples=STEP_PADDING_SAMPLES, upper_pressure=130,
            bin_width_mmhg=BIN_WIDTH_MMHG):
    if not 0 <= step_padding_samples <= 80:
        raise ValueError("step padding must be 0..80 samples")
    if upper_pressure not in (130, 170):
        raise ValueError("upper pressure must be 130 or 170 mmHg")
    if bin_width_mmhg not in (5, 10):
        raise ValueError("bin width must be 5 or 10 mmHg")
    if capture["header"]["calc"] not in (2, 3):
        return {"status": "calculation_incomplete", "bin_width_mmhg": bin_width_mmhg}
    pulse = estimate_pulse(capture)
    if pulse["status"] != "estimated":
        return {"status": "pulse_unreliable", "pulse": pulse,
                "bin_width_mmhg": bin_width_mmhg}

    points = capture["points"]
    pressure = np.array([float32(row["p"]) for row in points])
    voltage = np.array([float32(row["v"]) for row in points])
    frequency = pulse["dominant_hz"]
    if not 0.9 <= frequency <= 2.5:
        return {"status": "pulse_outside_study_band", "pulse": pulse,
                "bin_width_mmhg": bin_width_mmhg}

    sos = butter(3, [0.9, 2.5], btype="bandpass", fs=SAMPLE_RATE_HZ, output="sos")
    filtered = sosfiltfilt(sos, voltage)
    eligible = ((pressure >= 40) & (pressure <= 120) &
                (np.arange(len(points)) >= 80) &
                (np.arange(len(points)) < len(points) - 15))
    prominence = max(0.0005, 0.25 * (np.percentile(filtered[eligible], 95) -
                                    np.percentile(filtered[eligible], 5)))
    peaks, _ = find_peaks(filtered, prominence=prominence,
                          distance=round(0.65 * SAMPLE_RATE_HZ / frequency))
    troughs, _ = find_peaks(-filtered,
                            distance=round(0.5 * SAMPLE_RATE_HZ / frequency))
    steps = np.flatnonzero(np.abs(np.diff(pressure)) >= PRESSURE_STEP_MMHG) + 1
    beats = []
    for peak in peaks:
        at = int(np.searchsorted(troughs, peak))
        if at == 0 or at == len(troughs):
            continue
        left, right = int(troughs[at - 1]), int(troughs[at])
        length = right - left
        if not (80 <= peak < len(points) - 15 and
                0.6 * SAMPLE_RATE_HZ / frequency <= length <=
                1.5 * SAMPLE_RATE_HZ / frequency):
            continue
        cuff = float(np.median(pressure[left:right + 1]))
        if not 50 <= cuff < upper_pressure:
            continue
        if np.any((steps >= left - step_padding_samples) &
                  (steps <= right + step_padding_samples)):
            continue
        baseline = np.linspace(filtered[left], filtered[right], length + 1)
        pulse_wave = np.maximum(filtered[left:right + 1] - baseline, 0)
        beats.append({"pressure": cuff, "height": float(np.max(pulse_wave)),
                      "area": float(np.trapezoid(pulse_wave, dx=1 / SAMPLE_RATE_HZ))})

    if len(beats) < 20:
        return {"status": "insufficient_clean_beats", "pulse": pulse,
                "detected_peaks": len(peaks), "clean_beats": len(beats),
                "pressure_steps": len(steps), "bin_width_mmhg": bin_width_mmhg}
    height = _feature_curve(beats, "height", upper_pressure, bin_width_mmhg)
    area = _feature_curve(beats, "area", upper_pressure, bin_width_mmhg)
    status = height["status"]
    return {"status": status, "pulse": pulse,
            "detected_peaks": len(peaks), "clean_beats": len(beats),
            "pressure_steps": len(steps), "step_padding_samples": step_padding_samples,
            "upper_pressure_mmhg": upper_pressure,
            "bin_width_mmhg": bin_width_mmhg,
            "height": height, "area": area}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--step-padding-samples", type=int, default=STEP_PADDING_SAMPLES,
                        help="research sensitivity setting, default 40 samples")
    parser.add_argument("--upper-pressure", type=int, default=130, choices=(130, 170),
                        help="exclusive upper bound for beat bins; 170 for high-target captures")
    parser.add_argument("--bin-width", type=int, default=BIN_WIDTH_MMHG, choices=(5, 10),
                        help="pressure bin width in mmHg; default 5 preserves earlier reports")
    args = parser.parse_args()
    reports = []
    for path in args.captures:
        with path.open(encoding="utf-8-sig") as stream:
            capture = decode(stream)
        reports.append({"source": str(path),
                        **analyze(capture, args.step_padding_samples, args.upper_pressure,
                                  args.bin_width)})
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
