"""Shared, label-blind development envelope extraction (no BP estimation).

The stability range is sensitivity to bin origin, not an accuracy interval.
All consumers must use these unrounded features and gates before formatting.
"""

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt, welch

from bp_capture import float32


FS = 40.0
BIN = 10
BIN_ORIGINS = (0.0, 2.5, 5.0, 7.5)
MAX_PEAK_SPAN_MMHG = 15.0


def _range(values):
    return [float(np.min(values)), float(np.max(values))] if len(values) else None


def extract(capture):
    """Return beats and diagnostics, or an explicit extraction abstention.

    Only calc state, MCU ticks, raw pressure and raw voltage are read. Header
    results, firmware envelope fields and simulator settings are never inputs.
    """
    points = capture["points"]
    n = len(points)
    result = {"status": "abstain", "reason": None, "sample_count": n,
              "beats": [], "rejection_counts": {
                  "no_bracketing_trough": 0, "geometry_or_period": 0,
                  "pressure_step_padding": 0, "cuff_pressure_out_of_range": 0,
                  "accepted": 0}}

    def fail(reason):
        result["reason"] = reason
        return result

    if capture["header"]["calc"] not in (2, 3) or n < 800:
        return fail("incomplete_calculation_or_capture")
    if any(((points[i]["t"] - points[i - 1]["t"]) & 0xffffffff) != 25
           for i in range(1, n)):
        return fail("irregular_mcu_ticks")
    pressure = np.array([float32(row["p"]) for row in points])
    voltage = np.array([float32(row["v"]) for row in points])
    if not np.all(np.isfinite(pressure)) or not np.all(np.isfinite(voltage)):
        return fail("nonfinite_input")
    eligible = ((np.arange(n) >= 80) & (np.arange(n) < n - 15) &
                (pressure >= 20) & (pressure <= 300))
    indices = np.flatnonzero(eligible)
    delta = np.abs(np.diff(pressure))
    steps = np.flatnonzero(delta >= 5) + 1
    result.update({
        "raw_pressure_range_mmhg": _range(pressure),
        "eligible_pressure_range_mmhg": _range(pressure[eligible]),
        "pressure_step_count_ge_5mmhg": int(len(steps)),
        "pressure_step_max_abs_delta_mmhg": float(np.max(delta)),
        "pressure_step_p99_abs_delta_mmhg": float(np.percentile(delta, 99)),
    })
    if len(indices) < 600 or np.ptp(pressure[eligible]) < 50:
        return fail("insufficient_pressure_span")
    # Edge pulses can repeatedly cross20 mmHg. Choose the longest complete
    # interval; never concatenate separated windows and invent PSD adjacency.
    windows = np.split(indices, np.flatnonzero(np.diff(indices) != 1) + 1)
    selected = max(windows, key=len)
    result.update({"eligible_window_count": len(windows),
                   "selected_window_indices": [int(selected[0]), int(selected[-1])],
                   "discarded_eligible_samples": len(indices) - len(selected)})
    if len(selected) < 600 or np.ptp(pressure[selected]) < 50:
        return fail("fragmented_pressure_window")
    eligible[:] = False
    eligible[selected] = True
    result["selected_pressure_range_mmhg"] = _range(pressure[selected])
    sos = butter(3, (0.9, 2.5), btype="bandpass", fs=FS, output="sos")
    filtered = sosfiltfilt(sos, voltage)
    segment = filtered[eligible]
    rms = float(np.sqrt(np.mean(segment * segment)))
    result["filtered_rms_v"] = rms
    if rms < 0.001:
        return fail("weak_periodic_signal")
    frequency, power = welch(segment, fs=FS, nperseg=512)
    band = (frequency >= 0.9) & (frequency <= 2.5)
    dominant = float(frequency[band][np.argmax(power[band])])
    spectral_ratio = float(np.max(power[band]) / max(np.median(power[band]), 1e-12))
    result.update({"dominant_frequency_hz": dominant,
                   "dominant_pulse_bpm": 60 * dominant,
                   "spectral_peak_to_median": spectral_ratio})
    if not 1.0 <= dominant <= 2.35:
        return fail("cadence_outside_validated_range")
    if spectral_ratio < 8:
        return fail("unreliable_cadence")
    prominence = max(0.0005, 0.25 * float(np.percentile(segment, 95) -
                                         np.percentile(segment, 5)))
    distance = round(0.65 * FS / dominant)
    all_peaks, _ = find_peaks(filtered, distance=distance)
    peaks, _ = find_peaks(filtered, prominence=prominence, distance=distance)
    troughs, _ = find_peaks(-filtered, distance=round(0.5 * FS / dominant))
    result.update({"prominence_threshold_v": prominence,
                   "peak_candidates_before_prominence": len(all_peaks),
                   "peak_candidates_after_prominence": len(peaks),
                   "approx_rejected_by_prominence": max(0, len(all_peaks) - len(peaks))})
    rejection = result["rejection_counts"]
    beats = result["beats"]
    for peak in peaks:
        at = int(np.searchsorted(troughs, peak))
        if at == 0 or at == len(troughs):
            rejection["no_bracketing_trough"] += 1
            continue
        left, right = int(troughs[at - 1]), int(troughs[at])
        length = right - left
        if not (80 <= left < peak < right < n - 15 and
                0.6 * FS / dominant <= length <= 1.5 * FS / dominant):
            rejection["geometry_or_period"] += 1
            continue
        if np.any((steps >= left - 40) & (steps <= right + 40)):
            rejection["pressure_step_padding"] += 1
            continue
        # A median alone can conceal an out-of-range part of a beat.
        if not np.all(eligible[left:right + 1]):
            rejection["cuff_pressure_out_of_range"] += 1
            continue
        cuff = float(np.median(pressure[left:right + 1]))
        baseline = np.linspace(filtered[left], filtered[right], length + 1)
        wave = np.maximum(filtered[left:right + 1] - baseline, 0)
        beats.append((cuff, float(np.max(wave)),
                      float(np.trapezoid(wave, dx=1 / FS))))
    rejection["accepted"] = len(beats)
    result["accepted_beat_pressure_range_mmhg"] = _range([beat[0] for beat in beats])
    if len(beats) < 20:
        return fail("insufficient_clean_beats")
    result.update(status="ready", reason=None)
    return result


def bin_beats(beats, origin=0.0):
    """Keep every occupied bin; only >=2-beat bins enter the envelope."""
    grouped = {}
    for beat in beats:
        low = float(np.floor((beat[0] - origin) / BIN) * BIN + origin)
        grouped.setdefault(low, []).append(beat)
    return [{"low_mmhg": low, "center_mmhg": low + BIN / 2,
             "count": len(members),
             "height_median_v": float(np.median([b[1] for b in members])),
             "area_median_v_s": float(np.median([b[2] for b in members])),
             "used_for_envelope": len(members) >= 2}
            for low, members in sorted(grouped.items())]


def ratio_crossing(pressures, amplitudes, peak_index, fraction, direction):
    """Descriptive interpolated crossing, never a validated SBP/DBP."""
    threshold = fraction * amplitudes[peak_index]
    indices = (range(peak_index + 1, len(pressures)) if direction == "high"
               else range(peak_index - 1, -1, -1))
    previous = peak_index
    for index in indices:
        if amplitudes[index] <= threshold:
            span = amplitudes[previous] - amplitudes[index]
            if span <= 0:
                return None
            weight = (amplitudes[previous] - threshold) / span
            return round(float(pressures[previous] +
                               weight * (pressures[index] - pressures[previous])), 2)
        previous = index
    return None


def summarize_bins(rows):
    """Evaluate both features using the same unrounded occupied bins."""
    qualified = [row for row in rows if row["used_for_envelope"]]
    p = np.array([row["center_mmhg"] for row in qualified])
    result = {"status": "abstain", "reason": None,
              "qualified_bin_count": len(qualified), "envelopes": {}}
    if len(qualified) < 6:
        result["reason"] = "insufficient_occupied_bins"
    elif np.max(np.diff(p)) > 20:
        result["reason"] = "pressure_coverage_gap"
    estimates = []
    for name, key in (("height", "height_median_v"), ("area", "area_median_v_s")):
        if not qualified:
            result["envelopes"][name] = {"qualified": False}
            continue
        values = np.array([row[key] for row in qualified])
        smooth = np.convolve(np.pad(values, (1, 1), mode="edge"),
                             (0.25, 0.5, 0.25), mode="valid")
        peak = int(np.argmax(smooth))
        amplitude = float(smooth[peak])
        low_ratio = float(smooth[0] / amplitude) if amplitude > 0 else None
        high_ratio = float(smooth[-1] / amplitude) if amplitude > 0 else None
        reason = None
        if peak < 2 or len(p) - peak - 1 < 2 or qualified[peak]["count"] < 3:
            reason = "incomplete_or_weak_peak"
        elif amplitude < 0.001 or low_ratio >= 0.8 or high_ratio >= 0.8:
            reason = "incomplete_envelope_tails"
        # Distinct, comparable local maxima cannot define a unique peak.
        local_peaks, _ = find_peaks(smooth)
        competing = [int(i) for i in local_peaks if
                     abs(p[i] - p[peak]) >= 30 and smooth[i] >= 0.9 * amplitude]
        if competing:
            reason = reason or "ambiguous_envelope_peak"
        high_crossing = ratio_crossing(p, smooth, peak, 0.5, "high")
        low_crossing = ratio_crossing(p, smooth, peak, 0.6, "low")
        result["envelopes"][name] = {
            "qualified": True, "reason": reason,
            "peak_center_mmhg": float(p[peak]), "peak_smoothed": amplitude,
            "peak_bin_beats": qualified[peak]["count"],
            "low_edge_mmhg": float(p[0]), "high_edge_mmhg": float(p[-1]),
            "low_edge_ratio": low_ratio, "high_edge_ratio": high_ratio,
            "high_side_span_mmhg": float(p[-1] - p[peak]),
            "high_side_qualified_bins": len(p) - peak,
            "high_50pct_crossing_exists": high_crossing is not None,
            "high_50pct": high_crossing, "low_60pct": low_crossing,
            "competing_peak_centers_mmhg": [float(p[i]) for i in competing],
            "smoothed_values": smooth.tolist(),
        }
        result["reason"] = result["reason"] or reason
        estimates.append(float(p[peak]))
    if len(estimates) == 2:
        if abs(estimates[0] - estimates[1]) > 10:
            result["reason"] = result["reason"] or "height_area_peak_disagreement"
        result["candidate_peak_mmhg"] = float(np.mean(estimates))
        result["height_area_peaks_mmhg"] = estimates
    if result["reason"] is None:
        result["status"] = "envelope_candidate"
    return result


def assess_stability(beats):
    """Four fixed origins; failure is retained rather than choosing the best."""
    variants = []
    peaks = []
    for origin in BIN_ORIGINS:
        summary = summarize_bins(bin_beats(beats, origin))
        variants.append({"origin_mmhg": origin, **summary})
        peaks.extend(summary.get("height_area_peaks_mmhg", []))
    span = max(peaks) - min(peaks) if peaks else None
    reason = None
    if any(row["status"] != "envelope_candidate" for row in variants):
        reason = "bin_origin_gate_failed"
    elif span > MAX_PEAK_SPAN_MMHG:
        reason = "bin_origin_peak_unstable"
    return {"status": "pass" if reason is None else "reject", "reason": reason,
            "peak_range_mmhg": [min(peaks), max(peaks)] if peaks else None,
            "peak_span_mmhg": span, "max_allowed_span_mmhg": MAX_PEAK_SPAN_MMHG,
            "meaning": "bin-origin sensitivity only; not an accuracy interval",
            "variants": variants}
