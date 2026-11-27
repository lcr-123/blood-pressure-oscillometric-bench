"""Talk to the BP Pump 2 over its RS-232 port, and prove the link before using it.

Why this exists
    Every pressure number in the dataset comes from one MPXV5050GP behind one ADS1115.
    We have shown that chain is steady (25.0 ms point to point, no jitter across 59
    runs) and that it agrees with the panel to within 0.9 mmHg - but the panel is also
    something we read, so the honest claim has always been "self-consistent", never
    "independently verified". The BP Pump 2 has its own pressure sensor on the same
    manifold, and Appendix D of its manual exposes it as [GAUGE]. Reading that over
    RS-232 gives a second, instrument-grade measurement of the same pressure node.

Protocol (manual Appendix D, tmp/pdfs/opmanual_text.txt:3031-3302)
    Serial settings are fixed: 9600 baud, 8 data bits, no parity, 1 stop bit.
    Commands are ASCII in square brackets. A valid command is answered with ACK
    (0x06), optionally followed by data, then CR-LF. An invalid one gets NAK (0x15).

    Read-only commands used here:
        [BP_VERSION]  -> ACK + "2780201 Ver X.XX" + CRLF
        [BP_SERIAL]   -> ACK + serial number + CRLF
        [GAUGE]       -> ACK + pressure port reading + CRLF

    Nothing in this script changes the Tester's state. The state-changing commands
    ([CUFF_EXT], [SIM_STD120_80], [PSOURCE,XXX], [LEAK,XXX], [BLEED_SYSTEM]) are
    deliberately not sent; adding them is a separate decision.

Wiring, which is NOT established
    The Tester presents a D-9 female connector (manual:601). Whether the link needs a
    straight-through or a null-modem cable is not stated anywhere in the manual, which
    only lists "RS-232 Serial Cable (9M-9F)" as an accessory. Measure continuity before
    powering anything: pins 2-3 crossed means null modem. Guessing here risks driving
    two outputs against each other.

Usage
    python tools/bp_pump2_remote.py --list
    python tools/bp_pump2_remote.py --port COM7
    python tools/bp_pump2_remote.py --port COM7 --gauge 5 --interval 0.2
"""
import argparse
import sys
import time

import serial
from serial.tools import list_ports

# The MCU link is a Horco CMSIS-DAP composite device. It is NOT the Tester, and
# opening it at 9600 would just splatter bytes at the firmware.
MCU_VID_PID = 'FAED:4870'
BAUD = 9600
ACK = 0x06
NAK = 0x15


def candidates():
    """Serial ports that are not the MCU link."""
    out = []
    for port in list_ports.comports():
        hwid = (port.hwid or '').upper()
        if MCU_VID_PID in hwid:
            continue
        out.append(port)
    return out


def list_ports_and_exit():
    ports = list(list_ports.comports())
    if not ports:
        print('no serial ports at all - nothing enumerated')
        return 1
    print(f'{len(ports)} port(s):')
    for port in ports:
        mark = '  <- MCU link, skip' if MCU_VID_PID in (port.hwid or '').upper() else ''
        print(f'  {port.device:8} | {port.description} | {port.hwid}{mark}')
    usable = candidates()
    print()
    if usable:
        print('candidates for the Tester: ' + ', '.join(p.device for p in usable))
    else:
        print('no candidate: the only port present is the MCU link. '
              'Windows has not enumerated an RS-232 adapter.')
    return 0


def drain(port, seconds):
    """Collect whatever arrives, without blocking past `seconds`."""
    port.timeout = 0.05
    deadline = time.monotonic() + seconds
    raw = bytearray()
    while time.monotonic() < deadline:
        chunk = port.read(64)
        if chunk:
            raw.extend(chunk)
            deadline = max(deadline, time.monotonic() + 0.15)
    return bytes(raw)


def describe(raw):
    """Turn an ACK-plus-text reply into something readable."""
    if not raw:
        return 'no bytes at all'
    parts = []
    if raw[0] == ACK:
        parts.append('ACK')
        raw = raw[1:]
    elif raw[0] == NAK:
        return 'NAK - the command was rejected'
    text = raw.decode('ascii', errors='replace').strip()
    if text:
        parts.append(repr(text))
    return ' + '.join(parts)


def command(port, text, wait=1.0):
    if not text.startswith('['):
        text = f'[{text}]'
    port.reset_input_buffer()
    port.write(text.encode('ascii') + b'\r')
    port.flush()
    return drain(port, wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true', help='only list ports and exit')
    ap.add_argument('--port', help='port holding the Tester, e.g. COM7')
    ap.add_argument('--gauge', type=int, default=0,
                    help='also read [GAUGE] this many times')
    ap.add_argument('--interval', type=float, default=0.2,
                    help='seconds between [GAUGE] reads')
    args = ap.parse_args()

    if args.list or not args.port:
        return list_ports_and_exit()

    try:
        port = serial.Serial(args.port, BAUD, bytesize=8, parity='N',
                             stopbits=1, timeout=0.3, write_timeout=1.0)
    except Exception as exc:                                   # noqa: BLE001
        print(f'cannot open {args.port}: {exc}')
        print('if this says PermissionError, another program owns the port')
        return 2

    with port:
        print(f'opened {args.port} at {BAUD} 8N1')

        print('\n[BP_VERSION]  (read-only: proves the link and the protocol)')
        reply = command(port, 'BP_VERSION', wait=1.5)
        print('  ' + describe(reply))
        if not reply:
            print('\n  nothing came back. In order of likelihood:')
            print('    1. the cable is straight-through and the Tester needs pins 2-3 crossed')
            print('       (or the reverse) - measure continuity before swapping blindly')
            print('    2. the adapter is a TTL-level part, not a real RS-232 transceiver')
            print('    3. wrong port: this may be some other device that happens to be a COM port')
            return 3
        if reply[0] == NAK:
            print('  the port answered with NAK, so something IS listening and speaking;')
            print('  check the command spelling and that it ends with CR only')

        print('\n[BP_SERIAL]')
        print('  ' + describe(command(port, 'BP_SERIAL', wait=1.5)))

        if args.gauge:
            print(f'\n[GAUGE] x{args.gauge} every {args.interval:.2f} s')
            for index in range(args.gauge):
                reply = command(port, 'GAUGE', wait=0.8)
                print(f'  {index:3d}  {describe(reply)}')
                time.sleep(args.interval)

        print('\nlink works. nothing was changed on the Tester.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
