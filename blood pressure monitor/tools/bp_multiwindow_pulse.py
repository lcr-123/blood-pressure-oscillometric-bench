"""Read-only, label-free comparison of 256-point pulse FFT windows.

This is a host research diagnostic. It never connects to serial hardware and
does not replace the production pulse algorithm or validate a BP result.
"""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np

from bp_beat_analysis import estimate_pulse
from bp_capture import decode, float32


WINDOW = 256
SAMPLE_MS = 25
LOW_PRESSURE = 40.0
HIGH_PRESSURE = 120.0


def window_fft(voltage):
    """Mirror the firmware's detrend, Hann window and 0.9..4 Hz bin choice."""
    if len(voltage) != WINDOW:
        raise ValueError("FFT window must contain 256 samples")
    indices = np.arange(WINDOW)
    detrended = voltage - np.polyval(np.polyfit(indices, voltage, 1), indices)
    rms = float(np.sqrt(np.mean(detrended * detrended)))
    magnitudes = np.abs(np.fft.rfft(detrended * np.hanning(WINDOW)))
    band = magnitudes[6:26]
    peak_bin = int(np.argmax(band)) + 6
    # The C implementation selects sorted[band_count / 2], not NumPy's
    # average of the two middle entries for an even-sized band.
    noise = float(np.sort(band)[len(band) // 2])
    peak = float(magnitudes[peak_bin])
    return {"bin": peak_bin, "bpm": int(peak_bin * 40 * 60 / WINDOW + 0.5),
            "peak_magnitude": round(peak, 6), "noise_magnitude": round(noise, 6),
            "detrended_rms_v": round(rms, 6),
            "gate_pass": rms >= 0.001 and peak >= 0.0008 and peak >= 3 * noise}


def analyze_capture(capture, stride=128):
    if stride not in (128, 256):
        raise ValueError("stride must be 128 or 256")
    points = capture["points"]
    if any(((points[i]["t"] - points[i - 1]["t"]) & 0xFFFFFFFF) != SAMPLE_MS
           for i in range(1, len(points))):
        return {"status": "irregular_sampling", "windows": [], "candidate_bpm": None}
    pressures = np.array([float32(row["p"]) for row in points])
    voltages = np.array([float32(row["v"]) for row in points])
    first_window = window_fft(voltages[:WINDOW]) if len(points) >= WINDOW else None
    # Match the existing label-free diagnostic's first-80 / last-15 exclusion.
    valid_starts = [i for i in range(80, len(points) - 15 - WINDOW + 1)
                    if np.all((pressures[i:i + WINDOW] >= LOW_PRESSURE) &
                              (pressures[i:i + WINDOW] <= HIGH_PRESSURE))]
    windows = []
    if valid_starts:
        for start in range(valid_starts[0], len(points) - 15 - WINDOW + 1, stride):
            segment = pressures[start:start + WINDOW]
            if np.any((segment < LOW_PRESSURE) | (segment > HIGH_PRESSURE)):
                continue
            result = window_fft(voltages[start:start + WINDOW])
            result.update(start_index=start, pressure_start_mmhg=round(float(segment[0]), 2),
                          pressure_end_mmhg=round(float(segment[-1]), 2))
            windows.append(result)
    passing = [row["bin"] for row in windows if row["gate_pass"]]
    peak_bin, votes = Counter(passing).most_common(1)[0] if passing else (None, 0)
    support = votes / len(passing) if passing else 0.0
    candidate = (int(peak_bin * 40 * 60 / WINDOW + 0.5)
                 if len(passing) >= 3 and support >= 0.7 else None)
    return {"status": "candidate" if candidate is not None else "no_consensus",
            "first_window": first_window, "windows": windows,
            "passing_windows": len(passing), "modal_support": round(support, 3),
            "candidate_bpm": candidate}


def analyze_file(path, strides=(128, 256)):
    raw = path.read_bytes()
    capture = decode(raw.decode("utf-8-sig").splitlines())
    try:
        source = path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        source = str(path)
    return {"source": source, "source_sha256": hashlib.sha256(raw).hexdigest(),
            "samples": len(capture["points"]), "calc_state": capture["header"]["calc"],
            "independent_label_free": estimate_pulse(capture),
            "strides": {str(stride): analyze_capture(capture, stride) for stride in strides}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = {"method": "strict decode; exact 25 ms MCU ticks; 256-point detrended Hann FFT; "
                         "all samples in 40..120 mmHg; exclude first 80 and last 15; "
                         "0.9..4 Hz maximum bin with firmware amplitude gate and "
                         "exploratory 0.001 V detrended RMS floor (not bandpass RMS); "
                         "at least three passing windows and 70% modal-bin support; "
                         "128-point windows overlap and votes are not independent beats",
              "captures": [analyze_file(path) for path in args.captures]}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
