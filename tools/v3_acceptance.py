#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Score a batch of NEW captures with both frozen estimators and apply the v3 test.

The v3 candidate (`tools/reference_bp_v3.py`, a 3 s MAP median window) was registered in
`data/protocols/reference_bp_freeze_v3_candidate.md` together with four acceptance
criteria. Those criteria only mean anything if they are applied to rounds captured after
the registration, so this script refuses to run on the 62 rounds that already exist.

The refusal is not a formality. The 3 s window was chosen *because* it catches one of
those 62 rounds; scoring it again here would turn a selection set into a validation set
and every number produced would be circular. `--include-existing` exists only so the
original corpus can be reproduced in reports that say so explicitly; it never satisfies
the test and is rejected outright.

Both versions read the same decoded capture and differ in exactly one parameter, so any
difference in the table comes from that parameter and nothing else.

Usage:
    python tools/v3_acceptance.py --batch <dir> --panel-map <json>
    python tools/v3_acceptance.py --batch data/raw/prospective_v3 --json out.json

`--panel-map` is a JSON object of run_id -> panel MAP mmHg; without it the batch is
summarised without errors, since the acceptance criteria are defined on published counts
and dispersion rather than on agreement with the panel. Agreement is reported when known
and is never part of the pass/fail rule.

Eligibility is decided by the capture time inside the run_id against `REGISTERED_AT`, not
by which folder the file lives in: new rounds keep landing in
`data/raw/development_20261101/`, so a path-based rule rejects the very rounds the test
exists for.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import reference_bp as v2            # noqa: E402
import reference_bp_v3 as v3         # noqa: E402

EXISTING_GLOB = 'standard*_peakwindow_*.export.ndjson'

# The moment the four acceptance criteria were written down and committed
# (`5066fc5`, data/protocols/reference_bp_freeze_v3_candidate.md). Rounds captured before
# it belong to the corpus the window was chosen on; rounds after it are the test.
#
# The test used to be "is this file in data/raw", which looked equivalent and was not:
# every new round is written into the same development_20261101 folder, so the first real
# acceptance batch was rejected as "already scored". The run_id carries the capture time,
# so the comparison is made on that instead of on a path.
REGISTERED_AT = '2026-11-11T09:49:47'

CRITERIA = [
    ('published_not_worse_90pct',
     'MAP published rounds >= 0.9 x v2 published count on the same batch'),
    ('sd_lower_by_more_than_1',
     'MAP error sd strictly lower than v2 by more than 1.0 mmHg'),
    ('median_not_worse_by_1',
     'MAP median |error| not worse than v2 + 1.0 mmHg'),
    ('outliers_not_worse',
     'count of |error| > 20 mmHg not higher than v2'),
]


def preset_of(run_id):
    """Read the panel preset back out of a run_id, or None.

    The acquisition script names runs `standard<SBP>_<DBP:03d>_target<N>_peakwindow_<stamp>`,
    so `standard120_080` means 120/80 - the diastolic field is zero-padded to three digits
    while the systolic field is not.
    """
    head = str(run_id).split('_')
    if len(head) < 2 or not head[0].startswith('standard'):
        return None
    table = {'120_080': 1, '150_100': 2, '200_150': 3, '255_195': 4,
             '060_030': 5, '080_050': 6, '100_065': 7}
    sbp = head[0][len('standard'):]
    return table.get(f'{sbp}_{head[1]}')


def captured_at(run_id):
    """Pull the capture timestamp out of a run_id, or None when it cannot be read.

    run_id looks like `standard255_195_target275_peakwindow_20261111-101458`; the tail is
    `YYYYMMDD-HHMMSS` in local time, which is how every acquisition script names its runs.
    """
    tail = str(run_id).rsplit('_', 1)[-1]
    if '-' not in tail:
        return None
    day, clock = tail.split('-', 1)
    if len(day) != 8 or len(clock) != 6 or not (day + clock).isdigit():
        return None
    return f'{day[:4]}-{day[4:6]}-{day[6:]}T{clock[:2]}:{clock[2:4]}:{clock[4:]}'



def published(status, value):
    """A pressure counts as published only when the estimator did not refuse it.

    `reference_bp.estimate` still fills `map_mmhg` for a capture it marks
    `unresolved_map`; the number is present but explicitly disowned. Counting non-null
    values therefore reports every round as published and hides the refusals, which is
    the whole quantity this test is about. `unresolved_sbp` / `unresolved_dbp` are
    property-specific refusals and are handled by the caller.
    """
    return value is not None and not str(status).startswith('unresolved_map')


def score(path, module):
    capture = module.load(path)
    return module.estimate(capture)


def summarise(rows, key, version):
    """Summarise one version's answers.

    `rows` hold both versions side by side as `<key>_v2` / `<key>_v3`, so the version
    suffix is not optional: reading the bare `<key>_mmhg` silently returns None for
    every row and reports "0 published" while the captures are perfectly fine.
    """
    values = [r[f'{key}_{version}'] for r in rows]
    statuses = [r.get(f'{version}_status') for r in rows]
    ok = [published(s, v) for s, v in zip(statuses, values)]
    errors = [r[f'{key}_error_{version}'] for r, keep in zip(rows, ok)
              if keep and r.get(f'{key}_error_{version}') is not None]
    out = {
        'published': sum(1 for keep in ok if keep),
        'n': len(rows),
    }
    if errors:
        out['median_abs_error'] = round(statistics.median(abs(e) for e in errors), 3)
        out['mean_error'] = round(statistics.fmean(errors), 3)
        out['sd'] = round(statistics.stdev(errors), 3) if len(errors) > 1 else None
        out['worst_abs_error'] = round(max(abs(e) for e in errors), 3)
        out['over_10'] = sum(1 for e in errors if abs(e) > 10.0)
        out['over_20'] = sum(1 for e in errors if abs(e) > 20.0)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--batch', type=Path, required=True,
                        help='directory holding the new .export.ndjson captures')
    parser.add_argument('--panel-map', type=Path,
                        help='JSON object of run_id -> panel MAP mmHg')
    parser.add_argument('--json', type=Path, help='write the full result here')
    parser.add_argument('--include-existing', action='store_true',
                        help='allow the already-scored corpus; marks the test INVALID')
    args = parser.parse_args()

    if not args.batch.is_dir():
        raise SystemExit(f'not a directory: {args.batch}')

    existing = {p.name for p in (ROOT / 'data' / 'raw' / 'development_20261101').glob(EXISTING_GLOB)}
    for folder in (ROOT / 'data' / 'raw').glob('development_*'):
        existing |= {p.name for p in folder.glob(EXISTING_GLOB)}

    panel = {}
    if args.panel_map:
        panel = json.loads(args.panel_map.read_text(encoding='utf-8'))

    files = sorted(args.batch.glob('*.export.ndjson'))
    reused, undated = [], []
    for path in files:
        stamp = captured_at(path.name[:-len('.export.ndjson')])
        if stamp is None:
            undated.append((path.name, 'run_id carries no YYYYMMDD-HHMMSS timestamp'))
        elif stamp <= REGISTERED_AT:
            reused.append(path.name)
    if (reused or undated) and not args.include_existing:
        detail = '; '.join([f'{len(reused)} of {len(files)} captures predate the registration, '
                            f'for example {reused[0]}'] if reused else []) + \
                 ('; ' if reused and undated else '') + \
                 ('; '.join(f'{name}: {why}' for name, why in undated[:3]) if undated else '')
        raise SystemExit(
            f'{detail}. The v3 acceptance test may only run on rounds captured after '
            f'{REGISTERED_AT} (data/protocols/reference_bp_freeze_v3_candidate.md). Pass '
            '--include-existing only to reproduce the selection corpus, and report that run '
            'as INVALID for the test.')

    rows = []
    for path in files:
        run_id = path.name[:-len('.export.ndjson')]
        row = {'run_id': run_id, 'captured_at': captured_at(run_id), 'preset': preset_of(run_id)}
        try:
            a = score(path, v2)
            b = score(path, v3)
        except Exception as exc:                     # decode or estimator failure
            row.update(v2_status='error', v2_error_repr=repr(exc))
            rows.append(row)
            continue
        row['v2_status'] = a['status']
        row['v3_status'] = b['status']
        for key in ('map', 'sbp', 'dbp'):
            row[f'{key}_v2'] = a.get(f'{key}_mmhg')
            row[f'{key}_v3'] = b.get(f'{key}_mmhg')
            ref = panel.get(run_id)
            for version, answer in (('v2', a), ('v3', b)):
                value = answer.get(f'{key}_mmhg')
                if ref is not None and value is not None:
                    row[f'{key}_error_{version}'] = round(value - ref, 3)
        # Why a round was refused is part of the result: the v2 number exists either way,
        # and `unresolved_map` means the estimator disowned it.
        row['envelope_peak_raw_mv'] = a.get('envelope_peak_raw_mv')
        row['high_side_plateau_ratio'] = a.get('high_side_plateau_ratio')
        row['envelope_transient_suspected'] = a.get('envelope_transient_suspected')
        row['sbp_plateau_suspected'] = a.get('sbp_plateau_suspected')
        rows.append(row)

    result = {
        'batch': str(args.batch),
        'captures': len(rows),
        'registered_at': REGISTERED_AT,
        'selection_corpus_size': len(existing),
        'panel_map_supplied': bool(panel),
        'estimators': {'v2': 'tools/reference_bp.py (map_smoothing_s 2.0)',
                       'v3': 'tools/reference_bp_v3.py (map_smoothing_s 3.0)'},
        'invalid_for_acceptance_test': bool(reused or undated),
        'rows': rows,
    }
    result['summary'] = {'v2': summarise(rows, 'map', 'v2'),
                         'v3': summarise(rows, 'map', 'v3')}

    s2, s3 = result['summary']['v2'], result['summary']['v3']
    checks = {}
    if panel:
        checks['published_not_worse_90pct'] = s3['published'] >= 0.9 * s2['published']
        # The dispersion criteria are undefined when no round in the batch carries a
        # panel MAP; reporting that as FAIL would look like a real verdict.
        checks['sd_lower_by_more_than_1'] = (
            None if s2.get('sd') is None or s3.get('sd') is None
            else bool(s3['sd'] < s2['sd'] - 1.0))
        checks['median_not_worse_by_1'] = (
            None if s2.get('median_abs_error') is None or s3.get('median_abs_error') is None
            else bool(s3['median_abs_error'] <= s2['median_abs_error'] + 1.0))
        checks['outliers_not_worse'] = (
            None if s2.get('over_20') is None or s3.get('over_20') is None
            else bool(s3['over_20'] <= s2['over_20']))
    result['criteria'] = {name: {'met': checks.get(name), 'rule': text}
                          for name, text in CRITERIA}

    missing = [n for n, ok in checks.items() if ok is None]
    if not panel:
        verdict = 'NO PANEL REFERENCE - counts reported, pass/fail not evaluated'
    elif reused or undated:
        verdict = 'INVALID - the batch contains rounds from the selection corpus'
    elif missing:
        verdict = ('NOT EVALUABLE - the panel map has no entry for these run_ids, so '
                   + ', '.join(missing) + ' cannot be computed')
    elif all(checks.values()):
        verdict = 'v3 PASSES the pre-registered test on this batch'
    else:
        failed = [n for n, ok in checks.items() if not ok]
        verdict = 'v3 FAILS: ' + ', '.join(failed)
    result['verdict'] = verdict

    print(f"{len(rows)} captures from {args.batch}")
    print(f"v2: published {s2['published']}/{s2['n']}  "
          f"median|e| {s2.get('median_abs_error')}  sd {s2.get('sd')}  "
          f"worst {s2.get('worst_abs_error')}  >20 {s2.get('over_20')}")
    print(f"v3: published {s3['published']}/{s3['n']}  "
          f"median|e| {s3.get('median_abs_error')}  sd {s3.get('sd')}  "
          f"worst {s3.get('worst_abs_error')}  >20 {s3.get('over_20')}")
    for name, text in CRITERIA:
        met = checks.get(name)
        mark = 'n/a' if met is None else ('PASS' if met else 'FAIL')
        print(f'  {mark:4s} {name}: {text}')
    print(verdict)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
        print('WROTE', args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
