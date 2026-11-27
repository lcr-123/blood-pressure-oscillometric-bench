"""Attribute every failed cross-day slot from the round metadata, not from the logs.

Background: the frozen orchestrator named each attempt's log f'{tag}_p{preset}_a{n}.out'
without the block letter, so on any full day block B overwrote block A's logs. Eleven of
the 27 failed slots in the cross-day batch lost the only file that named their cause.

They are still attributable, because the capture script writes
data/raw/development_20261101/<run_id>.metadata.json itself, before the orchestrator gets a
chance to patch it. A failed round keeps `error` and `outcome='failed'`; it only loses
batch_tag / batch_day / wrap_block, because patch_metadata is skipped on the failure path.

This tool rebuilds the attribution by matching each failed manifest slot (day, block,
preset, attempt -- all recorded by the orchestrator) against failed metadata files whose
file-name stamp falls inside that day's window and whose panel_preset matches.

Usage
    python tools/attribute_failed_slots.py
    python tools/attribute_failed_slots.py --manifest tmp/omniprobe/crosstday_manifest.json --json out.json
"""
import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw' / 'development_20261101'
DEFAULT_MANIFEST = ROOT / 'tmp' / 'omniprobe' / 'crosstday_manifest.json'

# Buckets used in the reports. Longest first: the specific messages must win over the
# generic "device safety/offline event" prefix they are wrapped in.
BUCKETS = (
    ('Over-pressure', 'over-pressure: the 280 mmHg check fired before the target check'),
    ('profile peak could not be set', 'profile peak could not be set (a true zero outside -1..+1)'),
    ('stale/nonmonotonic', 'stale or non-monotonic pressure timestamp'),
    ('transport discontinuity', 'transport discontinuity (a bad byte or a failed sample)'),
    ('incomplete capture export', 'incomplete capture export'),
    ('not reached', 'target not reached in time'),
    ('baseline failed', 'unloaded zero baseline failed'),
    ('ACK', 'a command went unacknowledged'),
    ('raw signal', 'invalid calibration or extreme raw signal'),
)


def failure_text(meta):
    """The capture script records the abort in `error`, except on the export path.

    A round whose capture finished but whose export frame never completed ends in
    `export_error` instead -- day 2's `TimeoutError('incomplete capture export')` is the
    only such round in the batch, and without this fallback it looks unattributable.
    """
    return meta.get('error') or meta.get('export_error') or None


def bucket_of(error):
    if not error:
        return 'no error key in the metadata'
    for needle, label in BUCKETS:
        if needle in error:
            return label
    return 'other: ' + error.split('(')[0]


def parse_stamp(path):
    """<prefix>_<YYYYMMDD>-<HHMMSS>.metadata.json -> datetime."""
    stem = path.name[: -len('.metadata.json')]
    date, _, clock = stem.rpartition('_')[-1].partition('-')
    if len(date) != 8 or len(clock) != 6:
        return None
    try:
        return datetime.strptime(date + clock, '%Y%m%d%H%M%S')
    except ValueError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument('--json', type=Path, default=None)
    args = ap.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))

    windows = {}
    slots = []
    for day in manifest.get('days', []):
        start, finish = day.get('started'), day.get('finished')
        if start and finish:
            windows[day['day']] = (datetime.fromisoformat(start),
                                   datetime.fromisoformat(finish))
        for block in day.get('blocks', []):
            for slot in block.get('slots', []):
                if slot.get('outcome') == 'failed':
                    slots.append({'day': day['day'], 'block': block['block'],
                                  'preset': slot.get('preset'),
                                  'attempt': slot.get('attempt'),
                                  'log': slot.get('log')})

    candidates = []
    for path in RAW.glob('*.metadata.json'):
        try:
            meta = json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        if meta.get('outcome') != 'failed':
            continue
        stamp = parse_stamp(path)
        if stamp is None:
            continue
        candidates.append({'file': path.name, 'stamp': stamp,
                           'preset': meta.get('panel_preset'),
                           'error': failure_text(meta),
                           'closeout': meta.get('closeout_confirmed'),
                           'run_id': path.name[: -len('.metadata.json')]})
    candidates.sort(key=lambda c: c['stamp'])

    inside = [c for c in candidates
              if any(lo <= c['stamp'] <= hi for lo, hi in windows.values())]

    used = set()
    rows = []
    for slot in slots:
        window = windows.get(slot['day'])
        match = None
        if window is not None:
            lo, hi = window
            for cand in inside:
                if cand['file'] in used:
                    continue
                if cand['preset'] != slot['preset']:
                    continue
                if lo <= cand['stamp'] <= hi:
                    match = cand
                    break
        if match is not None:
            used.add(match['file'])
        rows.append({
            'day': slot['day'], 'block': slot['block'], 'preset': slot['preset'],
            'attempt': slot['attempt'], 'log': slot['log'],
            'time': match['stamp'].strftime('%Y-%m-%dT%H:%M:%S') if match else None,
            'run_id': match['run_id'] if match else None,
            'error': match['error'] if match else None,
            'cause': bucket_of(match['error']) if match else 'NOT ATTRIBUTED',
            'closeout_confirmed': match['closeout'] if match else None,
        })

    print(f'manifest                 {args.manifest}')
    print(f'failed slots             {len(slots)}')
    print(f'failed metadata on disk  {len(candidates)}')
    print(f'  inside a batch window  {len(inside)}')
    recovered = sum(1 for r in rows if r['run_id'])
    print(f'attributed               {recovered} / {len(slots)}')
    print()

    header = ('day', 'blk', 'p', 'a', 'time', 'cause')
    print('%-3s %-3s %-2s %-2s %-19s %s' % header)
    for row in rows:
        print('%-3d %-3s %-2s %-2s %-19s %s' % (
            row['day'], row['block'], row['preset'], row['attempt'],
            row['time'] or '-', row['cause']))

    print()
    counts = Counter(r['cause'] for r in rows)
    for cause, count in counts.most_common():
        print(f'  {count:>2}  {cause}')

    per_day = defaultdict(Counter)
    for row in rows:
        per_day[row['day']][row['cause']] += 1
    print()
    print('per day:')
    for day in sorted(per_day):
        items = ', '.join(f'{n}x {c.split(":")[0]}' for c, n in per_day[day].most_common())
        print(f'  day {day:>2}: {items}')

    leftover = [c for c in inside if c['file'] not in used]
    print()
    print(f'unattributed failed metadata inside windows: {len(leftover)}')
    for cand in leftover:
        print('  %s p%s %s' % (cand['stamp'].strftime('%m-%d %H:%M:%S'),
                               cand['preset'], (cand['error'] or '(no error key)')[:88]))

    if args.json:
        payload = {'manifest': str(args.manifest), 'failed_slots': len(slots),
                   'failed_metadata_on_disk': len(candidates),
                   'failed_metadata_in_windows': len(inside),
                   'attributed': recovered, 'slots': rows,
                   'causes': dict(counts),
                   'unattributed_metadata': [c['file'] for c in leftover]}
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode('utf-8') + b'\n'
        assert not data.startswith(b'\xef\xbb\xbf')
        args.json.write_bytes(data)
        print(f'\nWROTE {args.json} {len(data)} bytes')

    return 0 if recovered == len(slots) and not leftover else 1


if __name__ == '__main__':
    raise SystemExit(main())
