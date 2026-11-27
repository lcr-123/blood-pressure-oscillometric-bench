"""Audit a loaded, uncalculated valve-pulse capture against its MCU pulse tick."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import bp_capture


def audit(path, last_tick):
    capture = bp_capture.decode(path.read_text(encoding="utf-8").splitlines())
    header, valve, points = capture["header"], capture["valve"], capture["points"]
    pulses = valve["pulses"]
    if (header["calc"] != 0 or header["raw_kind"] != 2 or
            not 12 <= pulses <= 16 or valve["period_min"] != 200 or
            valve["period_max"] != 200 or
            valve["on_max"] != valve["on_min"] or
            not 1 <= valve["on_min"] <= 5 or not 150 <= len(points) <= 165):
        raise ValueError("expected complete loaded 1-5ms/200ms sensor-voltage capture")

    first_tick = (last_tick - (pulses - 1) * 200) & 0xFFFFFFFF
    start_tick = points[0]["t"]
    first_elapsed = (first_tick - start_tick) & 0xFFFFFFFF
    last_elapsed = (last_tick - start_tick) & 0xFFFFFFFF
    if not 900 <= first_elapsed <= 1150 or last_elapsed >= capture["duration_ms"]:
        raise ValueError("pulse ticks do not align with 1s baseline and 4s capture")

    slope = bp_capture.float32(header["slope"])
    baseline, pulse = [], []
    phase_bins = [[] for _ in range(8)]
    for index, point in enumerate(points):
        elapsed = (point["t"] - start_tick) & 0xFFFFFFFF
        pressure = bp_capture.float32(point["p"])
        voltage = bp_capture.float32(point["v"])
        sample = (elapsed, pressure, voltage)
        if elapsed < first_elapsed:
            baseline.append(sample)
        else:
            pulse.append(sample)
        if index == 0:
            continue
        interval = (point["t"] - points[index - 1]["t"]) & 0xFFFFFFFF
        if not 23 <= interval <= 27:
            raise ValueError("unexpected sampling interval")
        if first_elapsed <= elapsed <= last_elapsed + 200:
            prior = points[index - 1]
            phase = ((point["t"] - first_tick) & 0xFFFFFFFF) % 200
            phase_bins[phase // 25].append({
                "pressure": pressure - bp_capture.float32(prior["p"]),
                "voltage_equivalent": (voltage - bp_capture.float32(prior["v"])) * slope,
            })
    if len(baseline) < 30 or len(pulse) < 100:
        raise ValueError("baseline or pulse interval incomplete")

    def fitted_rate(samples):
        times = [sample[0] for sample in samples]
        pressures = [sample[1] for sample in samples]
        center_t, center_p = statistics.mean(times), statistics.mean(pressures)
        return 60000 * sum((t - center_t) * (p - center_p)
                           for t, p in zip(times, pressures)) / sum(
            (t - center_t) ** 2 for t in times)

    def segment(samples):
        return {"n": len(samples), "start_mmhg": samples[0][1],
                "end_mmhg": samples[-1][1],
                "change_mmhg": samples[-1][1] - samples[0][1],
                "duration_ms": samples[-1][0] - samples[0][0],
                "endpoint_rate_mmhg_min": (samples[-1][1] - samples[0][1]) *
                60000 / (samples[-1][0] - samples[0][0]),
                "fitted_rate_mmhg_min": fitted_rate(samples)}

    return {
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        "firmware": header["firmware"], "n": len(points), "pulses": pulses,
        "on_ms": valve["on_min"],
        "first_pulse_tick_ms": first_tick, "last_pulse_tick_ms": last_tick,
        "baseline": segment(baseline), "pulse_interval": segment(pulse),
        "phase_delta_mmhg": [
            {"phase_ms": [i * 25, i * 25 + 24], "n": len(values),
             "pressure_median": statistics.median(v["pressure"] for v in values) if values else None,
             "pressure_min": min((v["pressure"] for v in values), default=None),
             "voltage_equivalent_median": statistics.median(v["voltage_equivalent"] for v in values) if values else None,
             "voltage_equivalent_min": min((v["voltage_equivalent"] for v in values), default=None)}
            for i, values in enumerate(phase_bins)
        ],
        "limits": "One sensor and 25ms samples cannot identify physical cause or resolve a 1-5ms pulse.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--last-tick", required=True, type=int)
    args = parser.parse_args()
    print(json.dumps(audit(args.capture, args.last_tick), indent=2))


if __name__ == "__main__":
    main()
