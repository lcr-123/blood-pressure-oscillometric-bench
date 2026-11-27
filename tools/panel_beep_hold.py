"""Read the Tester's panel `Measured` number at known instants, using beeps as the clock.

Why this exists
    Every previous attempt to pair a panel reading with the serial path failed for the
    same reason, and it was not the operator and not the panel: a background job's
    console output never reaches the operator's screen. The `READ THE PANEL NOW` banner
    that tools/panel_vs_gauge.py prints is only visible to the agent, so the operator
    had nothing to time a reading against except the pump stopping. Five separate
    readings (143, 140, 144, 244, 238) all landed on the MCU value 0.3-2.8 s after the
    pump stopped, which is exactly what "read it when the noise stops" produces.

    A sound is a channel that does reach the operator. This script inflates to one
    point, seals, and then emits one short beep every `--interval` seconds, `--cues`
    times, starting `--first-cue` seconds after the pump stops. Each beep is a moment
    the operator can read the panel at, and each beep has a wall-clock timestamp in the
    saved report, so a reported number can be paired with both the MCU trace and the
    `[GAUGE]` trace at the same instant.

Why the holds are long and the pressure keeps moving
    The loop leaks, so the number on the panel falls steadily through the cue sequence.
    That is a feature: the sequence of six readings forms a shape, and a shape can be
    matched against two candidate traces even if any single pairing is ambiguous. The
    report stores both full traces, at 40 Hz for the MCU and about 1.2 Hz for `[GAUGE]`.

What this cannot do
    The panel shows whole mmHg, so an offset is resolved to about 1-2 mmHg. Both numbers
    come from the same transducer, so this says nothing about absolute accuracy; it only
    decides whether the -0.97 %/100 scale difference lives in the display path or in the
    sensor path.

Usage:
    python tools/panel_beep_hold.py --point 250 --cues 6 --interval 10 --first-cue 4
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
BEEP_HZ = 1000
BEEP_MS = 220


class GaugePoller(threading.Thread):
    """Poll `[GAUGE]` as fast as it answers and keep every sample with a timestamp."""

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

    def between(self, start_ms, end_ms=None):
        end = float('inf') if end_ms is None else end_ms
        return [(t, v) for t, v in self.rows if start_ms <= t <= end]

    def close(self):
        self.stop.set()
        self.join(timeout=3.0)
        try:
            self.port.close()
        except Exception:                                  # noqa: BLE001
            pass


def beep():
    """One short tone. Silence on failure: never let audio break a measurement run."""
    try:
        import winsound
        winsound.Beep(BEEP_HZ, BEEP_MS)
    except Exception:                                      # noqa: BLE001
        print('    <beep not available>', flush=True)


def cmd(b, text, pattern, tries=3):
    last = None
    for _ in range(tries):
        try:
            return b.command(text, pattern)
        except Exception as exc:                           # noqa: BLE001
            last = exc
    raise RuntimeError(f'command {text!r} failed {tries}x: {last}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tester-port', default='COM12')
    ap.add_argument('--point', type=int, default=250)
    ap.add_argument('--cues', type=int, default=6,
                    help='how many beeps, i.e. how many panel readings are asked for')
    ap.add_argument('--interval', type=float, default=10.0,
                    help='seconds between beeps')
    ap.add_argument('--first-cue', type=float, default=4.0,
                    help='seconds after the pump stops for the first beep')
    ap.add_argument('--tail', type=float, default=6.0,
                    help='seconds to keep recording after the last beep')
    ap.add_argument('--arm-delay', type=float, default=50.0,
                    help='seconds to keep beeping softly before inflating, so the '
                         'operator has time to walk over after the job is launched')
    ap.add_argument('--target-ceiling', type=int, default=275)
    args = ap.parse_args()

    if args.point > args.target_ceiling:
        raise SystemExit(f'point {args.point} exceeds the {args.target_ceiling} mechanism')

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = ROOT / 'tmp' / 'omniprobe' / f'panel_beep_{stamp}.ndjson'
    out_path = ROOT / 'data' / 'reports' / f'panel_beep_{stamp}.json'

    try:
        serial.Serial(args.tester_port, 9600, timeout=0.2).close()
    except Exception as exc:                              # noqa: BLE001
        print(f'cannot open the Tester port {args.tester_port}: {exc}')
        print('the BP Pump 2 RS-232 adapter is not present or is held by another program.')
        return 2

    poller = GaugePoller(args.tester_port)
    poller.start()
    time.sleep(1.5)

    total_hold = args.first_cue + args.interval * (args.cues - 1) + args.tail
    log = open(log_path, 'w', encoding='utf-8')
    b = open_bridge(log)
    report = dict(point_mmhg=args.point, cues=args.cues, interval_seconds=args.interval,
                  first_cue_seconds=args.first_cue, hold_seconds=round(total_hold, 1),
                  tester_port=args.tester_port, nonhuman_fixture_confirmed=True,
                  operator_task='read the panel Measured number at each beep, report in order',
                  started=stamp, cue_ms=[], operator_panel_values=None)
    try:
        cmd(b, 'status', r'\[UART3\]')

        print('=== zero before the hold ===')
        cmd(b, 'vent', r'\[Deflate\] VENT')
        b.observe(4.0)
        cmd(b, 'seal', r'\[Valve2\] CLOSE PC1=LOW')
        b.observe(5.0)
        mcu = [s['est'] for s in b.samples][-80:]
        gauge = [v for _, v in poller.rows[-10:]]
        report['zero'] = dict(mcu_mmhg=round(statistics.median(mcu), 2),
                              tester_mmhg=round(statistics.median(gauge), 2)
                              if gauge else None)
        print('  ', json.dumps(report['zero'], ensure_ascii=False))

        # The agent launches this script in the background, so nothing printed here ever
        # reaches the operator's screen. A beep train is the only channel that does.
        # It says "get ready, the machine is about to inflate", and it tightens into a
        # fast trill in the last few seconds so the operator is watching the panel when
        # the pump starts.
        #
        # The beeps are paced with `b.observe` rather than `time.sleep`, and that is not
        # cosmetic: an earlier run sat silent through 45 s of arming and the workbench
        # dropped the idle TCP session, so the first `vent` died with
        # `[WinError 10054] 远程主机强迫关闭了一个现有的连接`. Polling keeps it alive.
        print(f'=== arming, {args.arm_delay:.0f} s of beeps before the first inflation ===')
        arm_end = time.monotonic() + args.arm_delay
        while time.monotonic() < arm_end:
            left = arm_end - time.monotonic()
            print(f'  arming  {left:4.0f} s left', flush=True)
            if left > 15.0:
                beep()
                b.observe(4.0)
            elif left > 3.0:
                beep()
                b.observe(0.6)
            else:
                b.observe(0.3)
        print('  armed', flush=True)

        print(f'\n=== hold at {args.point} mmHg, then {args.cues} beeps ===')
        b.pressure_ceiling = args.point + 30
        b.deadline = time.monotonic() + 120.0
        b.active = True
        events = len(b.lines)
        cmd(b, f'target {args.point}', fr'inflate target set to {args.point} mmHg')
        cmd(b, 'start', r'\[Inflate\] START')
        window_start_ms = time.time() * 1000.0
        b.wait(lambda: any('target reached' in s for s in b.lines[events:]),
               60, f'target {args.point} not reached')
        stop_ms = time.time() * 1000.0
        cmd(b, 'seal', r'\[Valve2\] CLOSE PC1=LOW')
        cmd(b, 'pins', r'PB8=HIGH PC1=LOW PC8=HIGH')
        if any('[Deflate] PWM started' in s for s in b.lines[events:]):
            raise RuntimeError('deflate PWM started; the loop is not sealed')

        b.pressure_ceiling = args.point + 15
        b.deadline = time.monotonic() + total_hold + 120.0
        for index in range(args.cues):
            cue_at = args.first_cue + args.interval * index
            while (time.time() * 1000.0 - stop_ms) / 1000.0 < cue_at:
                b.observe(0.2)
            cue_ms = time.time() * 1000.0
            report['cue_ms'].append(round(cue_ms, 1))
            recent = [s['est'] for s in b.samples][-20:]
            gauge_now = [v for _, v in poller.rows[-1:]]
            print(f'  BEEP {index + 1}/{args.cues}  '
                  f'+{(cue_ms - stop_ms) / 1000.0:5.1f} s after the pump stopped   '
                  f'mcu {statistics.median(recent) if recent else float("nan"):6.1f}   '
                  f'serial gauge '
                  f'{gauge_now[0] if gauge_now else float("nan"):6.1f}', flush=True)
            beep()
        while (time.time() * 1000.0 - stop_ms) / 1000.0 < total_hold:
            b.observe(0.5)
        b.active = False

        trace = poller.between(window_start_ms)
        values = [v for _, v in trace]
        mcu_full = [[s['timestamp'], round(s['est'], 2)] for s in b.samples
                    if s['timestamp'] >= window_start_ms]
        report['stop_ms'] = round(stop_ms, 1)
        report['window_start_ms'] = round(window_start_ms, 1)
        report['gauge_points'] = len(values)
        report['gauge_first'] = round(values[0], 1) if values else None
        report['gauge_last'] = round(values[-1], 1) if values else None
        report['gauge_median'] = round(statistics.median(values), 1) if values else None
        report['gauge_trace'] = [[round(t, 1), v] for t, v in trace]
        report['mcu_trace'] = mcu_full
        report['cues'] = []
        for index, cue_ms in enumerate(report['cue_ms']):
            near = [v for t, v in poller.between(cue_ms - 1200.0, cue_ms + 1200.0)]
            mcu_near = [s['est'] for s in b.samples
                        if abs(s['timestamp'] - cue_ms) <= 300.0]
            report['cues'].append(dict(
                index=index + 1,
                after_pump_stop_s=round((cue_ms - stop_ms) / 1000.0, 2),
                gauge_mmhg=round(statistics.median(near), 1) if near else None,
                gauge_points=len(near),
                mcu_mmhg=round(statistics.median(mcu_near), 2) if mcu_near else None,
                operator_panel_value=None))
            print(f"  cue {index + 1}: +{report['cues'][-1]['after_pump_stop_s']:5.2f} s   "
                  f"serial {report['cues'][-1]['gauge_mmhg']}   "
                  f"mcu {report['cues'][-1]['mcu_mmhg']}")
        report['cues_count'] = len(report['cues'])
    except BaseException as exc:                           # noqa: BLE001
        report['error'] = repr(exc)
        print('ERROR', repr(exc), flush=True)
    finally:
        try:
            b.active = False
        except Exception:                                  # noqa: BLE001
            pass
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
