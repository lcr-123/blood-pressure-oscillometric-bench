"""Is the Tester's panel `Measured` number the same as its RS-232 `[GAUGE]` number?

Why this exists
    The 2026-10-25 calibration used the panel reading as its reference, while every
    cross-check since 2026-11-10 compares against the `[GAUGE]` string. If those two
    display paths differ by about 1%, part of the -0.97 %/100 scale difference we
    measured is a display-path offset rather than a sensor offset. The Operators
    Manual does not say whether they share a value, so this has to be measured.

Why the prompt fires during the hold, not at the pump stop
    The first two attempts prompted during a settled hold. The operator answered 143
    and 140 where the 150 point prompted at an MCU reading of 131.6, and 244 and 238
    where the 250 point prompted at 233.2. Those four numbers do lie on the MCU trace
    of the run, but 0.3-2.8 s after the pump stopped, and that is not proof of
    anything: the trace runs through every value between the stop and the prompt, so
    any number in that range "matches" somewhere. What it does show is that a prompt
    that arrives long after the pressure has moved cannot be paired with a reading.

    The third attempt prompted at the pump stop itself. The `[GAUGE]` stream answered
    105 and 202 fifteen hundredths of a second later, mid-transient, and settled to
    142 / 242 about a second after that. The stop transient is one to two seconds of
    a 2 mmHg/s coast; a reading taken inside it is worthless.

    So this version prompts once, at `--read-at` seconds after the pump stops. By then
    the compression heat has stopped moving the pressure quickly, and a reading two
    seconds early or late costs at most one or two mmHg. The banner says so, and asks
    for the number on screen at that moment rather than the one seen at the stop.

What is stored for the comparison
    Every `[GAUGE]` sample and every MCU `est` sample from the start of the ramp to the
    end of the hold, with wall-clock timestamps, so the pairing can be redone by
    `tools/panel_gauge_offset.py` however the reading has to be interpreted. Nothing is
    thrown away: the stop transient is in the trace on purpose, as evidence.

What this cannot do
    The panel has 1 mmHg resolution and the operator reports whole numbers, so this
    resolves an offset of about 1-2 mmHg, not better. It says nothing about absolute
    accuracy: both are still the same transducer.

Usage:
    python tools/panel_vs_gauge.py --points 150,250 --read-at 25 --hold 45
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
PROMPT_WINDOW_MS = 1500.0


class GaugePoller(threading.Thread):
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
        """Every sample in the window, with no lag dropped.

        The first version threw away the two seconds after a chosen start because the
        serial path was believed to lag. It does not lag: at the pump-stop transient
        the stream simply still holds the previous answer, and during a hold it tracks
        the MCU inside a 0.3 mmHg spread. So nothing is discarded here, and the window
        starts before the pump stopped so the transient itself stays analysable.
        """
        end = float('inf') if end_ms is None else end_ms
        return [(t, v) for t, v in self.rows if start_ms <= t <= end]

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tester-port', default='COM12')
    ap.add_argument('--points', default='150,250')
    ap.add_argument('--read-at', type=float, default=10.0,
                    help='seconds after the pump stops to ask for the panel reading; '
                         'the reading has to be taken while the pressure is falling '
                         'slowly, not during the fast stop transient')
    ap.add_argument('--hold', type=float, default=45.0,
                    help='recording window that keeps running after the prompt')
    ap.add_argument('--target-ceiling', type=int, default=275)
    args = ap.parse_args()

    points = [int(p) for p in args.points.split(',') if p.strip()]
    if max(points) > args.target_ceiling:
        raise SystemExit(f'point {max(points)} exceeds the {args.target_ceiling} mechanism')

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    log_path = ROOT / 'tmp' / 'omniprobe' / f'panel_vs_gauge_{stamp}.ndjson'
    out_path = ROOT / 'data' / 'reports' / f'panel_vs_gauge_{stamp}.json'

    try:
        serial.Serial(args.tester_port, 9600, timeout=0.2).close()
    except Exception as exc:                              # noqa: BLE001
        print(f'cannot open the Tester port {args.tester_port}: {exc}')
        print('the BP Pump 2 RS-232 adapter is not present or is held by another program.')
        return 2

    poller = GaugePoller(args.tester_port)
    poller.start()
    time.sleep(1.5)

    log = open(log_path, 'w', encoding='utf-8')
    b = open_bridge(log)
    report = dict(points_mmhg=points, read_at_seconds=args.read_at,
                  hold_seconds=args.hold, tester_port=args.tester_port,
                  gauge_lag_dropped_s=None, nonhuman_fixture_confirmed=True,
                  operator_task='read the panel Measured value at the pump stop',
                  started=stamp, rows=[])
    try:
        cmd(b, 'status', r'\[UART3\]')

        print('=== zero before the holds ===')
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

        for point in points:
            print(f'\n=== hold at {point} mmHg ===')
            current = (statistics.median([s['est'] for s in b.samples][-20:])
                       if b.samples else 0.0)
            if current > point - 5:
                print(f'  loop at {current:.1f}, above the {point} target; bleeding down')
                cmd(b, 'vent', r'\[Deflate\] VENT')
                b.deadline = time.monotonic() + 90.0
                b.pressure_ceiling = max(current, point) + 30
                bleed_deadline = time.monotonic() + 70.0
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
            # Everything from here on is kept: the pump ramp, the stop transient and the
            # hold. The gauge trace used to start only at the prompt, which is why the
            # readings the operator actually took could not be paired with it afterwards.
            window_start_ms = time.time() * 1000.0
            print('  ############################################################')
            print(f'  # INFLATING TO {point} mmHg. No need to read anything yet.')
            print(f'  # The prompt comes {args.read_at:.0f} s after the pump stops; read the '
                  f'panel then.')
            print('  ############################################################', flush=True)
            b.wait(lambda: any('target reached' in s for s in b.lines[events:]),
                   60, f'target {point} not reached')
            stop_ms = time.time() * 1000.0
            cmd(b, 'seal', r'\[Valve2\] CLOSE PC1=LOW')
            cmd(b, 'pins', r'PB8=HIGH PC1=LOW PC8=HIGH')
            if any('[Deflate] PWM started' in s for s in b.lines[events:]):
                raise RuntimeError('deflate PWM started; the loop is not sealed')

            b.pressure_ceiling = point + 15
            b.deadline = time.monotonic() + args.hold + 120
            remaining = args.hold
            prompted = False
            prompt_ms = None
            while remaining > 0:
                chunk = min(1.0, remaining)
                b.observe(chunk)
                remaining -= chunk
                elapsed = args.hold - remaining
                if not prompted and elapsed >= args.read_at:
                    print('  ' + '=' * 60)
                    print(f'  READ THE PANEL NOW: one whole number for `Measured`.')
                    print(f'  {elapsed:.0f} s after the pump stopped, the loop is sealed '
                          f'and the pressure is falling slowly.')
                    print('  Type it in the chat.')
                    print('  ' + '=' * 60, flush=True)
                    prompt_ms = time.time() * 1000.0
                    prompted = True
                if int(elapsed) % 5 == 0:
                    recent = [s['est'] for s in b.samples][-20:]
                    tail = [v for _, v in poller.rows][-1:]
                    print(f'    holding  {elapsed:4.1f}/{args.hold:.0f} s   mcu '
                          f'{statistics.median(recent) if recent else float("nan"):6.1f}   '
                          f'serial gauge {tail[0] if tail else float("nan"):6.1f}',
                          flush=True)
            b.active = False
            if prompt_ms is None:
                prompt_ms = time.time() * 1000.0

            trace = poller.between(window_start_ms)
            values = [v for _, v in trace]
            hold_trace = [(t, v) for t, v in trace if t >= prompt_ms]
            hold_values = [v for _, v in hold_trace]
            if trace:
                for t, v in trace[::10]:
                    print(f'    +{(t - window_start_ms) / 1000.0:6.1f} s   gauge {v:6.1f}')

                # Whatever both paths were reporting at the instant the operator was
                # told to look. The panel read is anchored to `prompt_ms`; the offset
                # that pairs a panel number with the same wall clock is computed by
                # tools/panel_gauge_offset.py from the full traces below.
                near = [v for t, v in poller.between(prompt_ms - PROMPT_WINDOW_MS,
                                                    prompt_ms + PROMPT_WINDOW_MS)]
                mcu_near = [s['est'] for s in b.samples
                            if abs(s['timestamp'] - prompt_ms) <= PROMPT_WINDOW_MS]
                mcu_hold = [s['est'] for s in b.samples if s['timestamp'] >= prompt_ms]
                row = dict(requested_mmhg=point,
                           stop_ms=round(stop_ms, 1),
                           prompt_ms=round(prompt_ms, 1),
                           gauge_at_prompt=round(statistics.median(near), 1)
                           if near else None,
                           gauge_at_prompt_points=len(near),
                           mcu_at_prompt=round(statistics.median(mcu_near), 2)
                           if mcu_near else None,
                           mcu_at_prompt_points=len(mcu_near),
                           gauge_points=len(values),
                           gauge_first=round(values[0], 1),
                           gauge_median=round(statistics.median(values), 1),
                           gauge_last=round(values[-1], 1),
                           gauge_min=round(min(values), 1),
                           gauge_max=round(max(values), 1),
                           gauge_hold_points=len(hold_values),
                           gauge_hold_first=round(hold_values[0], 1) if hold_values else None,
                           gauge_hold_last=round(hold_values[-1], 1) if hold_values else None,
                           gauge_hold_median=round(statistics.median(hold_values), 1)
                           if hold_values else None,
                           mcu_median=round(statistics.median(mcu_hold), 2)
                           if mcu_hold else None,
                           gauge_trace=[[round(t, 1), v] for t, v in trace],
                           mcu_trace=[[s['timestamp'], round(s['est'], 2)]
                                      for s in b.samples
                                      if s['timestamp'] >= window_start_ms],
                           operator_panel_value=None)
                report['rows'].append(row)
                print(f"  at the prompt: serial gauge {row['gauge_at_prompt']} "
                      f"({row['gauge_at_prompt_points']} pts)   "
                      f"mcu {row['mcu_at_prompt']} ({row['mcu_at_prompt_points']} pts)")
                print(f"  gauge over the whole window: first {row['gauge_first']:.1f}  "
                      f"median {row['gauge_median']:.1f}  last {row['gauge_last']:.1f}  "
                      f"min {row['gauge_min']:.1f}  max {row['gauge_max']:.1f}  "
                      f"({row['gauge_points']} pts)")
                print(f"  mcu median over the same window: {row['mcu_median']:.2f}")
            else:
                print('  no gauge readings in the window')
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
        print('fill in operator_panel_value per row once the operator reports them.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
