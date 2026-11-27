#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply the v5 pre-registered acceptance test to a batch of NEW captures.

The candidate is written down in `data/protocols/reference_bp_freeze_v5_candidate.md`:
one constant set, three envelope views, the per-quantity median of the views that publish,
two definitional offsets, and two reference-free plausibility gates. Its nine constants are
frozen there, and the five criteria C1-C5 are frozen there too. This script only applies
them.

Why eligibility is decided on the capture time
    The rule was designed after the author had seen all 222 existing rounds, so those rounds
    cannot testify for it. Every round captured before the registration commit belongs to
    the corpus the design looked at; only rounds captured after it are a test. New rounds
    keep landing in `data/raw/development_20261101/`, so a path cannot separate them and the
    timestamp inside the run_id is used instead - the same reasoning (and the same failure)
    that `tools/v3_acceptance.py` records.

What each criterion uses, and why the denominators differ
    C1, C5   every v5-published round in the batch.
    C2, C3   the intersection of the rounds v5 publishes and the rounds frozen v2 publishes.
             Scoring each on its own denominator would let a candidate win by refusing more
             rounds, which is exactly the mistake that got v3 rejected.
    C4       every round that survives the exclusion rules; a refusal counts as a refusal,
             not as a missing round.

    The batch itself is whatever survives the exclusion rules in §4: a round whose export the
    strict decoder rejects, or which the v2 validity gate calls unusable, is not part of the
    batch at all. §4 rule 6 keeps v5's own refusals in the batch, because a refusal is a real
    outcome of the candidate rather than a defect of the capture.

Usage
    python tools/v5_acceptance.py                        # batch = everything after registration
    python tools/v5_acceptance.py --list                 # just show what would be scored
    python tools/v5_acceptance.py --json data/reports/v5_validation_20261114.json

This tool never changes the frozen estimator and never writes to a capture.
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import covered_bp                     # noqa: E402
import reference_bp                   # noqa: E402
import validity_v2                    # noqa: E402

# The moment the criteria and the nine constants were committed as `7b0a04d`
# (data/protocols/reference_bp_freeze_v5_candidate.md, 2026-11-13T21:09:53+08:00).
# Rounds captured before it are the design corpus; rounds after it are the test.
REGISTERED_AT = '2026-11-13T21:09:53'

# §5 of the protocol pins this image: one batch is one firmware generation, so a round from
# any other build is excluded no matter when it was captured.
PUBLISHED_FIRMWARE_HEX = '61ca1da309439d9a4afa7f783aacbb56be56e4607cc09289a3729eb2e39f74ad'
PUBLISHED_FIRMWARE_BYTES = 184146

# The batch closed when its verdict was committed as `d7db003`
# (data/reports/v5_validation_20261114.md, 2026-11-14T15:21:46+08:00). A pre-registered test
# is scored once: a round captured after the verdict was recorded belongs to a future batch,
# and letting it drift into this one would move a published number without a new protocol.
BATCH_CLOSED_AT = '2026-11-14T15:21:46'

FIELDS = ('map_mmhg', 'sbp_mmhg', 'dbp_mmhg')
NAMES = {'map_mmhg': 'MAP', 'sbp_mmhg': 'SBP', 'dbp_mmhg': 'DBP'}

# Frozen in §2 of the protocol. Repeated here so a silent edit to the module shows up as a
# mismatch instead of quietly changing what was validated.
FROZEN_CONSTANTS = {
    'FS_HZ': 40.0,
    'BAND_HZ': (1.0, 2.0),
    'SMOOTH_S': 2.0,
    'MIN_VIEWS': 2,
    'PULSE_PRESSURE_FRACTION': 0.15,
    'NOTE_GAP_MMHG': 10.0,
    'MAP_OFFSET_MMHG': -5.31,
    'DBP_OFFSET_MMHG': -1.16,
    'SBP_OFFSET_MMHG': 0.0,
}

SD_LIMIT = 8.0            # C1
MEAN_LIMIT = 5.0          # C1
SD_GAIN_REQUIRED = 1.0    # C2
MEAN_TOLERANCE = 1.0      # C3
PUBLISH_RATE_FLOOR = 0.80  # C4
SILENT_LIMIT = 20.0       # C5

CRITERIA = [
    ('C1_accuracy', f'pooled sd <= {SD_LIMIT} and |mean| <= {MEAN_LIMIT} for MAP/SBP/DBP'),
    ('C2_sd_lower_than_v2', f'each sd lower than frozen v2 by >= {SD_GAIN_REQUIRED} mmHg '
                            f'on the rounds both publish'),
    ('C3_mean_not_worse', f'each |mean| no worse than frozen v2 by more than {MEAN_TOLERANCE} '
                          f'mmHg on the rounds both publish'),
    ('C4_publish_rate', f'published share of the batch >= {PUBLISH_RATE_FLOOR}'),
    ('C5_no_silent_blunder', f'no published round with any |error| > {SILENT_LIMIT} mmHg'),
]


def captured_at(run_id):
    """Pull the capture timestamp out of a run_id, or None when it cannot be read."""
    tail = str(run_id).rsplit('_', 1)[-1]
    if '-' not in tail:
        return None
    day, clock = tail.split('-', 1)
    if len(day) != 8 or len(clock) != 6 or not (day + clock).isdigit():
        return None
    return f'{day[:4]}-{day[4:6]}-{day[6:]}T{clock[:2]}:{clock[2:4]}:{clock[4:]}'


def constants_mismatch():
    """List every frozen constant whose shipped value differs from the protocol."""
    bad = []
    for name, expected in FROZEN_CONSTANTS.items():
        actual = getattr(covered_bp, name, '<missing>')
        if isinstance(expected, tuple):
            same = isinstance(actual, tuple) and tuple(actual) == expected
        else:
            same = actual == expected
        if not same:
            bad.append((name, expected, actual))
    return bad


def stats(errors):
    if not errors:
        return None
    sd = statistics.stdev(errors) if len(errors) > 1 else 0.0
    mean = statistics.fmean(errors)
    return {'n': len(errors), 'mean': mean, 'sd': sd,
            'aami_pass': abs(mean) <= MEAN_LIMIT and sd <= SD_LIMIT}


def batch_exports(pattern):
    """Every export captured after registration, split by whether it survives exclusion.

    A batch is one firmware generation. §5 of the protocol pins the image to
    `61ca1da3...`, so a round produced by any other build is not a round of this test even
    when it lands after the registration timestamp. Nothing enforced that until 2026-11-14
    evening, when two experimental builds were flashed and reverted; without this check the
    batch quietly absorbed six rounds from a build that no longer exists.
    """
    kept, excluded = [], []
    for path in sorted(glob.glob(pattern)):
        run_id = Path(path).name[:-len('.export.ndjson')]
        stamp = captured_at(run_id)
        if stamp is None or stamp <= REGISTERED_AT:
            continue                                  # design corpus, not the test
        if stamp > BATCH_CLOSED_AT:
            excluded.append({'run_id': run_id, 'captured_at': stamp,
                             'preset': covered_bp.preset_of(run_id),
                             'why': f'captured {stamp} after the batch closed at '
                                    f'{BATCH_CLOSED_AT}; it belongs to a future batch'})
            continue
        firmware = firmware_of(run_id)
        if firmware is not None and firmware != PUBLISHED_FIRMWARE_HEX:
            excluded.append({'run_id': run_id, 'captured_at': stamp,
                             'preset': covered_bp.preset_of(run_id),
                             'why': f'captured on firmware {firmware[:16]}..., not the '
                                    f'image §5 pins ({PUBLISHED_FIRMWARE_HEX[:16]}...)'})
            continue
        gate = validity_v2.check(path)
        preset = covered_bp.preset_of(run_id)
        if not gate['usable'] or preset not in covered_bp.PANEL:
            excluded.append({'run_id': run_id, 'captured_at': stamp, 'preset': preset,
                             'why': gate.get('reasons') or 'preset not recognised'})
            continue
        kept.append({'run_id': run_id, 'captured_at': stamp, 'preset': preset,
                     'path': path,
                     'peak_window_slope_mmhg_s': gate.get('peak_window_slope_mmhg_s')})
    return kept, excluded


def firmware_of(run_id):
    """The firmware hash a round records, or None when its metadata does not say."""
    path = covered_bp.RAW / f'{run_id}.metadata.json'
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8')).get('firmware_hex_sha256')
    except json.JSONDecodeError:
        return None


def evaluate(rows):
    """Score the batch and apply C1-C5. `rows` are the rounds that survive exclusion."""
    v5_pool = {field: [] for field in FIELDS}
    v2_pool = {field: [] for field in FIELDS}
    v5_both = {field: [] for field in FIELDS}
    v2_both = {field: [] for field in FIELDS}
    per_preset = {}
    silent = []
    v5_status_counts = {}
    v2_status_counts = {}
    published = 0

    for row in rows:
        preset = row['preset']
        sbp, dbp, mapv = covered_bp.PANEL[preset]
        panel = {'map_mmhg': mapv, 'sbp_mmhg': sbp, 'dbp_mmhg': dbp}
        detail = covered_bp.covered_estimate(row['path'])
        incumbent = reference_bp.estimate(reference_bp.load(row['path']))
        row['v5_status'] = detail['status']
        row['v2_status'] = incumbent['status']
        v5_status_counts[detail['status']] = v5_status_counts.get(detail['status'], 0) + 1
        v2_status_counts[incumbent['status']] = v2_status_counts.get(incumbent['status'], 0) + 1
        if detail['status'] == 'ok':
            row['v5'] = {field: detail[field] for field in FIELDS}
            row['v5_error'] = {field: detail[field] - panel[field] for field in FIELDS}
            published += 1
            for field in FIELDS:
                v5_pool[field].append(row['v5_error'][field])
            worst = max(abs(v) for v in row['v5_error'].values())
            row['v5_worst_abs_error'] = worst
            if worst > SILENT_LIMIT:
                silent.append(row['run_id'])
        if incumbent['status'] == 'ok':
            row['v2'] = {field: incumbent[field] for field in FIELDS}
            row['v2_error'] = {field: incumbent[field] - panel[field] for field in FIELDS}
            for field in FIELDS:
                v2_pool[field].append(row['v2_error'][field])
        if row.get('v5') and row.get('v2'):
            for field in FIELDS:
                v5_both[field].append(row['v5_error'][field])
                v2_both[field].append(row['v2_error'][field])
        bucket = per_preset.setdefault(preset, {'exports': 0, 'published': 0,
                                                'errors': {f: [] for f in FIELDS}})
        bucket['exports'] += 1
        if row.get('v5'):
            bucket['published'] += 1
            for field in FIELDS:
                bucket['errors'][field].append(row['v5_error'][field])

    intersection = sum(1 for row in rows if row.get('v5') and row.get('v2'))
    return {'v5_pooled': {field: stats(v5_pool[field]) for field in FIELDS},
            'v2_pooled': {field: stats(v2_pool[field]) for field in FIELDS},
            'v2_status_counts': dict(sorted(v2_status_counts.items())),
            'v5_status_counts': dict(sorted(v5_status_counts.items())),
            'v5_intersection': {field: stats(v5_both[field]) for field in FIELDS},
            'v2_intersection': {field: stats(v2_both[field]) for field in FIELDS},
            'intersection': intersection,
            'per_preset': {str(p): {'exports': b['exports'], 'published': b['published'],
                                    **{field: stats(b['errors'][field]) for field in FIELDS}}
                           for p, b in sorted(per_preset.items())},
            'published': published,
            'batch': len(rows),
            'silent': silent}


def verdict(result):
    checks = {}
    pooled = result['v5_pooled']
    checks['C1_accuracy'] = all(
        pooled[field] is not None and pooled[field]['aami_pass'] for field in FIELDS)
    sd2 = result['v2_intersection']
    sd5 = result['v5_intersection']
    checks['C2_sd_lower_than_v2'] = all(
        sd2[field] is not None and sd5[field] is not None
        and sd5[field]['sd'] <= sd2[field]['sd'] - SD_GAIN_REQUIRED for field in FIELDS)
    checks['C3_mean_not_worse'] = all(
        sd2[field] is not None and sd5[field] is not None
        and abs(sd5[field]['mean']) <= abs(sd2[field]['mean']) + MEAN_TOLERANCE
        for field in FIELDS)
    checks['C4_publish_rate'] = (
        result['batch'] > 0
        and result['published'] / result['batch'] >= PUBLISH_RATE_FLOOR)
    checks['C5_no_silent_blunder'] = len(result['silent']) == 0
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--pattern', default=str(covered_bp.RAW / 'standard*_target275*.export.ndjson'))
    parser.add_argument('--json', type=Path, help='write the full result here')
    parser.add_argument('--list', action='store_true', help='only list the batch')
    args = parser.parse_args()

    mismatch = constants_mismatch()
    if mismatch:
        print('REFUSING TO SCORE: shipped constants differ from the pre-registered ones')
        for name, expected, actual in mismatch:
            print(f'  {name}: protocol {expected!r} vs shipped {actual!r}')
        return 2

    rows, excluded = batch_exports(args.pattern)
    print(f'registration {REGISTERED_AT}; batch {len(rows)} round(s), '
          f'{len(excluded)} excluded by §4 rules 1-5')
    for item in excluded:
        print(f'  excluded {item["run_id"]}  {item["why"]}')
    if args.list:
        for row in rows:
            print(f'  {row["run_id"]}  preset {row["preset"]}')
        return 0
    if not rows:
        print('nothing to score: no capture after the registration timestamp')
        return 1

    result = evaluate(rows)
    checks = verdict(result)
    result['criteria'] = {name: {'met': checks[name], 'rule': text}
                          for name, text in CRITERIA}
    failed = [name for name, ok in checks.items() if not ok]
    result['verdict'] = ('v5 PASSES the pre-registered test on this batch' if not failed
                         else 'v5 FAILS: ' + ', '.join(failed))
    result['registered_at'] = REGISTERED_AT
    result['frozen_constants'] = {k: list(v) if isinstance(v, tuple) else v
                                  for k, v in FROZEN_CONSTANTS.items()}
    result['excluded'] = excluded
    result['rows'] = rows

    print(f'\nbatch {result["batch"]} round(s); v5 published {result["published"]}; '
          f'both published {result["intersection"]}; silent>20 {len(result["silent"])}')
    print('\nC1 pooled (v5, every published round)')
    for field in FIELDS:
        s = result['v5_pooled'][field]
        print(f'  {NAMES[field]:<4} ' + ('n/a' if s is None else
              f'n={s["n"]:>3} mean {s["mean"]:+6.2f} sd {s["sd"]:5.2f} '
              f'{"PASS" if s["aami_pass"] else "fail"}'))
    print('\nC2/C3 on the intersection (frozen v2 -> v5)')
    for field in FIELDS:
        a = result['v2_intersection'][field]
        b = result['v5_intersection'][field]
        if a is None or b is None:
            print(f'  {NAMES[field]:<4} n/a')
            continue
        print(f'  {NAMES[field]:<4} n={b["n"]:>3} mean {a["mean"]:+6.2f} -> {b["mean"]:+6.2f}  '
              f'sd {a["sd"]:5.2f} -> {b["sd"]:5.2f}')
    print('\nper preset (v5)')
    for preset, entry in result['per_preset'].items():
        cells = '  '.join(
            f'{NAMES[field][:3]} ' + ('  n/a  ' if entry[field] is None else
                                      f'{entry[field]["mean"]:+6.2f}/{entry[field]["sd"]:5.2f} '
                                      f'{"P" if entry[field]["aami_pass"] else "f"}')
            for field in FIELDS)
        print(f'  P{preset} {entry["published"]:>3}/{entry["exports"]:<3} {cells}')
    print()
    for name, text in CRITERIA:
        print(f'  {"PASS" if checks[name] else "FAIL":4s} {name}: {text}')
    print(result['verdict'])
    if result['silent']:
        print(f'silent rounds: {result["silent"]}')

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n',
                             encoding='utf-8')
        print('WROTE', args.json)
    return 0 if not failed else 3


if __name__ == '__main__':
    sys.exit(main())
