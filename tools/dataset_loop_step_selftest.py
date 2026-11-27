"""Synthetic check for tmp/dataset_loop_step_analysis.py.

Builds a pressure trace the way the real run would look - inflate, settle, pull,
hold, push home, hold - with a known volume, a known leak, and optional hand noise
on the pulled plateau, then checks that the analyser recovers the volume.

The generator has to be honest about one thing: the pulled pressure follows the
home pressure AT THE MOMENT OF THE PULL, not the pressure at the start of the
settle window. The first version of this file got that wrong by 9 mmHg of settle
leak and reported a 10.4 cc error that was really a bug in the test, not in the
analyser.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dataset_loop_step_analysis as ana  # noqa: E402

ATM = 760.0
DT = 0.05
G = 26.0
SETTLE_S = 90.0
PULL_S = 1.2
PULLED_S = 130.0
PUSH_S = 1.0
FINAL_S = 90.0


def build(v_true, leak_a=-0.10, leak_b=+0.02, p_home0=200.0, noise_b=0.0, seed=7):
    """Trace whose plateaus each advance along their own straight line.

    Gauge pressure is clamped at zero the same way ``ads1115.c`` clamps it, so a
    volume small enough to drive the loop below atmosphere reproduces the real
    failure instead of a physically impossible negative reading.
    """
    rng = np.random.default_rng(seed)
    p_at_pull = p_home0 + leak_a * SETTLE_S
    p_pulled = (ATM + p_at_pull) * v_true / (v_true + G) - ATM

    t, p = [], []
    now = 0.0
    while now < SETTLE_S:
        t.append(now)
        p.append(p_home0 + leak_a * now)
        now += DT

    for i in range(int(PULL_S / DT)):
        frac = (i + 1) * DT / PULL_S
        t.append(now)
        p.append(p_at_pull + (p_pulled - p_at_pull) * (1 - (1 - frac) ** 3))
        now += DT

    base_b = now - DT
    jitter = 0.0
    while now < base_b + PULLED_S:
        if noise_b:
            jitter = float(rng.normal(0.0, noise_b))
        t.append(now)
        p.append(p_pulled + leak_b * (now - base_b) + jitter)
        now += DT

    p_before_push = p_pulled + leak_b * (now - base_b)
    p_home_back = p_home0 + leak_a * (now + PUSH_S)
    for i in range(int(PUSH_S / DT)):
        frac = (i + 1) * DT / PUSH_S
        t.append(now)
        p.append(p_before_push + (p_home_back - p_before_push) * (1 - (1 - frac) ** 3))
        now += DT

    base_d = now - DT
    while now < base_d + FINAL_S:
        t.append(now)
        p.append(p_home_back + leak_a * (now - base_d))
        now += DT

    t = np.array(t)
    p = np.array(p)
    p_displayed = np.maximum(p, 0.0)          # the firmware clamp, ads1115.c:215-218
    samples = [dict(timestamp=int(1_700_000_000_000 + ti * 1000),
                    est=round(float(pi), 1),
                    raw=int(1440 + pi * 24), sensor=int(225 + pi * 3), valid='VALID')
               for ti, pi in zip(t, p_displayed)]
    return samples, p_pulled


def naive_volume(samples, pull_index, g=G, atm=ATM):
    """No leak correction: last reading before the step, first reading after it.

    The index pair is taken a full second either side of the detected step centre,
    because the few samples straddling the step centre are mid-ramp and their
    difference is not the step at all.
    """
    p = np.array([s['est'] for s in samples])
    dt_pts = max(1, int(round(1.0 / DT)))
    before = p[max(0, pull_index - dt_pts)]
    after = p[min(len(p) - 1, pull_index + dt_pts)]
    if before - after <= 0:
        raise RuntimeError(f'no step at index {pull_index}')
    return (atm + after) * g / (before - after)


def main():
    fails = []

    print('=== clean trace, true volume 150 cc, leak -0.10 / +0.02 mmHg/s ===')
    samples, p_pulled = build(150.0)
    r = ana.analyze(samples, 200.0, G)
    ana.print_report(r)
    err = r['volume_cc'] - 150.0
    print(f'  true 150.0   analyser {r["volume_cc"]:.1f} cc   error {err:+.1f} cc')
    if abs(err) > 6.0:
        fails.append(f'clean trace error {err:+.1f} cc')

    print('=== same trace, no leak correction at all ===')
    t = np.array([s['timestamp'] for s in samples]) / 1000.0
    t -= t[0]
    p = np.array([s['est'] for s in samples])
    pull, push, dt = ana.find_steps(t, p)
    v_naive = naive_volume(samples, pull['index'])
    print(f'  naive {v_naive:.1f} cc, error {v_naive - 150.0:+.1f} cc')
    print('  (the same-instant rule is what removes that error)')

    print('\n=== four true volumes, to check the mapping is monotone and scaled ===')
    print('  (80 cc is not in the list: pulling 26 mL out of 80 cc below atmosphere')
    print('   is physically impossible, the minimum measurable volume at 200 mmHg is')
    print(f'   {G * ATM / 191.0:.0f} cc)')
    for v in (110.0, 150.0, 300.0, 362.0):
        s, _ = build(v)
        rr = ana.analyze(s, 200.0, G)
        e = rr['volume_cc'] - v
        print(f'  true {v:6.1f} -> {rr["volume_cc"]:6.1f} cc (error {e:+5.1f}, '
              f'{e / v * 100:+5.1f} percent)')
        if abs(e / v) > 0.03:
            fails.append(f'true {v} gave {rr["volume_cc"]}')

    print('\n=== hand noise on the pulled plateau, 0.8 mmHg sd ===')
    s, _ = build(150.0, noise_b=0.8)
    rr = ana.analyze(s, 200.0, G)
    e = rr['volume_cc'] - 150.0
    print(f'  -> {rr["volume_cc"]:.1f} cc (error {e:+.1f})')
    if abs(e) > 8.0:
        fails.append(f'noisy pulled plateau error {e:+.1f} cc')

    print('\n=== a pulled plateau that hit the negative clamp must be refused ===')
    s, _ = build(150.0, p_home0=120.0)     # 120 -> 0 mmHg at 150 cc, right on the clamp
    try:
        rr = ana.analyze(s, 120.0, G)
        print(f'  NOT refused: {rr["volume_cc"]:.1f} cc, '
              f'B min {rr["plateau_b"]["p_mean"]:.1f} mmHg')
        fails.append('a clamped pulled plateau was accepted')
    except RuntimeError as exc:
        print(f'  refused: {exc}')

    print('\n=== a pulled plateau that never went flat must be refused ===')
    # 0.45 mmHg/s = 27 mmHg/min, like a hand still resting on the plunger. The start
    # pressure is raised so the decay stays above the clamp and the slope test is what
    # catches it, not the floor test.
    s, _ = build(150.0, leak_b=-0.45, p_home0=260.0)
    try:
        rr = ana.analyze(s, 260.0, G)
        print(f'  NOT refused: {rr["volume_cc"]:.1f} cc, '
              f'slope {rr["plateau_b"]["slope_mmhg_per_min"]:+.1f} /min')
        fails.append('a 27 mmHg/min pulled plateau was accepted')
    except RuntimeError as exc:
        print(f'  refused: {exc}')

    print('\n=== a home plateau that is rising must be refused ===')
    s, _ = build(150.0, leak_a=+0.05)
    try:
        rr = ana.analyze(s, 200.0, G)
        print(f'  NOT refused: {rr["volume_cc"]:.1f} cc, '
              f'slope {rr["plateau_a"]["slope_mmhg_per_min"]:+.1f} /min')
        fails.append('a rising home plateau was accepted')
    except RuntimeError as exc:
        print(f'  refused: {exc}')

    print('\n=== a trace with no pull at all must be refused ===')
    flat = [dict(timestamp=int(1_700_000_000_000 + i * 50), est=0.4, raw=1440,
                 sensor=225, valid='VALID') for i in range(400)]
    try:
        ana.analyze(flat, 200.0, G)
        print('  NOT refused')
        fails.append('a flat trace was accepted')
    except RuntimeError as exc:
        print(f'  refused: {exc}')

    print()
    if fails:
        print('FAILURES:')
        for f in fails:
            print(f'  - {f}')
        raise SystemExit(1)
    print('all checks passed')


if __name__ == '__main__':
    main()
