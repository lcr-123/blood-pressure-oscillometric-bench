#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Score the estimator against the published accuracy criteria.

Two questions get confused constantly:

  * Does the algorithm *meet the accuracy criteria*? AAMI/ANSI/ISO 81060-2 clause 5.2.4
    asks the mean of the paired differences to be within +-5 mmHg and their standard
    deviation within 8 mmHg. That is arithmetic on whatever data you have.
  * Has the device been *clinically validated*? ISO 81060-2 asks for at least 85 subjects,
    three paired measurements each, trained observers, a defined subject selection and a
    reference sphygmomanometer. That is an experiment on people, and this rig forbids one.

This tool answers only the first, and prints the British Hypertension Society grading bands
alongside so the numbers can be read the way cuff monitors are usually advertised ("BHS A").

Rounds whose metadata records a firmware image other than the published one are excluded:
one corpus is one firmware generation, and a round from a different build cannot be pooled
with it (see `data/reports/deflate_loop_limit_cycle_20261114.md` §6).

Usage
    python tools/standard_conformance.py
    python tools/standard_conformance.py --json data/reports/covered_algorithm_20261114.json \
        --out data/reports/standard_conformance_20261114.json

`--source` reads a scorer output (`tools/covered_bp.py --score --json ...`); `--out` writes
this tool's own result. Neither file is modified in place.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import covered_bp                     # noqa: E402

RAW = ROOT / 'data' / 'raw' / 'development_20261101'
DEFAULT_SOURCE = ROOT / 'data' / 'reports' / 'covered_algorithm_20261114.json'

# The image the corpus was captured on. Rounds labelled with anything else are a different
# firmware generation and are excluded rather than pooled.
PUBLISHED_FIRMWARE_HEX = '61ca1da309439d9a4afa7f783aacbb56be56e4607cc09289a3729eb2e39f74ad'

FIELDS = (('map_mmhg', 'MAP'), ('sbp_mmhg', 'SBP'), ('dbp_mmhg', 'DBP'))

# AAMI/ANSI/ISO 81060-2:2018 clause 5.2.4 limits on the mean and sd of the paired
# differences. The standard covers systolic and diastolic; MAP is not part of it, but
# papers usually apply the same limits.
MEAN_LIMIT = 5.0
SD_LIMIT = 8.0

# British Hypertension Society protocol: share of paired readings within 5, 10 and 15 mmHg.
# Grade A needs >=60/85/95 %, B >=50/75/90 %, C >=40/65/85 %; below that is D.
BHS_BANDS = (5.0, 10.0, 15.0)
BHS_GRADES = (
    ('A', (60.0, 85.0, 95.0)),
    ('B', (50.0, 75.0, 90.0)),
    ('C', (40.0, 65.0, 85.0)),
)


def firmware_of(run_id):
    """The firmware hash recorded for a round, or None when its metadata does not say."""
    path = RAW / f'{run_id}.metadata.json'
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8')).get('firmware_hex_sha256')
    except json.JSONDecodeError:
        return None


def bhs_grade(shares):
    for name, limits in BHS_GRADES:
        if all(share >= limit for share, limit in zip(shares, limits)):
            return name
    return 'D'


def describe(errors):
    """mean / sd / BHS shares for one quantity."""
    n = len(errors)
    mean = statistics.fmean(errors)
    sd = statistics.stdev(errors) if n > 1 else 0.0
    absolute = [abs(value) for value in errors]
    shares = [100.0 * sum(1 for value in absolute if value <= limit) / n
              for limit in BHS_BANDS]
    failed = [name for name, limit, value in (('mean', MEAN_LIMIT, abs(mean)),
                                              ('sd', SD_LIMIT, sd))
              if value > limit]
    return {'n': n, 'mean': mean, 'sd': sd,
            'within_5_10_15_percent': shares,
            'bhs_grade': bhs_grade(shares),
            'failed': failed,
            'aami_pass': not failed}


def print_block(label, errors, indent='  '):
    if not errors:
        return
    entry = describe(errors)
    shares = entry['within_5_10_15_percent']
    mark = 'PASS' if entry['aami_pass'] else 'FAIL ' + ','.join(entry['failed'])
    print(f'{indent}{label:22s} n={entry["n"]:3d}  mean {entry["mean"]:+6.2f}  '
          f'sd {entry["sd"]:5.2f}  within 5/10/15: '
          f'{shares[0]:5.1f}/{shares[1]:5.1f}/{shares[2]:5.1f}%  '
          f'BHS {entry["bhs_grade"]}  {mark}')


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE,
                        help='output of tools/covered_bp.py --score --json')
    parser.add_argument('--out', type=Path, help='write this result as JSON')
    args = parser.parse_args()

    payload = json.loads(args.source.read_text(encoding='utf-8'))
    kept, dropped = [], []
    for row in payload['rows']:
        if row['status'] != 'ok':
            continue                          # a refusal is not an estimate to score
        firmware = firmware_of(row['run_id'])
        if firmware is not None and firmware != PUBLISHED_FIRMWARE_HEX:
            dropped.append({'run_id': row['run_id'], 'firmware': firmware})
            continue
        kept.append(row)

    try:
        source_label = str(args.source.resolve().relative_to(ROOT)).replace('\\', '/')
    except ValueError:
        source_label = str(args.source)
    result = {'source': source_label,
              'firmware_pinned': PUBLISHED_FIRMWARE_HEX,
              'rounds_kept': len(kept),
              'rounds_dropped_for_firmware': len(dropped),
              'dropped': dropped,
              'limits': {'mean_mmhg': MEAN_LIMIT, 'sd_mmhg': SD_LIMIT,
                         'bhs_bands_mmhg': list(BHS_BANDS)},
              'pooled': {}, 'per_preset': {}}

    print(f'  source {result["source"]}')
    print(f'  published rounds kept {len(kept)}; dropped for firmware mismatch '
          f'{len(dropped)}')
    for item in dropped:
        print(f'    dropped {item["run_id"]}  firmware {item["firmware"][:16]}...')

    print('\n  pooled')
    for key, label in FIELDS:
        errors = [row['error_mmhg'][key] for row in kept]
        result['pooled'][key] = describe(errors)
        print_block(label, errors)

    print('\n  per preset')
    presets = {}
    for preset in sorted({row['preset'] for row in kept}):
        subset = [row for row in kept if row['preset'] == preset]
        entry = {'rounds': len(subset)}
        print(f'  preset {preset}  ({len(subset)} round(s))')
        for key, label in FIELDS:
            errors = [row['error_mmhg'][key] for row in subset]
            entry[key] = describe(errors)
            print_block(label, errors)
        presets[str(preset)] = entry
    result['per_preset'] = presets

    passing = [name for name, entry in presets.items()
               if all(entry[key]['aami_pass'] for key, _ in FIELDS)]
    result['presets_passing_all_three'] = passing
    print(f'\n  presets passing all three quantities: {len(passing)}/{len(presets)} '
          f'{sorted(passing, key=int)}')

    print('\n  what the criteria mean')
    print(f'    AAMI/ISO 81060-2 accuracy limits: |mean| <= {MEAN_LIMIT:.1f} mmHg and '
          f'sd <= {SD_LIMIT:.1f} mmHg')
    print('    ISO 81060-2 clinical procedure: >=85 subjects, >=3 paired measurements '
          'each, trained')
    print('      observers with a reference sphygmomanometer; a bench simulator cannot '
          'stand in')
    print('    BHS bands: A >=60/85/95%, B >=50/75/90%, C >=40/65/85% within 5/10/15 mmHg')

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, ensure_ascii=False, indent=1) + '\n',
                            encoding='utf-8')
        print('WROTE', args.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
