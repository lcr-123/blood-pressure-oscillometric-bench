"""Analysis for tmp/dataset_loop_step_20261109.py: find the pull, fit the plateaus,
solve the gas law.

The whole measurement hinges on one thing being right: the two plateaus have to be
evaluated at the SAME instant, because the loop leaks throughout. Everything else -
reading a display, waiting long enough - is bookkeeping by comparison.

So this module never trusts a hand-recorded time. It finds the step in the pressure
trace itself, fits a straight line to the tail of each plateau, and then evaluates
the two lines at one common instant.

Why the two plateaus must be evaluated at the PULL INSTANT
    The gas law V = P_B_abs * g / (P_A_abs - P_B_abs) is only valid when the number
    of moles is the same in both states. The loop leaks throughout, so moles are
    not equal whenever they are measured - only at the instant the plunger moved,
    when nothing had time to leave or enter. Extrapolating both plateau lines to
    that instant is therefore not a refinement, it is what makes the equation
    legal. An earlier version of this module evaluated both lines at the END of the
    pulled plateau instead, which reads as "the same instant" but silently compares
    two different mole counts; the synthetic test caught it as a +19 cc error at
    150 cc that grew to +116 cc at 362 cc, because the mole difference scales with
    the volume being measured.

    So A is evaluated with almost no extrapolation (its tail ends 1 s before the
    pull) and B is back-extrapolated across its whole plateau. B's slope is
    therefore the dominant uncertainty, and it is reported as a sensitivity table.

Why the round trip is judged by RATE and not by pressure
    A pressure-dependent leak drops more slowly at low pressure, so extrapolating a
    constant home rate forwards over minutes over-predicts the fall and leaves the
    returned pressure HIGH. Air past the plunger also leaves it HIGH. Same sign, so
    pressure cannot separate them. Rate can: a fixed leak must be slower at lower
    pressure, so a returned rate that is not higher than the starting rate passes.
"""
import math

import numpy as np

SMOOTH_POINTS = 9          # 9 samples at 20 Hz = 0.45 s
STEP_RATE_MMHG_S = 2.0     # a hand-driven plunger moves the loop far faster than a leak
MIN_STEP_MMHG = 12.0
PERSIST_S = 2.5            # the new level must hold this long to count as a real step
PERSIST_TOLERANCE_MMHG = 4.0
TAIL_S = 25.0              # how much of each plateau tail to fit
EDGE_SKIP_S = 1.0          # discard this much right next to the step
SLOPE_LIMIT_MMHG_MIN = 24.0


def _fit(ts, ps):
    """Least-squares line through one plateau tail."""
    ts = np.asarray(ts, dtype=float)
    ps = np.asarray(ps, dtype=float)
    if ts.size < 20:
        return None
    center = float(ts.mean())
    p_mean = float(ps.mean())
    den = float(((ts - center) ** 2).sum())
    if den <= 0:
        return None
    slope = float(((ts - center) * (ps - p_mean)).sum() / den)
    resid = ps - (p_mean + slope * (ts - center))
    return dict(slope=slope, resid_sd=float(resid.std(ddof=1)), n=int(ts.size),
                t0=float(ts[0]), t1=float(ts[-1]), center=center, p_mean=p_mean)


def _line_at(fit, t):
    """Evaluate a fitted line at an arbitrary time."""
    return fit['p_mean'] + fit['slope'] * (t - fit['center'])


def _plateau(t, p, t_lo, t_hi):
    if t_hi <= t_lo:
        return None
    sel = (t >= t_lo) & (t <= t_hi)
    if sel.sum() < 20:
        return None
    return _fit(t[sel], p[sel])


def _smooth_edge_safe(p, points):
    """Moving average with replicated edges.

    np.convolve(..., mode='same') zero-pads, which drags the first and last few
    smoothed values toward zero and fabricates a step at each end of the trace.
    The first version of this module did exactly that and then locked onto the
    fake end step instead of the real pull, so the padding is explicit here.
    """
    half = points // 2
    padded = np.concatenate([np.full(half, p[0]), p, np.full(points - 1 - half, p[-1])])
    return np.convolve(padded, np.ones(points) / points, mode='valid')


def find_steps(t, p):
    """Locate the biggest pressure fall and the biggest later rise."""
    if t.size < 100:
        raise RuntimeError(f'only {t.size} samples; not enough')
    p = np.asarray(p, dtype=float)
    ps = _smooth_edge_safe(p, SMOOTH_POINTS)
    dt = float(np.median(np.diff(t)))
    win = max(3, int(round(1.5 / dt)))
    if t.size <= 2 * win + 1:
        raise RuntimeError('trace too short for step detection')
    rate = np.full_like(ps, np.nan)
    rate[win:-win] = (ps[2 * win:] - ps[:-2 * win]) / (2 * win * dt)

    def extremes(sign):
        out = []
        with np.errstate(invalid='ignore'):
            mask = sign * rate > STEP_RATE_MMHG_S
        if not mask.any():
            return out
        idx = np.flatnonzero(mask)
        for g in np.split(idx, np.flatnonzero(np.diff(idx) > win) + 1):
            i = int(g[np.nanargmax(sign * rate[g])])
            drop = float(ps[max(0, i - win)] - ps[min(len(ps) - 1, i + win)])
            if abs(drop) < MIN_STEP_MMHG:
                continue
            out.append(dict(index=i, t=float(t[i]), rate=float(rate[i]),
                            delta_mmhg=drop, width_samples=int(g[-1] - g[0] + 1)))
        return out

    def persists(step, seconds=PERSIST_S, tolerance=PERSIST_TOLERANCE_MMHG):
        """True when the level after the step holds instead of snapping back.

        A real plunger move leaves the loop at a new pressure and the stop holds it
        there. A syringe that was tugged and released gives a dip that comes straight
        back - the 2026-11-09 attempt is full of those (194 -> 184 -> 190 -> 172 ->
        190 -> 151 -> 190 in ten seconds), and picking the deepest of them would
        report a step that never existed. Requiring the new level to hold for
        `seconds` is what separates the two.

        The window starts after the step has finished, not 1 s after its centre: the
        detected index sits in the middle of the movement, so clearing the measured
        width is the only way to keep the ramp out of the "held level" sample.
        """
        clear = step['width_samples'] // 2 + int(round(1.0 / dt))
        start = step['index'] + clear
        end = start + int(round(seconds / dt))
        if end >= p.size:
            return False
        after = p[start:end]
        reference = float(np.median(after))
        return bool(np.all(np.abs(after - reference) <= tolerance))

    falls = [s for s in extremes(-1.0) if persists(s)]
    rises = [s for s in extremes(+1.0) if persists(s)]
    if not falls:
        raise RuntimeError('no sustained pressure fall found; a plunger that was pulled '
                           'and released does not count - pull it to the stop and let go')
    if not rises:
        raise RuntimeError('no sustained pressure rise found; was the plunger pushed '
                           'fully home and held there?')
    pull = max(falls, key=lambda d: abs(d['delta_mmhg']))
    later = [r for r in rises if r['t'] > pull['t']]
    if not later:
        raise RuntimeError('the rise came before the fall; check the choreography')
    push = max(later, key=lambda d: d['delta_mmhg'])
    return pull, push, dt


def _solve(p_a, p_b, g_ml, atm):
    step = (atm + p_a) - (atm + p_b)
    if step <= 0:
        raise RuntimeError('the pull did not lower the pressure')
    return (atm + p_b) * g_ml / step, step


def analyze(samples, target, g_ml, atm=760.0, tail_s=TAIL_S):
    if not samples:
        raise RuntimeError('no samples')
    t = np.array([s['timestamp'] for s in samples], dtype=float) / 1000.0
    t -= t[0]
    p = np.array([s['est'] for s in samples], dtype=float)
    raw = np.array([s['raw'] for s in samples], dtype=float)

    pull, push, dt = find_steps(t, p)
    half = max(1.0, pull['width_samples'] * dt / 2.0)
    push_half = max(1.0, push['width_samples'] * dt / 2.0)
    t_after_pull = pull['t'] + half
    t_before_push = push['t'] - push_half

    a = _plateau(t, p, pull['t'] - half - tail_s, pull['t'] - half - EDGE_SKIP_S)
    b = _plateau(t, p, t_before_push - tail_s, t_before_push - EDGE_SKIP_S)
    d = _plateau(t, p, t[-1] - tail_s, t[-1])
    for label, fit in (('A (home, before the pull)', a), ('B (pulled)', b)):
        if fit is None:
            raise RuntimeError(f'plateau {label} has too few samples; check the schedule')
    if a['slope'] * 60 > 0.4:
        raise RuntimeError(f'plateau A is rising ({a["slope"] * 60:+.2f} mmHg/min); '
                           'the loop was not sealed')
    if abs(b['slope'] * 60) > SLOPE_LIMIT_MMHG_MIN:
        raise RuntimeError(f'plateau B is not flat ({b["slope"] * 60:+.2f} mmHg/min); '
                           'was the plunger still being held by hand?')
    # ads1115.c clamps negative gauge pressure to zero, so a plateau that touches the
    # floor is flat for a reason that has nothing to do with the gas law. Checked after
    # the slope test, because a hand-held plunger is the likelier mistake and its
    # message is more actionable.
    b_floor = float(np.min(p[(t >= b['t0']) & (t <= b['t1'])]))
    if b_floor < 5.0:
        raise RuntimeError(f'plateau B reached {b_floor:.1f} mmHg, at or near the '
                           'negative-pressure clamp; use a higher target')

    # Primary: the pull instant, the only moment the mole count is equal on both
    # branches. A's tail ends 1 s before it, so A needs almost no extrapolation;
    # B is back-extrapolated across its whole plateau.
    t_primary = t_after_pull
    p_a_primary = _line_at(a, t_primary)
    p_b_primary = _line_at(b, t_primary)
    v_primary, step_primary = _solve(p_a_primary, p_b_primary, g_ml, atm)

    # Secondary, reported as a bracket: evaluate at the end of B's tail, so B needs
    # no extrapolation at all and A is carried forward instead. A's rate is well
    # determined over its plateau, so a long carry costs little - which means the
    # gap between the two numbers measures how much B's slope matters.
    t_tail = b['t1']
    p_a_tail = _line_at(a, t_tail)
    p_b_tail = _line_at(b, t_tail)
    v_tail, step_tail = _solve(p_a_tail, p_b_tail, g_ml, atm)

    # How far the measured pressure right after the pull sits from the tail line:
    # nonzero means the fast pull cooled the gas and it was still rewarming.
    sel_early = (t >= t_after_pull) & (t <= t_after_pull + EDGE_SKIP_S + 2.0)
    rebound = (float(np.mean(p[sel_early])) - _line_at(b, t_after_pull)) if sel_early.any() else float('nan')

    def p2p(arr, lo, hi):
        sel = (t >= lo) & (t <= hi)
        return float(np.ptp(arr[sel])) if sel.any() else float('nan')

    # B's slope is what carries the primary evaluation back across the plateau, so
    # scale THAT to see how much a hidden leak in the pulled branch matters. Note
    # the sign: a steeper decay means the pressure at the pull was HIGHER, which
    # shrinks the step and therefore inflates the volume.
    sens = []
    for factor in (0.5, 1.0, 1.5, 2.0):
        p_b_alt = p_b_primary + (factor - 1.0) * b['slope'] * (t_primary - b['center'])
        st = (atm + p_a_primary) - (atm + p_b_alt)
        if st <= 0:
            continue
        sens.append(dict(pulled_leak_factor=factor, p_pulled=round(p_b_alt, 2),
                         v_cc=round((atm + p_b_alt) * g_ml / st, 1)))

    dv_dp_b = g_ml * (atm + p_a_primary) / step_primary ** 2
    dv_dp_a = -g_ml * (atm + p_b_primary) / step_primary ** 2
    sd_res = math.hypot(dv_dp_a, dv_dp_b) * (0.05 / math.sqrt(3.0))

    result = dict(
        g_ml=g_ml, atm_assumed=atm, target_mmhg=target,
        n_samples=int(t.size), duration_s=round(float(t[-1]), 2),
        sample_interval_ms=round(dt * 1000, 2),
        pull=dict(t=round(pull['t'], 2), delta_mmhg=round(pull['delta_mmhg'], 2),
                  rate_mmhg_s=round(pull['rate'], 2),
                  width_ms=round(pull['width_samples'] * dt * 1000)),
        push=dict(t=round(push['t'], 2), delta_mmhg=round(push['delta_mmhg'], 2),
                  rate_mmhg_s=round(push['rate'], 2),
                  width_ms=round(push['width_samples'] * dt * 1000)),
        plateau_a=dict(slope_mmhg_per_min=round(a['slope'] * 60, 3), n=a['n'],
                       resid_sd=round(a['resid_sd'], 3),
                       span_s=[round(a['t0'], 1), round(a['t1'], 1)],
                       raw_p2p_counts=p2p(raw, a['t0'], a['t1'])),
        plateau_b=dict(slope_mmhg_per_min=round(b['slope'] * 60, 3), n=b['n'],
                       resid_sd=round(b['resid_sd'], 3),
                       span_s=[round(b['t0'], 1), round(b['t1'], 1)],
                       raw_p2p_counts=p2p(raw, b['t0'], b['t1'])),
        primary=dict(rule='evaluated at the pull instant, where both branches hold '
                          'the same number of moles',
                     t=round(t_primary, 2), p_home=round(p_a_primary, 2),
                     p_pulled=round(p_b_primary, 2), step_mmhg=round(step_primary, 2),
                     volume_cc=round(v_primary, 1)),
        bracket_at_b_tail=dict(rule='evaluated at the end of the pulled tail, B not '
                                    'extrapolated; the gap measures how much B slope matters',
                               t=round(t_tail, 2), p_home=round(p_a_tail, 2),
                               p_pulled=round(p_b_tail, 2), step_mmhg=round(step_tail, 2),
                               volume_cc=round(v_tail, 1)),
        volume_cc=round(v_primary, 1),
        volume_bracket_cc=[round(min(v_primary, v_tail), 1), round(max(v_primary, v_tail), 1)],
        rebound_residual_mmhg=round(rebound, 2),
        volume_sensitivity=sens,
        volume_resolution_cc=round(sd_res, 2),
        atm_sensitivity_cc={str(int(x)): round((x + p_b_primary) * g_ml /
                                               ((x + p_a_primary) - (x + p_b_primary)), 1)
                            for x in (730, 745, 760, 775, 790)},
    )

    if d is not None:
        result['plateau_d'] = dict(slope_mmhg_per_min=round(d['slope'] * 60, 3),
                                   span_s=[round(d['t0'], 1), round(d['t1'], 1)],
                                   raw_p2p_counts=p2p(raw, d['t0'], d['t1']))
        result['round_trip'] = dict(
            returned_rate_mmhg_per_min=round(d['slope'] * 60, 3),
            start_rate_mmhg_per_min=round(a['slope'] * 60, 3),
            rate_check='pass' if d['slope'] <= a['slope'] + 0.5 / 60 else 'fail',
        )
    return result


def print_report(r):
    print('\n' + '=' * 70)
    print(f'STEP   pull at {r["pull"]["t"]:.1f} s  {r["pull"]["delta_mmhg"]:+.1f} mmHg '
          f'({r["pull"]["rate_mmhg_s"]:+.1f} mmHg/s, {r["pull"]["width_ms"]:.0f} ms)')
    print(f'       push at {r["push"]["t"]:.1f} s  {r["push"]["delta_mmhg"]:+.1f} mmHg '
          f'({r["push"]["rate_mmhg_s"]:+.1f} mmHg/s)')
    print(f'PLATEAU A (home, before pull) {r["plateau_a"]["slope_mmhg_per_min"]:+.2f} mmHg/min '
          f'n={r["plateau_a"]["n"]} raw_p2p={r["plateau_a"]["raw_p2p_counts"]:.0f} counts')
    print(f'PLATEAU B (pulled)            {r["plateau_b"]["slope_mmhg_per_min"]:+.2f} mmHg/min '
          f'n={r["plateau_b"]["n"]} raw_p2p={r["plateau_b"]["raw_p2p_counts"]:.0f} counts')
    pr = r['primary']
    print(f'PRIMARY  at {pr["t"]:.1f} s: home {pr["p_home"]:.2f}  pulled {pr["p_pulled"]:.2f}  '
          f'step {pr["step_mmhg"]:.2f}')
    print(f'VOLUME   {r["volume_cc"]:.1f} cc    bracket {r["volume_bracket_cc"][0]:.1f} - '
          f'{r["volume_bracket_cc"][1]:.1f} cc')
    print(f'REBOUND RESIDUAL {r["rebound_residual_mmhg"]:+.2f} mmHg '
          f'(0 means the pull did not cool the gas)')
    print('SENSITIVITY TO THE PULLED-SIDE LEAK RATE')
    for row in r['volume_sensitivity']:
        print(f'   leak x{row["pulled_leak_factor"]:.1f} -> {row["v_cc"]:.1f} cc')
    print('SENSITIVITY TO ASSUMED ATMOSPHERE')
    print('   ' + '  '.join(f'{k}:{v:.0f}' for k, v in r['atm_sensitivity_cc'].items()))
    if 'round_trip' in r:
        rt = r['round_trip']
        print(f'ROUND TRIP  drift {rt["start_rate_mmhg_per_min"]:+.2f} -> '
              f'{rt["returned_rate_mmhg_per_min"]:+.2f} /min  {rt["rate_check"].upper()}')
    print('=' * 70 + '\n')
