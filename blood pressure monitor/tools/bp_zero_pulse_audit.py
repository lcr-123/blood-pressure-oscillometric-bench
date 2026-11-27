"""Audit an uncalculated sealed-zero capture against its last valve pulse tick."""

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import bp_capture


def audit(path, last_tick):
    capture = bp_capture.decode(path.read_text(encoding="utf-8").splitlines())
    header, valve, points = capture["header"], capture["valve"], capture["points"]
    if (header["calc"] != 0 or header["raw_kind"] != 2 or
            valve["pulses"] < 2 or valve["period_min"] != 200 or
            valve["period_max"] != 200 or valve["on_min"] != 5 or
            valve["on_max"] != 5):
        raise ValueError("expected uncalculated 5ms/200ms sensor-voltage capture")
    if not points[0]["t"] <= last_tick <= points[-1]["t"]:
        raise ValueError("last pulse tick outside capture")

    slope = bp_capture.float32(header["slope"])
    voltage = [bp_capture.float32(point["v"]) for point in points]
    pressure = [bp_capture.float32(point["p"]) for point in points]
    groups = [[] for _ in range(8)]
    for index in range(1, len(points)):
        interval = (points[index]["t"] - points[index - 1]["t"]) & 0xFFFFFFFF
        if not 23 <= interval <= 27:
            raise ValueError("unexpected sampling interval")
        phase = (points[index]["t"] - last_tick) % 200
        groups[phase // 25].append((voltage[index] - voltage[index - 1]) * slope)

    return {
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        "firmware": header["firmware"],
        "points": len(points),
        "pulses": valve["pulses"],
        "last_pulse_tick_ms": last_tick,
        "pressure_range_mmhg": [min(pressure), max(pressure)],
        "voltage_range_v": [min(voltage), max(voltage)],
        "equivalent_peak_to_peak_mmhg": (max(voltage) - min(voltage)) * slope,
        "phase_delta_mmhg": [
            {"phase_ms": [bin_index * 25, bin_index * 25 + 24],
             "n": len(values), "median": statistics.median(values) if values else None,
             "min": min(values) if values else None,
             "max": max(values) if values else None}
            for bin_index, values in enumerate(groups)
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--last-tick", required=True, type=int)
    args = parser.parse_args()
    print(json.dumps(audit(args.capture, args.last_tick), indent=2))


if __name__ == "__main__":
    main()
