"""Offline raw-voltage cadence, envelope, and capture-capacity diagnostics.

Input is a complete bp.capture/1, /2 or /3 export. This research tool never
communicates with the board and its candidates are not blood-pressure results.
"""

import argparse
import json
import math
from pathlib import Path
from statistics import median

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt, welch

from bp_capture import decode, float32


SAMPLE_INTERVAL_MS = 25
CAPTURE_CAPACITY = 2800
CAPACITY_BY_FIRMWARE = {"STACK_WATERMARK_20261027": 2800,
                        "CAPTURE_COMPACT_20261028": 3300,
                        "TARGET275_CAPTURE_20261105": 3300,
                        "CAPTURE4200_20261105": 4200}
RAW_BAND_HZ = (0.9, 4.0)


def estimate_pulse(capture):
    """Estimate periodic voltage cadence without a reference BPM or BP result."""
    points = capture["points"]
    if any((points[i]["t"] - points[i - 1]["t"]) & 0xFFFFFFFF != SAMPLE_INTERVAL_MS
           for i in range(1, len(points))):
        return {"status": "irregular_sampling"}
    pressure = np.array([float32(row["p"]) for row in points])
    voltage = np.array([float32(row["v"]) for row in points])
    indices = np.arange(len(points))
    eligible = indices[(indices >= 80) & (indices < len(points) - 15) &
                       (pressure >= 40.0) & (pressure <= 120.0)]
    if len(eligible) < 512:
        return {"status": "insufficient_samples", "eligible_count": len(eligible)}

    sample_rate = 1000 / SAMPLE_INTERVAL_MS
    sos = butter(3, RAW_BAND_HZ, btype="bandpass", fs=sample_rate, output="sos")
    filtered = sosfiltfilt(sos, voltage)
    segment = filtered[eligible[0]:eligible[-1] + 1]
    frequency, power = welch(segment, fs=sample_rate, nperseg=512)
    band = (frequency >= RAW_BAND_HZ[0]) & (frequency <= RAW_BAND_HZ[1])
    band_frequency, band_power = frequency[band], power[band]
    best = int(np.argmax(band_power))
    dominant_hz = float(band_frequency[best])
    spectral_ratio = float(band_power[best] / max(np.median(band_power), 1e-12))
    split_frequencies = []
    for half in np.array_split(segment, 2):
        half_frequency, half_power = welch(half, fs=sample_rate,
                                          nperseg=min(512, len(half)))
        half_band = (half_frequency >= RAW_BAND_HZ[0]) & (half_frequency <= RAW_BAND_HZ[1])
        split_frequencies.append(float(half_frequency[half_band]
                                       [np.argmax(half_power[half_band])]))

    prominence = max(0.0005, 0.35 * (np.percentile(segment, 95) -
                                     np.percentile(segment, 5)))
    peaks, _ = find_peaks(segment, distance=max(1, round(0.65 * sample_rate /
                                                        dominant_hz)),
                          prominence=prominence)
    intervals = np.diff(peaks) * SAMPLE_INTERVAL_MS
    expected_ms = 1000 / dominant_hz
    cadence_fraction = (float(np.mean(np.abs(intervals - expected_ms) <=
                                      0.2 * expected_ms)) if len(intervals) else 0.0)
    rms_v = float(np.sqrt(np.mean(segment * segment)))
    consistent_halves = all(abs(value - dominant_hz) <= 0.2 * dominant_hz
                            for value in split_frequencies)
    status = ("estimated" if rms_v >= 0.001 and spectral_ratio >= 8 and
              len(peaks) >= 8 and cadence_fraction >= 0.7 and consistent_halves
              else "signal_unreliable")
    report = {"status": status, "eligible_count": len(eligible),
              "pressure_range_mmhg": [40, 120], "peak_count": len(peaks),
              "cadence_fraction": round(cadence_fraction, 3),
              "spectral_ratio": round(spectral_ratio, 2),
              "bandpass_rms_v": round(rms_v, 6),
              "dominant_hz": round(dominant_hz, 3),
              "split_dominant_hz": [round(value, 3) for value in split_frequencies]}
    if len(intervals):
        report["median_interpeak_ms"] = int(median(intervals))
    if status == "estimated":
        report["pulse_bpm"] = round(dominant_hz * 60)
    return report


def raw_cadence(capture, bpm):
    if not 30 <= bpm <= 240:
        raise ValueError("bpm must be 30..240")
    points = capture["points"]
    if any((points[i]["t"] - points[i - 1]["t"]) & 0xFFFFFFFF != SAMPLE_INTERVAL_MS
           for i in range(1, len(points))):
        return {"status": "irregular_sampling"}

    pressure = np.array([float32(row["p"]) for row in points])
    voltage = np.array([float32(row["v"]) for row in points])
    indices = np.arange(len(points))
    eligible = indices[(indices >= 80) & (indices < len(points) - 15) &
                       (pressure >= 40.0) & (pressure <= 120.0)]
    if len(eligible) < 256:
        return {"status": "insufficient_samples", "eligible_count": len(eligible)}

    # Filter the complete trace so the pressure-window boundaries do not create edges.
    sos = butter(3, RAW_BAND_HZ, btype="bandpass", fs=1000 / SAMPLE_INTERVAL_MS,
                 output="sos")
    filtered = sosfiltfilt(sos, voltage)
    segment = filtered[eligible[0]:eligible[-1] + 1]
    prominence = max(0.0005, 0.35 * (np.percentile(segment, 95) -
                                     np.percentile(segment, 5)))
    expected_samples = 60000 / (bpm * SAMPLE_INTERVAL_MS)
    peaks, _ = find_peaks(segment, distance=max(1, round(0.65 * expected_samples)),
                          prominence=prominence)
    if len(peaks) < 5:
        return {"status": "insufficient_peaks", "peak_count": len(peaks),
                "eligible_count": len(eligible)}

    intervals = np.diff(peaks) * SAMPLE_INTERVAL_MS
    cadence_fraction = float(np.mean(np.abs(intervals - 60000 / bpm) <= 12000 / bpm))
    frequency, power = welch(segment, fs=1000 / SAMPLE_INTERVAL_MS,
                             nperseg=min(512, len(segment)))
    band = (frequency >= RAW_BAND_HZ[0]) & (frequency <= RAW_BAND_HZ[1])
    dominant_hz = float(frequency[band][np.argmax(power[band])])
    expected_hz = bpm / 60
    if not RAW_BAND_HZ[0] <= expected_hz <= RAW_BAND_HZ[1]:
        status = "expected_outside_band"
    elif cadence_fraction >= 0.7 and abs(dominant_hz - expected_hz) <= 0.2 * expected_hz:
        status = "cadence_detected"
    else:
        status = "cadence_unreliable"
    return {"status": status, "eligible_count": len(eligible),
            "pressure_range_mmhg": [40, 120], "peak_count": len(peaks),
            "median_interpeak_ms": int(median(intervals)),
            "cadence_fraction": round(cadence_fraction, 3),
            "dominant_hz": round(dominant_hz, 3),
            "dominant_bpm": round(dominant_hz * 60, 1),
            "prominence_v": round(prominence, 6)}


def beat_candidates(capture, bpm):
    if capture["header"]["calc"] not in (2, 3):
        raise ValueError("completed envelope calculation required")
    if not 30 <= bpm <= 240:
        raise ValueError("bpm must be 30..240")
    points = capture["points"]
    pressure = np.array([float32(row["p"]) for row in points])
    smooth = np.array([float32(row["s"]) for row in points])
    start, end = 80, len(points) - 15
    if end <= start:
        raise ValueError("capture too short for transient exclusions")

    beat_samples = 60000 / (bpm * SAMPLE_INTERVAL_MS)
    segment = smooth[start:end]
    prominence = max(0.0005, 0.1 * (np.percentile(segment, 95) - np.percentile(segment, 10)))
    peaks, _ = find_peaks(segment, distance=max(1, round(0.65 * beat_samples)),
                          prominence=prominence)
    indices = [start + int(index) for index in peaks
               if pressure[start + index] >= 15.0]
    if len(indices) < 5:
        return {"status": "insufficient_peaks", "peak_count": len(indices)}

    intervals = np.diff(indices)
    cadence_fraction = float(np.mean(np.abs(intervals - beat_samples) <= 0.2 * beat_samples))
    diagnostics = {"peak_count": len(indices),
                   "median_interpeak_ms": int(median(intervals) * SAMPLE_INTERVAL_MS),
                   "cadence_fraction": round(cadence_fraction, 3),
                   "prominence_v": round(prominence, 6)}
    if cadence_fraction < 0.7:
        return {"status": "cadence_unreliable", **diagnostics}

    pressures = [float(median(pressure[max(0, i - 4):i + 5])) for i in indices]
    amplitudes = [float(smooth[i]) for i in indices]
    curve = [median(amplitudes[max(0, j - 2):min(len(indices), j + 3)])
             for j in range(len(indices))]
    eligible = [j for j, value in enumerate(pressures) if value >= 40.0]
    if not eligible:
        return {"status": "no_map_region", **diagnostics}
    map_j = max(eligible, key=lambda j: curve[j])
    threshold_sbp = 0.5 * curve[map_j]
    threshold_dbp = 0.6 * curve[map_j]
    sbp_j = next((j for j in range(map_j) if curve[j] >= threshold_sbp), None)
    dbp_j = next((j for j in range(map_j + 1, len(indices) - 1)
                  if curve[j] <= threshold_dbp and curve[j + 1] <= threshold_dbp), None)
    return {
        "status": "diagnostic_only",
        **diagnostics,
        "map_candidate": {"sample": indices[map_j], "pressure_mmhg": round(pressures[map_j], 2),
                          "amplitude_v": round(curve[map_j], 6)},
        "sbp_candidate_mmhg": round(pressures[sbp_j], 2) if sbp_j is not None else None,
        "dbp_candidate_mmhg": round(pressures[dbp_j], 2) if dbp_j is not None else None,
    }


def capacity_projection(capture, current_target, future_targets, capacity=CAPTURE_CAPACITY):
    if not math.isfinite(current_target) or current_target <= 0:
        raise ValueError("current target must be positive and finite")
    if type(capacity) is not int or capacity < 1:
        raise ValueError("capture capacity must be a positive integer")
    points = capture["points"]
    if len(points) < 2:
        raise ValueError("at least two samples required for capacity projection")
    start = float32(points[0]["p"])
    end = float32(points[-1]["p"])
    duration_s = capture["duration_ms"] / 1000
    if duration_s <= 0 or start <= end:
        raise ValueError("positive deflation rate required for projection")
    rate = (start - end) / duration_s
    projections = []
    for target in future_targets:
        if not math.isfinite(target) or target < current_target:
            raise ValueError("future target must be finite and >= current target")
        extra = round((target - current_target) / rate * 1000 / SAMPLE_INTERVAL_MS)
        projected = len(points) + extra
        projections.append({"target_mmhg": target, "projected_samples": projected,
                            "remaining_samples": capacity - projected})
    return {"observed_samples": len(points), "start_pressure_mmhg": round(start, 2),
            "end_pressure_mmhg": round(end, 2), "mean_rate_mmhg_s": round(rate, 3),
            "current_target_mmhg": current_target,
            "capture_capacity": capacity,
            "projections": projections}


def analyze(path, bpm=None, current_target=None, future_targets=None, capacity_override=None):
    with path.open(encoding="utf-8-sig") as stream:
        capture = decode(stream)
    report = {"source": str(path), "schema": capture["header"]["schema"],
              "note": "host research diagnostics; not a BP result or capacity guarantee",
              "pulse_estimate": estimate_pulse(capture)}
    if bpm is not None:
        report["raw_cadence"] = raw_cadence(capture, bpm)
        report["beats"] = beat_candidates(capture, bpm)
    if current_target is not None or future_targets is not None:
        if current_target is None or future_targets is None:
            raise ValueError("current target and future targets must be provided together")
        firmware = capture["header"]["firmware"]
        capacity = CAPACITY_BY_FIRMWARE.get(firmware)
        if capacity is None:
            if capacity_override is None:
                raise ValueError(f"unknown firmware capacity for {firmware}; specify --capacity")
            capacity = capacity_override
        elif capacity_override is not None and capacity_override != capacity:
            raise ValueError(f"capacity for {firmware} is {capacity}, not {capacity_override}")
        report["capacity"] = capacity_projection(capture, current_target, future_targets, capacity)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--bpm", type=int, help="optional reference for legacy diagnostics only")
    parser.add_argument("--current-target", type=float)
    parser.add_argument("--future-targets", type=float, nargs="+")
    parser.add_argument("--capacity", type=int, help="required for unknown firmware markers")
    args = parser.parse_args()
    if (args.current_target is None) != (args.future_targets is None):
        parser.error("--current-target and --future-targets must be provided together")
    reports = [analyze(path, args.bpm, args.current_target, args.future_targets, args.capacity)
               for path in args.captures]
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
