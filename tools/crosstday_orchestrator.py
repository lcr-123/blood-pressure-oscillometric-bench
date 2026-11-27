"""Cross-day capture batch: 7 presets x 2 rounds per block, two blocks per day.

Protocol: data/protocols/reference_bp_batch_crosstday_v1.md. Read that file before
running this; it fixes the design, the acceptance tests and the exclusion rules, and
none of them may be changed after the first capture.

What one day does
    1. switch Preset 1..7 over RS-232 ([SIM_STD*]) - a switch command is retried up to
       SWITCH_ATTEMPTS times with a wide first-byte window before the day is stopped
       (amendment 1, see below);
    2. two captures per preset  -> 14 rounds in block A;
    3. beep, wait for the operator to rewrap the cuff and drop the marker file;
    4. Preset 1..7 again, two captures each -> 14 rounds in block B.
    28 rounds, about 95 minutes of rig time.

Amendment 1 (2026-11-16), recorded in data/protocols/..._amend1.md
    The original rule stopped the day on the first [SIM_STD*] that did not answer.
    On day 1 that rule fired four times - three of them on the first switch of a
    block, after 19-20 minutes of RS-232 silence - even though a manual retry a
    second later answered in 0.06-0.12 s and probes answered 0.53-0.59 s. The
    instrument drops the occasional reply; treating that as "the panel cannot be
    proven" throws away a healthy day. A switch is now retried, with the SAME
    command only, and every attempt is written into the round metadata.

Design notes that are not obvious
    * The panel switch is proven by ACK only. The manual has no read-back command, and
      an ACK means "the command exists", not "the panel moved". Every round therefore
      records `panel_state_established` plus the raw switch reply, and rounds taken
      without an ACK are excluded by §4 rule 9 rather than silently kept.
    * [GAUGE] is never sent: it moves the Tester off the Standard BP screen
      (data/reports/gauge_command_side_effect_20261109.md).
    * The rewrap pause needs a positive confirmation. A silent timeout would let the
      script "assume" the cuff was rewrapped, which turns T2 (the wrap test) into a
      tautology, so a missing marker marks block B as absent for that day
      (§4 rules 10 and 11).
    * Background-job stdout is invisible to the operator, so the pause is announced
      with winsound.Beep, not with text.

Promotion (2026-11-25): this is tmp/run_crosstday_20261116.py (amend1, sha256
    e963e0fb...) moved into tools/ because tmp/ is gitignored. Exactly two behaviour
    changes, both about evidence keeping:
      * the per-slot log name now ends in the block letter
        ({tag}_p{preset}_a{attempt}_{block}.out).  Before, block B overwrote every
        block-A log on any full day -- 11 of the 27 failed slots in the cross-day
        batch lost the only file that named their cause, and the rest were only
        reattributable from the round metadata the capture script writes itself.
      * round metadata records orchestrator_path = tools/crosstday_orchestrator.py.
    Everything else -- presets, targets, attempt caps, switch policy, the rewrap
    marker protocol, the manifest schema -- is byte-identical to the frozen copy.
    The frozen copy stays in tmp/ so the published sha256 still verifies.

Usage
    python tools/crosstday_orchestrator.py --day 1 --rounds 2 --port COM12
    python tools/crosstday_orchestrator.py --day 1 --rounds 2 --dry-run
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tmp'))

CAPTURE = ROOT / 'tmp' / 'bp_standard255_195_target275_peakwindow_20261105.py'
SPLIT = ROOT / 'tmp' / 'split_export_135527.py'
GATE = ROOT / 'tools' / 'validity_v2.py'
MANIFEST = ROOT / 'tmp' / 'omniprobe' / 'crosstday_manifest.json'
REWRAP_MARKER = ROOT / 'tmp' / 'omniprobe' / 'crosstday_rewrapped.txt'

BAUD = 9600
TARGET_MMHG = 275
MAX_ATTEMPTS_FACTOR = 3      # per (preset, block) slot, so one bad round cannot stall a day
REWRAP_BEEP_EVERY_S = 20.0

# Panel-switch policy (amendment 1, 2026-11-16). See
# data/protocols/reference_bp_batch_crosstday_v1_amend1.md for why this exists:
# the Tester occasionally goes silent for more than 12 s, and the original rule
# treated a single NO REPLY as proof that the panel could not be set, which threw
# away three otherwise healthy block-A runs on day 1. A switch is now retried a
# bounded number of times with a first-byte window wide enough to outlast a silent
# spell. Only the SAME [SIM_STD*] command is ever resent, so a lost ACK cannot move
# the panel to a different preset than the one recorded, and every attempt is
# written into the round metadata as `panel_switch_attempts`.
SWITCH_WINDOW_S = 12.0
SWITCH_ATTEMPTS = 3
SWITCH_RETRY_GAP_S = 2.0

# The per-round metadata used to be written with orchestrator_sha256 = None, which left
# the rounds unable to prove which orchestrator produced them. Compute it once at import
# so every round carries the same value as the day-level manifest.
import hashlib as _hashlib
ORCHESTRATOR_SHA256 = _hashlib.sha256(Path(__file__).resolve().read_bytes()).hexdigest()

# preset -> (command, sbp, dbp, map note, pulse volume cc); manual Table 3-2
PRESETS = {
    1: ('SIM_STD120_80', 120, 80, 93, 0.68),
    2: ('SIM_STD150_100', 150, 100, 116, 0.65),
    3: ('SIM_STD200_150', 200, 150, 166, 0.60),
    4: ('SIM_STD255_195', 255, 195, 215, 0.55),
    5: ('SIM_STD60_30', 60, 30, 40, 0.75),
    6: ('SIM_STD80_50', 80, 50, 60, 0.71),
    7: ('SIM_STD100_65', 100, 65, 76, 0.69),
}


def run(args, log=None):
    result = subprocess.run([sys.executable] + [str(a) for a in args],
                            capture_output=True, text=True, cwd=str(ROOT))
    text = (result.stdout or '') + (result.stderr or '')
    if log:
        log.write_text(text, encoding='utf-8')
    return result.returncode, text


def beep():
    try:
        import winsound
        winsound.Beep(880, 250)
        winsound.Beep(660, 250)
    except Exception:
        print('\a', end='', flush=True)


def wait_for_rewrap(days: int, block: str, timeout_s: float) -> dict:
    """Block until the operator drops the marker file, or the deadline expires."""
    if REWRAP_MARKER.exists():
        REWRAP_MARKER.unlink()
    print(f'\n=== REWRAP THE CUFF NOW (before block {block}) ===', flush=True)
    print(f'  after rewrapping, create {REWRAP_MARKER.name} in tmp/omniprobe/', flush=True)
    print(f'  the run waits up to {timeout_s:.0f} s; without the marker block {block} '
          f'is recorded as absent for day {days}', flush=True)
    started = time.monotonic()
    last_beep = 0.0
    while time.monotonic() - started < timeout_s:
        if REWRAP_MARKER.exists():
            waited = time.monotonic() - started
            print(f'  marker seen after {waited:.1f} s', flush=True)
            return {'confirmed': True, 'waited_s': round(waited, 1),
                    'marker_text': REWRAP_MARKER.read_text(encoding='utf-8',
                                                           errors='replace').strip()[:200]}
        if time.monotonic() - last_beep >= REWRAP_BEEP_EVERY_S:
            beep()
            last_beep = time.monotonic()
        time.sleep(1.0)
    print(f'  no marker within {timeout_s:.0f} s: block {block} will be recorded as absent',
          flush=True)
    return {'confirmed': False, 'waited_s': round(timeout_s, 1), 'marker_text': None}


def ask_first_byte(port, text, window):
    """Send [text] and wait up to `window` s for the first byte of the reply.

    Unlike bp_preset_remote.command() this stops waiting as soon as something
    arrives, so the window can be wide without paying it on every healthy switch.
    """
    port.reset_input_buffer()
    port.timeout = 0.05
    started = time.monotonic()
    port.write(('[' + text + ']').encode('ascii') + b'\r')
    port.flush()
    raw = bytearray()
    while time.monotonic() - started < window:
        chunk = port.read(64)
        if chunk:
            raw.extend(chunk)
            break
    if raw:
        deadline = time.monotonic() + 0.4
        while time.monotonic() < deadline:
            chunk = port.read(64)
            if chunk:
                raw.extend(chunk)
                deadline = max(deadline, time.monotonic() + 0.15)
            else:
                port.timeout = 0.05
    return bytes(raw)


def switch_preset(port, preset, bpr) -> dict:
    """Send [SIM_STD*] and report exactly what came back, retrying a silent Tester.

    Amendment 1 (2026-11-16): a single NO REPLY used to stop the whole day. The
    Tester has been observed silent for >12 s on a link that answers in 0.55 s
    moments later, so the switch is retried with the same command. The reply that
    counts is the first ACK; every attempt is kept so the record shows what happened.
    """
    cmd = PRESETS[preset][0]
    if bpr is None:
        return {'preset': preset, 'command': cmd, 'reply': 'not attempted (dry run)',
                'ack': False, 'attempts': []}
    attempts = []
    for i in range(1, SWITCH_ATTEMPTS + 1):
        raw = ask_first_byte(port, cmd, SWITCH_WINDOW_S)
        reply = bpr.describe(raw)
        attempts.append({'attempt': i, 'reply': reply, 'bytes': len(raw)})
        if reply.startswith('ACK'):
            return {'preset': preset, 'command': cmd, 'reply': reply, 'ack': True,
                    'attempts': attempts}
        if i < SWITCH_ATTEMPTS:
            print(f'    [{cmd}] {reply} on attempt {i}/{SWITCH_ATTEMPTS}; '
                  f'retrying the same command in {SWITCH_RETRY_GAP_S:.0f} s', flush=True)
            time.sleep(SWITCH_RETRY_GAP_S)
    return {'preset': preset, 'command': cmd, 'reply': attempts[-1]['reply'],
            'ack': False, 'attempts': attempts}


def patch_metadata(run_id: str, extra: dict) -> bool:
    """Add the batch fields to the round metadata the capture script already wrote."""
    path = ROOT / 'data' / 'raw' / 'development_20261101' / f'{run_id}.metadata.json'
    if not path.is_file():
        return False
    meta = json.loads(path.read_text(encoding='utf-8'))
    meta.update(extra)
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    return True


def capture_round(preset, attempt, tag, extra, block, dry_run=False):
    sbp, dbp, mapv, vol = PRESETS[preset][1:]
    log = ROOT / 'tmp' / 'omniprobe' / f'{tag}_p{preset}_a{attempt:03d}_{block}.out'
    if dry_run:
        print(f'  would capture preset {preset} ({sbp}/{dbp}, {vol} cc) -> {log.name}',
              flush=True)
        return {'attempt': attempt, 'outcome': 'dry_run', 'run_id': None}
    code, text = run([CAPTURE, '--confirm-nonhuman-fixture', '--confirm-current-panel',
                      '--panel-preset', preset, '--panel-pulse-volume-cc', vol,
                      '--target-mmhg', TARGET_MMHG, '--accept-rx-errors', '-1',
                      '--dataset-role', 'prospective_validation'], log)
    result = None
    for line in text.splitlines():
        if line.startswith('RESULT '):
            result = json.loads(line[7:])
    entry = {'attempt': attempt, 'exit_code': code, 'log': log.name}
    if not result or result.get('outcome') != 'export_received':
        entry.update(outcome=(result or {}).get('outcome', 'no result'), run_id=None)
        print(f'    attempt {attempt} FAILED {(result or {}).get("outcome")} '
              f'(see {log.name})', flush=True)
        return entry

    run_id = result['run_id']
    run([SPLIT, run_id])
    export = ROOT / 'data' / 'raw' / 'development_20261101' / f'{run_id}.export.ndjson'
    _, gate_text = run([GATE, export])
    usable = 'USABLE' in gate_text
    slope = next((line.split('peak_slope=')[1].split()[0]
                  for line in gate_text.splitlines() if 'peak_slope=' in line), '?')
    patched = patch_metadata(run_id, extra)
    entry.update(outcome='export_received', run_id=run_id, n=result.get('n'),
                 gate_usable=usable, peak_slope=slope, metadata_patched=patched)
    print(f'    capture {run_id}  n={result.get("n")}  '
          f'gate={"USABLE" if usable else "REJECTED"}  slope={slope} mmHg/s', flush=True)
    return entry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--day', type=int, required=True, help='1-based day index of the batch')
    ap.add_argument('--rounds', type=int, default=2, help='captures per preset per block')
    ap.add_argument('--port', default='COM12')
    ap.add_argument('--batch-tag', default='crosstday')
    ap.add_argument('--presets', default='1,2,3,4,5,6,7')
    ap.add_argument('--rewrap-wait-s', type=float, default=1800.0)
    ap.add_argument('--valve-result', type=Path, default=None,
                    help='tmp/omniprobe/daily_valve_<stamp>.result.json from the daily card')
    ap.add_argument('--daily-card', type=Path, default=None)
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    presets = [int(p) for p in str(args.presets).split(',') if p.strip()]
    for p in presets:
        if p not in PRESETS:
            raise SystemExit(f'unknown preset {p}')

    stamp = time.strftime('%Y%m%d-%H%M%S')
    tag = f'{args.batch_tag}_d{args.day:02d}_{stamp}'

    valve = None
    if args.valve_result and Path(args.valve_result).is_file():
        valve = json.loads(Path(args.valve_result).read_text(encoding='utf-8'))
    valve_point = (valve or {}).get('valve_working_point')
    daily_card = str(args.daily_card) if args.daily_card else None

    manifest = {'batch_tag': args.batch_tag, 'day': args.day, 'tag': tag,
                'panel_presets': presets, 'rounds_per_preset_per_block': args.rounds,
                'target_mmhg': TARGET_MMHG, 'started': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'valve_result_path': str(args.valve_result) if args.valve_result else None,
                'valve_working_point': valve_point, 'daily_card_path': daily_card,
                'rewrap': None, 'blocks': []}
    if MANIFEST.is_file():
        previous = json.loads(MANIFEST.read_text(encoding='utf-8'))
    else:
        previous = {'batch_tag': args.batch_tag, 'days': []}
    if any(d.get('day') == args.day for d in previous.get('days', [])):
        raise SystemExit(f'{MANIFEST} already records day {args.day}; '
                         f'pick a new day index instead of overwriting it')

    port = None
    bpr = None
    if not args.dry_run:
        import serial
        import bp_preset_remote as bpr  # noqa: F811  (import inside the live branch)
        port = serial.Serial(args.port, BAUD, bytesize=8, parity='N', stopbits=1,
                             timeout=0.3, write_timeout=1.0)
        print('opened %s at %d 8N1' % (args.port, BAUD), flush=True)
        print('  [BP_VERSION] ' + bpr.describe(bpr.command(port, 'BP_VERSION')), flush=True)
        print('  [CUFF_EXT]   ' + bpr.describe(bpr.command(port, 'CUFF_EXT')), flush=True)

    print(f'{tag}: day {args.day}, presets {presets}, {args.rounds} round(s) per preset '
          f'per block, target {TARGET_MMHG} mmHg', flush=True)
    print(f'  valve working point: {valve_point or "not supplied"}', flush=True)

    try:
        for block in ('A', 'B'):
            if block == 'B':
                result = wait_for_rewrap(args.day, block, args.rewrap_wait_s)
                manifest['rewrap'] = result
                if not result['confirmed']:
                    print('block B skipped: no rewrap confirmation (§4 rules 10/11)',
                          flush=True)
                    manifest['blocks'].append({'block': block, 'skipped': 'no rewrap marker'})
                    break
            block_entry = {'block': block, 'switches': [], 'slots': []}
            for preset in presets:
                switch = switch_preset(port, preset, bpr)
                block_entry['switches'].append(switch)
                print(f'  preset {preset}: [{switch["command"]}] {switch["reply"]}', flush=True)
                if not switch['ack'] and not args.dry_run:
                    print('  the Tester rejected the switch: stopping the day rather than '
                          'capturing under a panel label we cannot support', flush=True)
                    block_entry['stopped'] = 'preset switch not acknowledged'
                    manifest['blocks'].append(block_entry)
                    raise SystemExit(3)
                extra = {'batch_tag': args.batch_tag, 'batch_day': args.day,
                         'wrap_block': block, 'panel_state_established': switch['ack'],
                         'panel_switch_command': switch['command'],
                         'panel_switch_reply': switch['reply'],
                         'panel_switch_attempts': switch['attempts'],
                         'panel_switch_policy': {
                             'amendment': 'amend1_20261116',
                             'window_s': SWITCH_WINDOW_S,
                             'max_attempts': SWITCH_ATTEMPTS,
                             'retry_gap_s': SWITCH_RETRY_GAP_S},
                         'valve_working_point': valve_point,
                         'daily_card_path': daily_card,
                         'orchestrator_sha256': ORCHESTRATOR_SHA256,
                         'orchestrator_path': 'tools/crosstday_orchestrator.py'}
                good = 0
                attempt = 0
                while good < args.rounds and attempt < args.rounds * MAX_ATTEMPTS_FACTOR:
                    attempt += 1
                    entry = capture_round(preset, attempt, tag, extra, block, args.dry_run)
                    entry['preset'] = preset
                    block_entry['slots'].append(entry)
                    if entry.get('run_id'):
                        good += 1
                    if args.dry_run:
                        break          # one preview line per slot is enough
                if good < args.rounds and not args.dry_run:
                    print(f'  preset {preset}: only {good} of {args.rounds} round(s) kept',
                          flush=True)
            manifest['blocks'].append(block_entry)
    finally:
        if port is not None:
            try:
                port.close()
            except Exception:
                pass
        manifest['finished'] = time.strftime('%Y-%m-%dT%H:%M:%S')
        manifest['orchestrator_sha256'] = ORCHESTRATOR_SHA256
        kept = [s for b in manifest['blocks'] for s in b.get('slots', []) if s.get('run_id')]
        manifest['captures_kept'] = len(kept)
        if args.dry_run:
            print(f'\ndry run: {len(kept)} capture(s) would be recorded; nothing written',
                  flush=True)
            return 0
        previous.setdefault('days', []).append(manifest)
        previous['updated'] = manifest['finished']
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(previous, ensure_ascii=False, indent=2) + '\n',
                            encoding='utf-8')
        print(f'\n{len(kept)} capture(s) kept on day {args.day}', flush=True)
        print('WROTE', MANIFEST, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
