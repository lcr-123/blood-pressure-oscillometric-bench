"""Volume from a gas-driven release: the plunger is let go, the gas pushes it out.

The measurement
    The loop is sealed at a known high pressure P1 with the plunger at the home stop
    (0 mL). The plunger is released; the trapped gas expands into the extra 26 mL of
    stroke until the stop catches it. Moles are constant, so

        P1_abs * V = P2_abs * (V + g)
        V = (atm + P2) * g / ((atm + P1) - (atm + P2))

    Which P2 to use matters, and the trace says why. Expanding the gas cools it, so the
    reading first OVERSHOOTS downward, then recovers upward as heat comes back in from
    the walls (and the walls do deliver - the cuff is a big warm surface), and only
    after that does the ordinary leak push it down again. The isothermal answer sits at
    the top of that hump, minus the leak accumulated on the way up.

Why high pressure at all
    At 0-10 mmHg gauge the cuff bladder and its foam are floppy: 26 mL of stroke moved
    the pressure by 7 mmHg, which the gas law turns into 2800 cc - not a volume this
    rig has. The walls absorbed the stroke, not the gas. Above about 150 mmHg the walls
    are taut and the gas law applies to the air alone.

Usage:
    python tools/release_volume_analysis.py <samples.json> [--stroke 26] [--atm 760]
"""
import argparse
import json
import statistics
from pathlib import Path

SLOPE = 81.529          # mmHg per volt at the sensor node (cal write 81.529 -20.03)
INTERCEPT = -20.03

HIGH_PLATEAU_MMHG = 120.0   # the release must start from a real plateau
DROP_MMHG = 15.0            # and lower the pressure by at least this much
WINDOW_S = 1.5


def load(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return data if isinstance(data, list) else [data]


def to_mmhg(sensor_mv):
    return sensor_mv / 1000.0 * SLOPE + INTERCEPT


def find_release(t, p):
    """Locate the fastest fall that starts from a real plateau.

    t is in SECONDS. An earlier version compared seconds against a millisecond window,
    so the look-back ran to the start of the file and every rate came out diluted -
    the release was there (188.9 -> 122.3 mmHg in 1 s) and the detector could not see
    it. It then latched onto the inflation ramp instead. Gating on the starting
    pressure is what makes this unambiguous: only the release begins above 120 mmHg
    and then falls hard.
    """
    best = None
    n = len(p)
    for i in range(20, n):
        j = i - 1
        while j > 0 and t[i] - t[j] < WINDOW_S:
            j -= 1
        if t[i] - t[j] < WINDOW_S * 0.6:
            continue
        if p[j] < HIGH_PLATEAU_MMHG:
            continue
        if p[j] - p[i] < DROP_MMHG:
            continue
        rate = (p[j] - p[i]) / (t[i] - t[j])
        if best is None or rate > best[0]:
            best = (rate, i, j)
    if best is None:
        return None, None
    return best[1], best[2]


def slope_per_min(t, p):
    if len(t) < 5:
        return float('nan')
    mt = sum(t) / len(t)
    mp = sum(p) / len(p)
    num = sum((a - mt) * (b - mp) for a, b in zip(t, p))
    den = sum((a - mt) ** 2 for a in t)
    return num / den * 60.0 if den else float('nan')


def solve(p1, p2, g, atm):
    d = (atm + p1) - (atm + p2)
    return (atm + p2) * g / d if d > 1e-6 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('samples')
    ap.add_argument('--stroke', type=float, default=26.0)
    ap.add_argument('--atm', type=float, default=760.0)
    ap.add_argument('--json', action='store_true')
    args = ap.parse_args()

    rows = [r for r in load(args.samples) if 'sensor' in r]
    t = [r['timestamp'] / 1000.0 for r in rows]
    p = [to_mmhg(r['sensor']) for r in rows]

    i_release, i_before = find_release(t, p)
    out = dict(samples=len(rows), stroke_ml=args.stroke, atm=args.atm)
    if i_release is None:
        out['error'] = 'no release found'
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    pre = [(tt, pp) for tt, pp in zip(t[:i_before + 1], p[:i_before + 1])
           if t[i_before] - tt <= 5.0]
    p1 = statistics.median([pp for _, pp in pre])
    t_release = t[i_release]

    post = [(tt - t_release, pp) for tt, pp in zip(t, p) if tt >= t_release]
    post_t = [a for a, _ in post]
    post_p = [b for _, b in post]

    lowest = min(post_p)
    i_low = post_p.index(lowest)
    peak = max(post_p)
    i_peak = post_p.index(peak)

    tail = [(a, b) for a, b in zip(post_t, post_p) if a >= post_t[-1] - 60.0]
    leak = slope_per_min([a for a, _ in tail], [b for _, b in tail]) \
        if len(tail) > 10 else float('nan')
    after_peak = [(a, b) for a, b in zip(post_t, post_p) if a >= post_t[i_peak]]
    decay = slope_per_min([a for a, _ in after_peak], [b for _, b in after_peak]) \
        if len(after_peak) > 20 else float('nan')

    warm_s = post_t[i_peak]
    correction = abs(leak) / 60.0 * warm_s if leak == leak else 0.0
    p2_peak = peak + correction

    variants = {
        'settled_last': post_p[-1],
        'peak_observed': peak,
        'peak_leak_corrected': p2_peak,
        'first_after_release': post_p[0],
        'lowest_overshoot': lowest,
    }
    vol = {}
    for k, v in variants.items():
        got = solve(p1, v, args.stroke, args.atm)
        vol[k] = round(got, 1) if got else None

    out.update(
        release_at_s=round(t_release - t[0], 1),
        p1_mmhg=round(p1, 2),
        lowest_mmhg=round(lowest, 2),
        lowest_at_s=round(post_t[i_low], 1),
        peak_mmhg=round(peak, 2),
        peak_at_s=round(warm_s, 1),
        final_mmhg=round(post_p[-1], 2),
        leak_last60_mmhg_per_min=round(leak, 2),
        decay_after_peak_mmhg_per_min=round(decay, 2),
        warmup_recovery_mmhg=round(peak - lowest, 2),
        leak_correction_mmhg=round(correction, 2),
        p2_variants={k: round(v, 2) for k, v in variants.items()},
        volume_cc_by_variant=vol,
    )
    best = vol['peak_leak_corrected']
    out['volume_cc'] = best
    usable = [v for k, v in vol.items()
              if v is not None and k in ('settled_last', 'peak_observed',
                                         'peak_leak_corrected', 'first_after_release')]
    if usable:
        out['volume_bracket_cc'] = [min(usable), max(usable)]
    agrees = (decay == decay and leak == leak
              and abs(decay - leak) <= max(0.8, abs(leak) * 0.4))
    out['consistency'] = (
        'the decay after the peak is explained by the measured leak'
        if agrees else
        'the decay after the peak does NOT match the tail leak, so something else '
        'moved as well (cuff creep, valve, or the operator)')

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return

    print(f'release at {out["release_at_s"]:.0f} s, stroke {args.stroke:.0f} mL, '
          f'atm {args.atm:.0f} mmHg')
    print(f'  P1                 {out["p1_mmhg"]:8.2f} mmHg')
    print(f'  lowest (overshoot) {out["lowest_mmhg"]:8.2f} at {out["lowest_at_s"]:5.1f} s')
    print(f'  peak (isothermal)  {out["peak_mmhg"]:8.2f} at {out["peak_at_s"]:5.1f} s '
          f'(recovery {out["warmup_recovery_mmhg"]:+.2f})')
    print(f'  final              {out["final_mmhg"]:8.2f} mmHg')
    print(f'  leak (last 60 s)   {out["leak_last60_mmhg_per_min"]:8.2f} mmHg/min')
    print(f'  decay after peak   {out["decay_after_peak_mmhg_per_min"]:8.2f} mmHg/min')
    print(f'  leak correction    {out["leak_correction_mmhg"]:+8.2f} mmHg')
    print()
    print('  volume by which P2 you believe:')
    for k, v in vol.items():
        shown = f'{v:7.1f} cc' if v else '    n/a'
        print(f'    {k:22} P2 {variants[k]:7.2f} -> {shown}')
    print()
    if best:
        print(f'  best estimate {out["volume_cc"]:.0f} cc, bracket '
              f'{out["volume_bracket_cc"][0]:.0f}-{out["volume_bracket_cc"][1]:.0f} cc')
    else:
        print('  no usable P2: the release did not lower the pressure')
    print(f'  consistency: {out["consistency"]}')


if __name__ == '__main__':
    main()
