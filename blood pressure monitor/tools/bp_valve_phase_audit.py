"""Read-only valve command alignment; /4 exact trace, /2-/3 inferred schedule."""

import argparse
import json
from pathlib import Path
import statistics
from bisect import bisect_right

from bp_capture import decode, float32


def summarize(values):
    ordered = sorted(values)
    if not ordered:
        return {"n": 0}
    return {
        "n": len(ordered),
        "median_mmhg": round(statistics.median(ordered), 3),
        "min_mmhg": round(ordered[0], 3),
        "max_mmhg": round(ordered[-1], 3),
        "falls_ge5": sum(value <= -5.0 for value in ordered),
        "rises_ge5": sum(value >= 5.0 for value in ordered),
    }


def audit_timing(capture, lower, upper):
    """Use measured command edges, never tick modulo a nominal period."""
    if (capture['timing'] is None or not capture['timing']['complete'] or
            not capture['pulses']):
        raise ValueError('complete nonempty GPIO command timing required')
    points = capture['points']
    first = points[0]['t']

    def relative(tick):
        delta = (tick - first) & 0xFFFFFFFF
        return delta if delta < 0x80000000 else delta - 0x100000000

    opens = [relative(pulse['open']) for pulse in capture['pulses']]
    closes = [opened + ((pulse['close'] - pulse['open']) & 0xFFFFFFFF)
              for opened, pulse in zip(opens, capture['pulses'])]
    pressure = [float32(row['p']) for row in points]
    phases, first_deltas, rows, seen = {}, [], [], set()
    for i in range(1, len(points)):
        if not lower <= pressure[i - 1] < upper:
            continue
        tick = relative(points[i]['t'])
        pulse_i = bisect_right(opens, tick) - 1
        if pulse_i < 0:
            continue
        age = tick - opens[pulse_i]
        delta = pressure[i] - pressure[i - 1]
        phase_bin = (age // 25) * 25
        phases.setdefault(phase_bin, []).append(delta)
        if pulse_i not in seen:
            first_deltas.append(delta)
            seen.add(pulse_i)
        rows.append(dict(sample_i=i, pulse_i=pulse_i, elapsed_ms=tick,
                         since_open_ms=age, since_close_ms=tick-closes[pulse_i],
                         command_open=tick < closes[pulse_i],
                         pressure_mmhg=pressure[i], delta_mmhg=delta))
    return dict(phase_source='recorded GPIO command edges on MCU sample clock',
                complete_command_trace=True, independent_pressure_reference=False,
                pressure_band_mmhg=[lower, upper], recorded_pulses=len(opens),
                phase_bin_width_ms=25,
                phase_deltas={str(phase): summarize(values) for phase, values in sorted(phases.items())},
                first_sample_after_valve=summarize(first_deltas), aligned_samples=rows,
                limitation='Command timing does not measure mechanical motion or ADS conversion aperture; correlation is not causation.')


def audit(path, lower, upper):
    capture = decode(path.read_text(encoding="utf-8-sig").splitlines())
    if capture['header']['schema'] == 'bp.capture/4':
        return dict(source=str(path), **audit_timing(capture, lower, upper))
    if capture["header"]["schema"] not in ("bp.capture/2", "bp.capture/3"):
        raise ValueError("a /2 or /3 capture with valve diagnostics is required")
    valve = capture["valve"]
    if valve["period_min"] != 200 or valve["period_max"] != 200:
        raise ValueError("this audit requires exactly 200 ms recorded valve periods")
    points = capture["points"]
    ticks = [((row["t"] - points[0]["t"]) & 0xFFFFFFFF) for row in points]
    if any(right - left != 25 for left, right in zip(ticks, ticks[1:])):
        raise ValueError("this audit requires exact 25 ms MCU sample intervals")
    pressure = [float32(row["p"]) for row in points]
    exact_steps = [step for step in capture["steps"] if step["phase"] != 255]
    if exact_steps:
        anchor_index = exact_steps[0]["i"]
        anchor_phase = exact_steps[0]["phase"]
        anchor_source = "step_trace"
    elif valve["fall_found"]:
        anchor_index = valve["fall_i"]
        anchor_phase = valve["fall_phase"]
        anchor_source = "aggregate_max_fall"
    else:
        raise ValueError("no exact valve phase is available")
    if anchor_phase >= 200:
        raise ValueError("the anchor event falls outside the 200 ms pulse period")
    anchor = ticks[anchor_index] - anchor_phase
    first_phase = anchor_phase % 25
    phases = [(tick - anchor) % 200 for tick in ticks]
    for step in capture["steps"]:
        if step["phase"] != 255 and phases[step["i"]] != step["phase"]:
            raise ValueError("step phases disagree with the recorded 200 ms schedule")
    if valve["fall_found"] and phases[valve["fall_i"]] != valve["fall_phase"]:
        raise ValueError("maximum fall phase disagrees with the recorded schedule")
    if valve["rise_found"] and phases[valve["rise_i"]] != valve["rise_phase"]:
        raise ValueError("maximum rise phase disagrees with the recorded schedule")
    reconstructed_bins = [0] * 9
    for index in range(1, len(points)):
        if abs(pressure[index] - pressure[index - 1]) >= 5.0:
            reconstructed_bins[phases[index] // 25] += 1
    if reconstructed_bins != valve["phase"]:
        raise ValueError("reconstructed pressure-step bins differ from valve diagnostics")

    by_phase = {}
    cycles = []
    for index in range(1, len(points)):
        if not lower <= pressure[index - 1] < upper:
            continue
        phase = phases[index]
        by_phase.setdefault(phase, []).append(pressure[index] - pressure[index - 1])
        if (phase == first_phase and index + 1 < len(points) and
                ticks[index + 1] - ticks[index] == 25):
            cycles.append({
                "sample_i": index,
                "before_mmhg": round(pressure[index - 1], 2),
                "first_delta_mmhg": pressure[index] - pressure[index - 1],
                "next_delta_mmhg": pressure[index + 1] - pressure[index],
                "net_50ms_mmhg": pressure[index + 1] - pressure[index - 1],
            })
    if len(by_phase) != 8:
        raise ValueError("expected all eight 25 ms sample phases")
    first = [row["first_delta_mmhg"] for row in cycles]
    rebound = [row["next_delta_mmhg"] for row in cycles]
    net = [row["net_50ms_mmhg"] for row in cycles]
    return {
        "source": str(path),
        "complete_command_trace": False,
        "phase_source": "inferred constant-period schedule from pressure-step anchor",
        "pressure_band_mmhg": [lower, upper],
        "anchor_elapsed_ms": anchor,
        "anchor_source": anchor_source,
        "verified_step_phases": len(exact_steps),
        "recorded_pulses": valve["pulses"],
        "recorded_steps": valve["steps"],
        "phase_deltas": {str(phase): summarize(values)
                         for phase, values in sorted(by_phase.items())},
        "first_sample_after_valve": summarize(first),
        "following_sample": summarize(rebound),
        "net_two_samples": summarize(net),
        "large_first_falls": [row for row in cycles if row["first_delta_mmhg"] <= -5.0],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--lower", type=int, default=50)
    parser.add_argument("--upper", type=int, default=130)
    args = parser.parse_args()
    if args.lower >= args.upper:
        parser.error("lower must be less than upper")
    print(json.dumps(audit(args.capture, args.lower, args.upper), indent=2))


if __name__ == "__main__":
    main()
