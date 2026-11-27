"""Static multi-point cross-check: the MCU sensor against the Tester's own gauge.

What this measures
    Two independent pressure channels on the same pneumatic node, compared at several
    sealed hold points. The Tester (Fluke BP Pump 2) reports whole mmHg from its own
    transducer via [GAUGE]; the MCU reports the MPXV5050G through an ADS1115 at 20 Hz.
    Neither is traceable, so this bounds their disagreement rather than proving either.

Design decisions and why (each one came from a measured failure)
    settle 90 s, not 6 s
        2026-11-09: after inflation the first 30 s of a hold lose 15% of the drop to
        compression heat (rate -21.1 mmHg/min), the next 30 s only 4% (-7.8), and the
        plateau is not thermally flat until ~90 s (-5.8, steady). Comparing at 6 s
        compares two transients.

    zero measured before AND after the sweep
        The MCU zero moved 2 mmHg between two sweeps an hour apart on 2026-11-10
        (sensor 253 -> 228 mV), which showed up as a 1.3 mmHg shift in the fitted
        intercept and 0.8 percentage points of apparent scale error. The dataset's own
        21 sealed-hold zeros span 3.58 mmHg, so this is normal behaviour, not a fault.
        Recording both ends lets the analysis correct for it instead of absorbing it
        into the slope.

    the gauge lag is dropped, not compensated
        [GAUGE] returns a value whose internal sample lags the command by 1-2 samples
        (2026-11-09: first reading was 101 mmHg below the MCU, everything after agreed
        within 2.6). The first 2 s of each window are simply discarded.

    median over an identical window on both sides
        The loop leaks ~6 mmHg/min during a hold, so a reading from one moment cannot be
        compared with one from another. Both medians are taken from the same wall-clock
        window.

    repeats inside one hold
        Re-inflating for each repeat would take 90 s of settling apiece. Splitting one
        36 s hold into three 12 s sub-windows gives within-point repeatability for free,
        which is what tells us whether the residual scatter is noise or drift.

Usage:
    python tools/bp_static_crosscheck.py --points 60,120,180,260
    python tools/bp_static_crosscheck.py --points 100,150,200,240 --settle 90 --repeats 3
"""
import argparse
import json
import statistics
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import serial

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tmp'))
from direct_serial_bridge_20261107 import open_bridge  # noqa: E402

ACK = 0x06
GAUGE_LAG_S = 2.0          # the gauge's reported value lags its command by 1-2 samples
DEFAULT_SETTLE_S = 90.0    # compression heat is not gone before this
DEFAULT_ZERO_SETTLE_S = 90.0


class GaugePoller(threading.Thread):
    """Poll [GAUGE] continuously; this laptop sustains about 1-2 Hz while the MCU runs."""

    def __init__(self, port_name):
        super().__init__(daemon=True)
        self.port = serial.Serial(port_name, 9600, bytesize=8, parity='N',
                                  stopbits=1, timeout=0.8, write_timeout=1.0)
        self.stop = threading.Event()
        self.rows = []

    def run(self):
        while not self.stop.is_set():
            try:
                self.port.reset_input_buffer()
                started = time.monotonic()
                self.port.write(b'[GAUGE]\r')
                self.port.flush()
            except Exception:                              # noqa: BLE001
                break
            raw = bytearray()
            deadline = started + 1.2
            while time.monotonic() < deadline:
                chunk = self.port.read(64)
                if chunk:
                    raw.extend(chunk)
                    if raw.endswith(b'\r\n'):
                        break
            stamp = time.time() * 1000.0
            value = None
            if raw and raw[0] == ACK:
                text = raw[1:].decode('ascii', errors='replace')
                for token in text.split('m')[0].split():
                    try:
                        value = float(token)
                        break
                    except ValueError:
                        continue
            if value is not None:
                self.rows.append((stamp, value))
            time.sleep(0.01)

    def window(self, start_ms, end_ms, skip_s=GAUGE_LAG_S):
        return [v for t, v in self.rows
                if start_ms + skip_s * 1000.0 <= t <= end_ms]

    def close(self):
        self.stop.set()
        self.join(timeout=3.0)
        try:
            self.port.close()
        except Exception:                                  # noqa: BLE001
            pass


def cmd(b, text, pattern, tries=3):
    last = None
    for _ in range(tries):
        try:
            return b.command(text, pattern)
        except Exception as exc:                           # noqa: BLE001
            last = exc
    raise RuntimeError(f'command {text!r} failed {tries}x: {last}')


def measure_zero(b, poller, seconds):
    """Sealed, vented-to-ambient zero. Records both channels plus the raw sensor mV."""
    cmd(b, 'vent', r'\[Deflate\] VENT')
    b.observe(4.0)
    cmd(b, 'seal', r'\[Valve2\] CLOSE PC1=LOW')
    b.observe(seconds)
    mcu_rows = b.samples[-int(seconds * 20):]
    est = [s['est'] for s in mcu_rows]
    sensor = [s['sensor'] for s in mcu_rows]
    gauge = [v for _, v in poller.rows[-8:]]
    return dict(mcu_mmhg=round(statistics.median(est), 2),
                mcu_sensor_mv=round(statistics.median(sensor), 1),
                tester_mmhg=round(statistics.median(gauge), 2) if gauge else None,
                settle_seconds=seconds)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tester-port', default='COM12')
    ap.add_argument('--points', default='100,150,200,240')
    ap.add_argument('--settle', type=float, default=DEFAULT_SETTLE_S,
                    help='seconds to let compression heat dissipate before measuring')
    ap.add_argument('--zero-settle', type=float, default=DEFAULT_ZERO_SETTLE_S)
    ap.add_argument('--hold', type=float, default=36.0,
                    help='total measurement time per point, split into --repeats windows')
    ap.add_argument('--repeats', type=int, default=3)
    ap.add_argument('--target-ceiling', type=int, default=275)
    args = ap.parse_args()

    points = [int(p) for p in args.points.split(',') if p.strip()]
    if max(points) > args.target_ceiling:
        raise SystemExit(f'point {max(points)} exceeds the {args.target_ceiling} mmHg ceiling')
    window_s = args.hold / args.repeats

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = ROOT / 'tmp' / 'omniprobe' / f'static_xcheck_{stamp}.ndjson'
    out_path = ROOT / 'data' / 'reports' / f'static_crosscheck_{stamp}.json'

    # Fail fast and clearly if the Tester is not attached. The FTDI adapter on this rig
    # drops out when its USB connector is nudged, and a bare traceback tells the operator
    # nothing actionable.
    try:
        serial.Serial(args.tester_port, 9600, timeout=0.2).close()
    except Exception as exc:                              # noqa: BLE001
        print(f'cannot open the Tester port {args.tester_port}: {exc}')
        print('the BP Pump 2 RS-232 adapter is not present or is held by another program.')
        print('check the USB end of the FTDI adapter, then rerun. nothing was changed.')
        return 2

    poller = GaugePoller(args.tester_port)
    poller.start()
    time.sleep(1.5)

    log = open(log_path, 'w', encoding='utf-8')
    b = open_bridge(log)
    report = dict(points_mmhg=points, settle_seconds=args.settle,
                  zero_settle_seconds=args.zero_settle, hold_seconds=args.hold,
                  repeats=args.repeats, window_seconds=window_s,
                  tester_port=args.tester_port, gauge_lag_dropped_s=GAUGE_LAG_S,
                  nonhuman_fixture_confirmed=True, started=stamp, rows=[])

    try:
        cmd(b, 'status', r'\[UART3\]')
        report['calibration'] = [s for s in cmd(b, 'cal', r'\[Cal\]') if s.startswith('[Cal]')]

        print('=== zero at start of sweep ===')
        report['zero_start'] = measure_zero(b, poller, args.zero_settle)
        print('  ', json.dumps(report['zero_start'], ensure_ascii=False))

        for point in points:
            print(f'\n=== {point} mmHg ===')

            # Descending targets need the loop bled down first. If it is still sealed at
            # 223 mmHg and we ask for 180, the firmware inflates from whatever it sees and
            # the ceiling trips ('reported pressure reached 210 mmHg' killed the 21:00
            # reverse-order sweep). Bleed to just under the target, then seal and inflate.
            current = statistics.median([s['est'] for s in b.samples][-20:]) if b.samples else 0.0
            if current > point - 5:
                print(f'  loop is at {current:.1f} mmHg, above the {point} target; bleeding down')
                cmd(b, 'vent', r'\[Deflate\] VENT')
                b.deadline = time.monotonic() + 90.0
                b.pressure_ceiling = max(current, point) + 30
                bleed_deadline = time.monotonic() + 60.0
                while time.monotonic() < bleed_deadline:
                    b.observe(1.0)
                    if not b.samples:
                        continue
                    if statistics.median([s['est'] for s in b.samples][-10:]) <= point - 8:
                        break
                cmd(b, 'seal', r'\[Valve2\] CLOSE PC1=LOW')
                b.observe(2.0)

            b.pressure_ceiling = point + 30
            b.deadline = time.monotonic() + 120.0
            b.active = True
            events = len(b.lines)
            cmd(b, f'target {point}', fr'inflate target set to {point} mmHg')
            cmd(b, 'start', r'\[Inflate\] START')
            b.wait(lambda: any('target reached' in s for s in b.lines[events:]),
                   60, f'target {point} not reached')
            cmd(b, 'seal', r'\[Valve2\] CLOSE PC1=LOW')
            cmd(b, 'pins', r'PB8=HIGH PC1=LOW PC8=HIGH')
            if any('[Deflate] PWM started' in s for s in b.lines[events:]):
                raise RuntimeError('deflate PWM started; the loop is not sealed')

            b.deadline = time.monotonic() + args.settle + args.hold + 60
            b.pressure_ceiling = point + 15
            print(f'  settling {args.settle:.0f} s (compression heat)')
            b.observe(args.settle)

            windows = []
            for index in range(args.repeats):
                start_ms = time.time() * 1000.0
                b.observe(window_s)
                end_ms = time.time() * 1000.0
                mcu = [s['est'] for s in b.samples
                       if start_ms <= s['timestamp'] <= end_ms]
                gauge = poller.window(start_ms, end_ms)
                if len(mcu) < 20 or len(gauge) < 3:
                    print(f'    window {index}: too few samples '
                          f'(mcu={len(mcu)} gauge={len(gauge)})')
                    continue
                mcu_med = statistics.median(mcu)
                gauge_med = statistics.median(gauge)
                windows.append(dict(repeat=index,
                                    mcu_mmhg=round(mcu_med, 2),
                                    tester_mmhg=round(gauge_med, 2),
                                    difference_mmhg=round(gauge_med - mcu_med, 2),
                                    mcu_first=round(mcu[0], 2),
                                    mcu_last=round(mcu[-1], 2),
                                    mcu_points=len(mcu),
                                    tester_points=len(gauge)))
                print(f'    repeat {index}: MCU {mcu_med:7.2f}  Tester {gauge_med:7.2f}  '
                      f'diff {gauge_med - mcu_med:+6.2f}   ({len(mcu)}/{len(gauge)} pts)')

            b.active = False
            if windows:
                diffs = [w['difference_mmhg'] for w in windows]
                row = dict(requested_mmhg=point, windows=windows,
                           mcu_mmhg=round(statistics.median([w['mcu_mmhg'] for w in windows]), 2),
                           tester_mmhg=round(statistics.median([w['tester_mmhg'] for w in windows]), 2),
                           difference_mmhg=round(statistics.fmean(diffs), 2),
                           within_point_spread=round(max(diffs) - min(diffs), 2))
                report['rows'].append(row)
                print(f"  point mean diff {row['difference_mmhg']:+.2f}  "
                      f"within-point spread {row['within_point_spread']:.2f}")

        print('\n=== zero at end of sweep ===')
        report['zero_end'] = measure_zero(b, poller, args.zero_settle)
        print('  ', json.dumps(report['zero_end'], ensure_ascii=False))

        zs, ze = report['zero_start'], report['zero_end']
        report['zero_drift'] = dict(
            mcu_mmhg=round(ze['mcu_mmhg'] - zs['mcu_mmhg'], 2),
            mcu_sensor_mv=round(ze['mcu_sensor_mv'] - zs['mcu_sensor_mv'], 1),
            tester_mmhg=(round(ze['tester_mmhg'] - zs['tester_mmhg'], 2)
                         if ze['tester_mmhg'] is not None and zs['tester_mmhg'] is not None
                         else None))

        rows = [r for r in report['rows'] if 'difference_mmhg' in r]
        if rows:
            diffs = [r['difference_mmhg'] for r in rows]
            report['summary'] = dict(
                n=len(diffs), mean_difference=round(statistics.fmean(diffs), 2),
                min_difference=round(min(diffs), 2),
                max_difference=round(max(diffs), 2),
                spread=round(max(diffs) - min(diffs), 2),
                max_abs=round(max(abs(d) for d in diffs), 2),
                mean_within_point_spread=round(statistics.fmean(
                    [r['within_point_spread'] for r in rows]), 2))
            print('\n=== summary ===')
            print(json.dumps(report['summary'], ensure_ascii=False))
            print(json.dumps(report['zero_drift'], ensure_ascii=False))
    except BaseException as exc:                           # noqa: BLE001
        report['error'] = repr(exc)
        print('ERROR', repr(exc), flush=True)
    finally:
        try:
            b.active = False
        except Exception:                                  # noqa: BLE001
            pass
        # Vent to ambient, then CLOSE valve 2 again. Leaving it open keeps the cuff
        # connected to atmosphere indefinitely, which flattens the cuff and lets air
        # migrate through the valve seat - and it means the next run starts from an
        # unknown mechanical state. The project rule is vent -> wait for a fresh zero ->
        # seal, and this is the seal half.
        vent_ok = False
        try:
            cmd(b, 'vent', r'\[Deflate\] VENT', tries=2)
            b.observe(3.0)
            vent_ok = True
        except BaseException as vent_error:                 # noqa: BLE001
            print('VENT ERROR', repr(vent_error), flush=True)
        if vent_ok:
            try:
                cmd(b, 'seal', r'\[Valve2\] CLOSE PC1=LOW', tries=2)
                b.observe(2.0)
                for line in b.command('pins', r'\[Pins\]'):
                    if line.startswith('[Pins]'):
                        report['final_pins'] = line
                        print('final ' + line)
                        if 'PC1=LOW' not in line:
                            print('WARNING: valve 2 did not close after venting')
            except BaseException as seal_error:             # noqa: BLE001
                print('SEAL ERROR', repr(seal_error), flush=True)
                report['seal_error'] = repr(seal_error)
        poller.close()
        try:
            b.sock.close()
        except Exception:                                  # noqa: BLE001
            pass
        log.close()
        report['finished'] = datetime.now().strftime('%Y%m%d-%H%M%S')
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                            encoding='utf-8')
        print(f'\nwrote {out_path.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
