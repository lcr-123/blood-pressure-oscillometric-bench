"""Let the gas itself push the plunger out, and read the volume at high pressure.

Why the low-pressure method failed
    The atmosphere test worked mechanically - the syringe is sealed and leak-free, the
    plateau sat at 1.5-1.7 mmHg for 240 s with a slope of only -0.07 mmHg/min - but
    26 mL of stroke moved the pressure by just 7 mmHg instead of the 58-191 mmHg that
    gas law predicts for any plausible loop. Applying the same equation to that number
    gives V = 2822 cc, which this rig does not have.

    The explanation is compliance, not volume. Near 0 gauge the cuff bladder and its
    foam are floppy: pressure can be absorbed by the walls bulging instead of by the
    gas compressing. Effective volume and gas volume are only equal when the walls are
    taut, and the walls are taut at 150-260 mmHg. That is why the earlier attempts at
    240 mmHg were the right pressure - they just asked the operator to pull against
    1.0 kgf, which never worked.

    So: keep the high pressure, and let the GAS do the work. At 240 mmHg the gas pushes
    the plunger OUT by itself with about 1.0 kgf. The operator does not pull; the
    operator lets go.

Sequence
    1. vent   - valve2 open, plunger pushed fully HOME (0 mL). No force is needed
                because there is no pressure yet.
    2. seal, then inflate to 240 mmHg with the MCU pump. The gas is now compressed
                into the small rest-volume and is at 240 mmHg.
    3. sealed settle - the 60 s wait, so the compression heat from pumping is gone
                before any measurement starts.
    4. release - the plunger is let go. The gas expands it out to the hard stop,
                which is the state the stop holds forever. The pressure falls by a
                known relationship to V.
    5. plateau - read the settled pressure; also report the first-read value, because
                the expansion cools the gas and the reading recovers upward.

        V = (atm + P2) * 26 / ((atm + P1) - (atm + P2))

    Predicted fall from 240 mmHg with 26 mL:

        V = 342 cc -> 240 falls to 169   (fall 71)
        V = 300 cc -> 240 falls to 160   (fall 80)
        V = 150 cc -> 240 falls to  92   (fall 148)
        V = 123 cc -> 240 falls to  66   (fall 175)

    So a fall near 70 mmHg means the big loop and a fall near 150 means a small one.
    Either way it is tens of millimetres, not the 7 that compliance gave.

Usage: python tools/high_pressure_release.py [target_mmhg] [name]
"""
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

# The bridge module lives in tmp/ (it is a scratch harness, not a deliverable), so a
# copy of this script inside tools/ has to look one level up as well as beside itself.
_HERE = Path(__file__).resolve().parent
for _candidate in (_HERE, _HERE.parent / 'tmp'):
    if (_candidate / 'direct_serial_bridge_20261107.py').exists():
        sys.path.insert(0, str(_candidate))
        break
from direct_serial_bridge_20261107 import ROOT, open_bridge  # noqa: E402

TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 240
NAME = sys.argv[2] if len(sys.argv) > 2 else f'release{TARGET}_20261109'
STROKE_ML = 26.0
ATM = 760.0
SETTLE_S = 75.0
STEP_MMHG = 15.0
STEP_WINDOW_MS = 6000
PERSIST_S = 3.0
TOLERANCE_MMHG = 3.0
WAIT_S = 1200.0
HOLD_S = 210.0
MV_TO_MMHG = 81.529 / 1000.0
SNAPSHOTS = (0, 5, 10, 20, 30, 45, 60, 90, 120, 150, 180, 210)

START_FLAG = ROOT / 'tmp' / 'omniprobe' / 'release_home.flag'
if START_FLAG.exists():
    START_FLAG.unlink()

log_path = ROOT / 'tmp' / 'omniprobe' / f'{NAME}.ndjson'
samples_path = ROOT / 'tmp' / 'omniprobe' / f'{NAME}.samples.json'
if samples_path.exists():
    raise SystemExit(f'{samples_path.name} exists; pick another name')

log = open(log_path, 'w', encoding='utf-8')
b = open_bridge(log)
report = dict(run=NAME, target_mmhg=TARGET, stroke_ml=STROKE_ML, atm_mmhg=ATM,
              method='gas pushes the plunger out from the home stop at high pressure',
              nonhuman_fixture_confirmed=True)


def send(text, pattern, tries=3):
    last = None
    for attempt in range(1, tries + 1):
        try:
            return b.command(text, pattern)
        except TimeoutError as exc:
            last = exc
            print(f'   (no echo for "{text}", attempt {attempt}/{tries})', flush=True)
            time.sleep(0.5)
    raise last


def poll_safe(timeout=0.05):
    try:
        b.poll(timeout)
    except RuntimeError as exc:
        if 'stale/nonmonotonic' not in str(exc):
            raise
        was = b.active
        b.active = False
        try:
            b.poll(timeout)
        finally:
            b.active = was


def wait_safe(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        poll_safe(min(0.05, max(0.005, end - time.monotonic())))


def true_mmhg(ms=1500):
    """Unclamped pressure from the sensor node; the est column clamps at 0."""
    if not b.samples:
        return float('nan')
    newest = b.samples[-1]['timestamp']
    seg = [p['sensor'] for p in b.samples if newest - p['timestamp'] <= ms]
    return statistics.median(seg) * MV_TO_MMHG - 20.03 if seg else float('nan')


def slope_per_min(seconds):
    if len(b.samples) < 30:
        return float('nan')
    newest = b.samples[-1]['timestamp']
    seg = [p for p in b.samples if newest - p['timestamp'] <= seconds * 1000]
    if len(seg) < 20:
        return float('nan')
    ts = [p['timestamp'] / 1000.0 for p in seg]
    ps = [p['sensor'] * MV_TO_MMHG - 20.03 for p in seg]
    mt = sum(ts) / len(ts)
    mp = sum(ps) / len(ps)
    num = sum((t - mt) * (p - mp) for t, p in zip(ts, ps))
    den = sum((t - mt) ** 2 for t in ts)
    return num / den * 60.0 if den else float('nan')


def solve(p1, p2, g=STROKE_ML, atm=ATM):
    """Volume from a pressure fall caused by expanding g mL out of the loop."""
    d = (atm + p1) - (atm + p2)
    if d <= 0:
        return None
    return (atm + p2) * g / d


def persists(samples, taken_at_ms):
    """The new level must hold, not just dip."""
    if not samples:
        return False
    now = samples[-1]['timestamp']
    if now - taken_at_ms < PERSIST_S * 1000:
        return False
    marks = []
    edge = now - PERSIST_S * 1000
    with_edge = edge
    while with_edge < now - 200:
        seg = [p['sensor'] for p in samples
               if with_edge <= p['timestamp'] <= with_edge + 500]
        if len(seg) >= 5:
            marks.append(statistics.median(seg) * MV_TO_MMHG - 20.03)
        with_edge += 500
    if len(marks) < 3:
        return False
    centre = statistics.median(marks)
    return all(abs(m - centre) <= TOLERANCE_MMHG for m in marks)


try:
    b.wait(lambda: bool(b.messages), 3, 'missing hello')
    we = b.messages[0].get('writeEnabled', {})
    if not (we.get('serial') if isinstance(we, dict) else we):
        raise RuntimeError('bridge serial write permission missing')
    st = send('status', r'\[UART3\]')
    report['initial_status'] = st
    report['calibration_readback'] = send('cal', r'\[Cal\]')
    if not any('cal=VALID' in s for s in st):
        raise RuntimeError('calibration invalid')

    # ---- stage 1: plunger fully home while the loop is at atmosphere ----------
    send('vent', r'\[Deflate\] VENT')
    wait_safe(5.0)
    print('\n' + '#' * 74, flush=True)
    print('#  >>>>>>  PUSH THE PLUNGER FULLY HOME (0 mL) AND KEEP IT THERE  <<<<<<',
          flush=True)
    print('#  valve2 is open, so this takes no force at all', flush=True)
    print('#  when it is home, say so; I seal and pump up to %d mmHg' % TARGET, flush=True)
    print('#' * 74 + '\n', flush=True)
    t0 = time.monotonic()
    while time.monotonic() - t0 < 600:
        poll_safe(0.05)
        if START_FLAG.exists():
            break
        if int(time.monotonic() - t0) % 15 == 0:
            pass
    else:
        raise RuntimeError('nobody confirmed the home position')
    report['level_at_home'] = round(true_mmhg(2000), 2)
    send('seal', r'\[Valve2\] CLOSE PC1=LOW')
    wait_safe(3.0)
    report['sealed_level'] = round(true_mmhg(2000), 2)

    # ---- stage 2: inflate to target -----------------------------------------
    b.active = True
    b.deadline = time.monotonic() + 200
    b.pressure_ceiling = TARGET + 30
    events = len(b.lines)
    send('target %d' % TARGET, fr'inflate target set to {TARGET} mmHg')
    send('start', r'\[Inflate\] START')
    b.wait(lambda: any('target reached' in s for s in b.lines[events:]), 150,
           'target not reached')
    report['inflate'] = [s for s in b.lines[events:] if 'target reached' in s][-1]
    send('seal', r'\[Valve2\] CLOSE PC1=LOW')
    report['sealed_pins'] = send('pins', r'PB8=HIGH PC1=LOW PC8=HIGH')
    if any('[Deflate] PWM started' in s for s in b.lines[events:]):
        raise RuntimeError('deflate PWM started; the loop is not sealed')
    print(f'INFLATED  {report["inflate"].strip()}', flush=True)

    # ---- stage 3: settle, so pumping heat is gone ---------------------------
    b.deadline = time.monotonic() + SETTLE_S + WAIT_S + HOLD_S + 180
    b.pressure_ceiling = 4000
    print(f'\nSETTLING {SETTLE_S:.0f} s (pump heat bleeds off; do not touch the plunger)',
          flush=True)
    wait_safe(SETTLE_S)
    p1 = true_mmhg(4000)
    report['p1_mmhg'] = round(p1, 2)
    report['settle_slope_mmhg_per_min'] = round(slope_per_min(30.0), 2)
    print(f'P1 = {p1:.2f} mmHg, last-30s slope {report["settle_slope_mmhg_per_min"]:+.2f} '
          f'mmHg/min', flush=True)
    if report['settle_slope_mmhg_per_min'] < -12.0:
        raise RuntimeError(f'plateau still falling at '
                           f'{report["settle_slope_mmhg_per_min"]:+.1f} mmHg/min; '
                           f'not settled enough to attribute the fall to the expansion')

    # ---- stage 4: release, the gas expands the plunger ----------------------
    print('\n' + '#' * 74, flush=True)
    print('#  >>>>>>  LET GO OF THE PLUNGER  <<<<<<', flush=True)
    print(f'#  the {TARGET} mmHg gas pushes it out on its own, about 1.0 kgf', flush=True)
    print('#  do not pull, do not resist; just release and take your hand away',
          flush=True)
    print('#  expected fall from %.0f mmHg: to about 180 (big loop) or 150 (small loop)'
          % p1, flush=True)
    print('#' * 74 + '\n', flush=True)

    t_release = time.monotonic()
    lowest = p1
    fall_at = None
    next_tick = t_release
    while time.monotonic() - t_release < WAIT_S:
        poll_safe(0.05)
        now = true_mmhg(1200)
        lowest = min(lowest, now)
        if now < lowest + TOLERANCE_MMHG:
            lowest = now
        if fall_at is None and p1 - now >= STEP_MMHG:
            fall_at = b.samples[-1]['timestamp']
            print(f'   FALL DETECTED at {datetime.now():%H:%M:%S}: '
                  f'{p1:.1f} -> {now:.1f} mmHg', flush=True)
        if fall_at and persists(b.samples, fall_at):
            print(f'   level held for {PERSIST_S:.0f} s: {now:.1f} mmHg', flush=True)
            break
        if time.monotonic() >= next_tick:
            next_tick = time.monotonic() + 10.0
            print(f'   {time.monotonic() - t_release:4.0f} s   level {now:7.1f} mmHg   '
                  f'lowest {lowest:7.1f}', flush=True)
    else:
        raise RuntimeError('the plunger never moved; the gas was not able to push it out')
    p2_raw = true_mmhg(3000)
    report['p2_first_mmhg'] = round(p2_raw, 2)

    # ---- stage 5: plateau, the expansion cools the gas then recovers --------
    print(f'\nHOLDING {HOLD_S:.0f} s to let the cooled gas come back to room temperature',
          flush=True)
    hold_start = time.monotonic()
    snaps = {}
    idx = 0
    while True:
        elapsed = time.monotonic() - hold_start
        while idx < len(SNAPSHOTS) and elapsed >= SNAPSHOTS[idx]:
            snaps[SNAPSHOTS[idx]] = round(true_mmhg(1500), 1)
            idx += 1
        if elapsed >= HOLD_S:
            break
        poll_safe(0.05)
    b.active = False
    report['plateau_by_seconds'] = snaps
    print('PLATEAU', json.dumps(snaps), flush=True)
    p2 = snap_choice = snaps.get(120) or snaps.get(max(snaps)) or true_mmhg(3000)
    p2 = true_mmhg(4000)
    report['p2_settled_mmhg'] = round(p2, 2)
    report['fall_mmhg'] = round(p1 - p2, 2)
    v = solve(p1, p2)
    report['volume_cc'] = round(v, 1) if v else None
    v_first = solve(p1, p2_raw)
    report['volume_from_first_read_cc'] = round(v_first, 1) if v_first else None
    print(f'\nP1 {p1:.1f} -> P2 {p2:.1f} mmHg   (fall {report["fall_mmhg"]:.1f})',
          flush=True)
    if v:
        print(f'\nVERDICT  loop volume = {v:.0f} cc '
              f'(from the settled read; first read would give {v_first:.0f} cc)',
              flush=True)
        if v > 500 or v < 40:
            print('         that is outside the physically plausible range, so the'
                  ' expansion still included cuff compliance or a leak', flush=True)
        elif v > 250:
            print('         LARGE branch: E = 342 cc predicted; the cuff holds ~315 cc',
                  flush=True)
        elif v < 120:
            print('         SMALL branch: canister in circuit, cuff around 40 cc',
                  flush=True)
        else:
            print('         MID branch: between the two nominal cases', flush=True)
        report['verdict'] = 'volume_measured'
    else:
        report['verdict'] = 'no_fall'
        print('\nVERDICT  no pressure fall, so no volume can be derived.', flush=True)
    report['outcome'] = 'release_completed'
except BaseException as exc:
    report['error'] = repr(exc)
    report['outcome'] = 'failed'
    print('ERROR', repr(exc), flush=True)
finally:
    try:
        b.active = False
    except Exception:
        pass
    try:
        send('vent', r'\[Deflate\] VENT')
    except BaseException as vent_error:
        print('VENT ERROR', repr(vent_error), flush=True)
    report['nonpressure_lines'] = [s for s in b.lines
                                   if not s.startswith('[Pressure]')
                                   and not s.startswith('{')][-40:]
    samples = list(b.samples)
    try:
        b.sock.close()
    except Exception:
        pass
    log.close()
    samples_path.write_text(json.dumps(
        [{k: s[k] for k in ('timestamp', 'raw', 'sensor', 'est', 'valid')} for s in samples]) + '\n',
        encoding='utf-8')
    if START_FLAG.exists():
        START_FLAG.unlink()
    (ROOT / 'tmp' / 'omniprobe' / f'{NAME}.result.json').write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('RESULT', json.dumps({k: report[k] for k in report
                               if k != 'nonpressure_lines'}, ensure_ascii=False), flush=True)
