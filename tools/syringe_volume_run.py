"""Syringe volume measurement, rewritten from scratch after four failed attempts.

THE PHYSICS
The loop is one closed volume of gas V (cuff + tubing + tee + valve dead space + sensor port)
plus whatever the syringe barrel adds. With the plunger at graduation g the gas occupies V+g.
Nothing else changes between two plateaus (same moles, same temperature), so

    P1_abs * (V + g1) = P2_abs * (V + g2)
    V = (P2_abs * g2 - P1_abs * g1) / (P1_abs - P2_abs)

with P_abs = gauge + 760. This needs no panel reference and no external truth, which is exactly
why it is worth doing: it is the only volume number that does not trust the BP Pump 2.

WHY THE PREVIOUS ATTEMPTS FAILED, AND WHAT CHANGES HERE
1. The plunger was free while pressurised. 150 mmHg on a 20 mL barrel (area 3.14 cm2) is 0.64 kgf,
   so the plunger creeps outward on its own; a 20 mL pull was effectively 12.5 mL. Fix: the
   plunger is tied down at every plateau, and the operator reports the graduation they actually see.
2. The pressure was recorded before the system settled. Compression heats the gas, which then
   cools and loses about 15% in the first 30 s. Fix: 60 s settle before the first plateau, and every
   plateau is fitted as a line over its tail instead of read as one sample.
3. A hand on the rig injects 4.7 mmHg peak-to-peak of noise (0.27 mmHg with the hand off, 17x).
   Fix: every plateau window is hands-off, and the script refuses to accept a plateau while the raw
   counts are still moving.
4. Reading times and action times drifted apart. Fix: this script records event timestamps and the
   analysis is done offline from the log, so nothing depends on when a human wrote a number down.

The leak (about 6.5 mmHg/min at 150 mmHg) is not eliminated; it is measured. Each plateau is
fitted, both plateaus are extrapolated to the instant of the pull, and the analysis prints both the
raw and the leak-corrected volume so the size of the correction is visible.

Usage:
    python tmp/syringe_volume_20261109.py [start_mmhg] [g1] [g2] [g3] [name]

Defaults: 200 mmHg, graduations 0 / 9 / 18 mL. The operator only acts when the script prints a
line beginning with '>>>'.

Why 200 mmHg and not 150. Absolute pressure sets how far the same 9 mL pull moves the gauge. At
150 mmHg a 150 cc loop would end up at 43 mmHg, and a 110 cc loop at 10 mmHg, where the leak starts
sucking air in and the closed-volume assumption fails. From 200 mmHg the third plateau lands at
87 mmHg for a 150 cc loop, 57 for 110 cc, 39 for 90 cc - all safely positive.

Why 9 mL steps and not 8 or 20. The volume comes out as (P2*g2 - P1*g1)/(P1-P2), so an error in the
graduation enters roughly as P/(P1-P2) cc per mL. With 9 mL steps and about a 50 mmHg drop that is
about 9 cc per mL of reading error, and a syringe read to +-0.5 mL gives +-5 cc on 150 cc. Larger
steps are better still, but a 20 mL barrel must keep 2 mL of margin or the plunger can leave the
barrel, so 18 mL is the useful maximum.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from direct_serial_bridge_20261107 import ROOT, open_bridge  # noqa: E402

start = int(sys.argv[1]) if len(sys.argv) > 1 else 200
g1 = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
g2 = float(sys.argv[3]) if len(sys.argv) > 3 else 9.0
g3 = float(sys.argv[4]) if len(sys.argv) > 4 else 18.0
name = sys.argv[5] if len(sys.argv) > 5 else f'syringe_{start}'

ATM = 760.0
SETTLE_S = 90.0          # the compression transient is spent by here (rate stable by 60-90 s)
PLATEAU_A_S = 30.0
PLATEAU_BC_S = 45.0
STEP_DROP_MMHG = 10.0    # a real pull drops the median by 18-57 mmHg; hand noise cannot do 10
# Hands-off noise on this rig measures 11-19 counts peak-to-peak over a 1.2 s window (A/B test),
# 332 counts with a hand on the plunger. The earlier 6-count gate was physically unreachable, which
# is why that run sat printing "hand on rig" forever at p2p 10-17. 25 counts separates the two
# regimes with a factor of 13 to the bad side and 1.3 to the good side.
QUIET_P2P_COUNTS = 25.0
QUIET_RATE = 0.30
QUIET_HOLD_S = 6.0
MAX_PRESSURE = 330.0

SLOPE = 81.529
INTERCEPT = -20.03

log = open(ROOT / 'tmp' / 'omniprobe' / f'{name}.ndjson', 'w', encoding='utf-8')
b = open_bridge(log)

report = dict(
    protocol='three_plateau_syringe_volume',
    intent='measure the total gas volume of the cuff loop without trusting the panel',
    start_mmhg=start,
    graduations_ml=dict(g1=g1, g2=g2, g3=g3),
    step_drop_threshold_mmhg=STEP_DROP_MMHG,
    settle_s=SETTLE_S,
    plateau_windows_s=dict(A=PLATEAU_A_S, B=PLATEAU_BC_S, C=PLATEAU_BC_S),
    nonhuman_fixture_confirmed=True,
    calibration_changed=False,
    firmware_changed=False,
    events=[],
    plateaus=[],
    operator_reported_graduations={},
)


def window(seconds_ago_from, seconds_ago_to):
    """Samples whose age is between the two bounds, in seconds before the newest sample."""
    if not b.samples:
        return []
    newest = b.samples[-1]['timestamp']
    low = newest - int(seconds_ago_from * 1000)
    high = newest - int(seconds_ago_to * 1000)
    return [s for s in b.samples if low <= s['timestamp'] <= high]


def true_mmhg(sample):
    """Unclamped pressure. ads1115.c clamps negative pressure to 0, which hides the zero."""
    return sample['sensor'] / 1000.0 * SLOPE + INTERCEPT


def pressures(samples):
    return np.array([true_mmhg(s) for s in samples], dtype=float)


def med(samples):
    if not samples:
        return float('nan')
    return float(np.median(pressures(samples)))


def raw_p2p(samples):
    if not samples:
        return float('nan')
    values = [s['raw'] for s in samples]
    return float(max(values) - min(values))


def stats(samples):
    if len(samples) < 10:
        return None
    values = pressures(samples)
    stamps = np.array([s['timestamp'] for s in samples]) / 1000.0
    return dict(median=float(np.median(values)),
                spread=float(values.max() - values.min()),
                raw_p2p=raw_p2p(samples),
                rate=float(np.polyfit(stamps - stamps[0], values, 1)[0]),
                t_first=float(stamps[0]), t_last=float(stamps[-1]),
                n=len(samples))


def note(label, **fields):
    entry = dict(label=label, t_ms=int(time.time() * 1000), **fields)
    report['events'].append(entry)


def read_plateau(label, seconds):
    """Watch a plateau for `seconds`, printing live, and record the tail for offline fitting."""
    began = time.monotonic()
    quiet_since = None
    while time.monotonic() - began < seconds:
        b.observe(1.0)
        current = stats(window(1.2, 0.0))
        if current is None:
            continue
        if current['median'] > MAX_PRESSURE:
            raise RuntimeError(f'pressure {current["median"]:.0f} above the guard')
        quiet = (current['raw_p2p'] <= QUIET_P2P_COUNTS
                 and abs(current['rate']) <= QUIET_RATE)
        if quiet and quiet_since is None:
            quiet_since = time.monotonic()
        elif not quiet:
            quiet_since = None
        hands_off = quiet_since is not None and (time.monotonic() - quiet_since) >= QUIET_HOLD_S
        print(f'    {label} {current["median"]:7.2f} mmHg  raw p2p {current["raw_p2p"]:4.0f}  '
              f'rate {current["rate"]:+.3f} mmHg/s  '
              f'{"HANDS OFF OK" if hands_off else ("hand on rig" if current["raw_p2p"] > QUIET_P2P_COUNTS else "drifting")}',
              flush=True)
    tail = stats(window(20.0, 0.0))
    if tail is not None:
        report['plateaus'].append(dict(label=label, **{k: round(v, 3) if isinstance(v, float) else v
                                                       for k, v in tail.items()}))
        print(f'    {label} tail fit: median {tail["median"]:.2f} mmHg, '
              f'rate {tail["rate"]:+.3f} mmHg/s, raw p2p {tail["raw_p2p"]:.0f}', flush=True)
    return tail


def wait_for_pull(timeout_s):
    """Wait until the median FALLS by STEP_DROP_MMHG. Returns the pre-pull baseline."""
    began = time.monotonic()
    while time.monotonic() - began < timeout_s:
        b.observe(0.5)
        recent = window(1.5, 0.0)
        baseline = window(5.0, 2.0)
        if len(recent) < 20 or len(baseline) < 20:
            continue
        current = med(recent)
        reference = med(baseline)
        drop = reference - current
        if drop >= STEP_DROP_MMHG:
            before = stats(baseline)
            print(f'    PULL DETECTED: {reference:.1f} -> {current:.1f} mmHg '
                  f'(drop {drop:.1f})', flush=True)
            return before
        print(f'    waiting for the pull ... {current:7.2f} mmHg '
              f'(drop {drop:+.1f}, raw p2p {raw_p2p(recent):.0f})', flush=True)
    return None


try:
    b.wait(lambda: bool(b.messages), 3, 'missing hello')

    try:
        b.command('status', r'\[UART3\]')
        b.command('pins', r'PC1=')
        b.command('cal', r'slope=')
    except BaseException as exc:
        print(f'PREFLIGHT WARNING {exc!r}', flush=True)

    try:
        b.command('vent', r'\[Deflate\] VENT')
    except BaseException:
        pass
    b.observe(6.0)
    base = stats(window(2.0, 0.0))
    report['baseline'] = dict(median=round(base['median'], 3),
                              raw_p2p=round(base['raw_p2p'], 1))
    print(f'BASELINE {base["median"]:+.2f} mmHg true, raw p2p {base["raw_p2p"]:.0f} counts',
          flush=True)
    if base['raw_p2p'] > 60:
        raise RuntimeError(f'baseline noise {base["raw_p2p"]:.0f} counts: hands off and retry')

    print(f'CHECK: plunger tied at {g1:g} mL, cuff attached the same way as in the dataset, '
          f'hands off the rig', flush=True)

    try:
        b.command('seal', r'\[Valve2\] CLOSE PC1=LOW')
    except BaseException:
        pass
    b.observe(1.0)

    b.pressure_ceiling = start + 60
    b.deadline = time.monotonic() + 300
    events_before = len(b.lines)
    b.command('target %d' % start, fr'inflate target set to {start} mmHg')
    b.command('start', r'\[Inflate\] START')
    b.wait(lambda: any('target reached' in s for s in b.lines[events_before:]), 90,
           'target not reached')
    b.command('seal', r'\[Valve2\] CLOSE PC1=LOW')
    note('sealed_at_target')
    b.deadline = time.monotonic() + 1800

    print(f'SETTLING {SETTLE_S:.0f} s. Do not touch anything: compression heats the gas and the '
          f'first 30 s loses about 15 percent.', flush=True)
    b.observe(SETTLE_S)
    note('settle_done')

    print(f'>>> PLATEAU A: hands off for {PLATEAU_A_S:.0f} s. Plunger stays tied at {g1:g} mL. '
          f'Tell me the graduation you read.', flush=True)
    a = read_plateau('A', PLATEAU_A_S)
    note('plateau_A_done')

    print(f'>>> NOW: release the tie, pull the plunger smoothly to {g2:g} mL in 2-3 s, '
          f're-tie it immediately, then take both hands off the rig.', flush=True)
    before_b = wait_for_pull(600.0)
    if before_b is None:
        raise RuntimeError('first pull not seen')
    note('pull_1_done', p_before=round(before_b['median'], 3),
         t_before_ms=int(before_b['t_last'] * 1000))
    print(f'>>> PLATEAU B: hands off for {PLATEAU_BC_S:.0f} s. Tell me the graduation you read.',
          flush=True)
    read_plateau('B', PLATEAU_BC_S)
    note('plateau_B_done')

    print(f'>>> NOW: release the tie, pull the plunger to {g3:g} mL, re-tie, hands off.',
          flush=True)
    before_c = wait_for_pull(600.0)
    if before_c is None:
        print('    second pull not seen; the first equation still stands', flush=True)
        note('pull_2_missing')
    else:
        note('pull_2_done', p_before=round(before_c['median'], 3),
             t_before_ms=int(before_c['t_last'] * 1000))
        print(f'>>> PLATEAU C: hands off for {PLATEAU_BC_S:.0f} s. Tell me the graduation.',
              flush=True)
        read_plateau('C', PLATEAU_BC_S)
        note('plateau_C_done')

    report['outcome'] = 'completed'
    print()
    print('EVENT TIMES RECORDED. Volume is computed offline by')
    print(f'   python tmp/syringe_analyze_20261109.py {name}')
    print('  because the fit windows and the extrapolation to each pull can then be varied')
    print('  without touching the hardware again.', flush=True)
except BaseException as exc:
    report['error'] = repr(exc)
    report['outcome'] = 'failed'
    print('ERROR', repr(exc), flush=True)
finally:
    try:
        b.command('vent', r'\[Deflate\] VENT')
        b.observe(2.0)
    except BaseException as vent_error:
        print('VENT ERROR', repr(vent_error), flush=True)
    try:
        b.sock.close()
    except Exception:
        pass
    log.close()
    out = ROOT / 'tmp' / 'omniprobe' / f'{name}.events.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('WROTE', out.relative_to(ROOT), flush=True)
