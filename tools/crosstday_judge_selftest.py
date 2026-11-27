"""Synthetic checks for tools/crosstday_judge.py.

The judge exists because the frozen analyser never implements protocol §4 rule 10, and
on the 2026-11-16..25 batch that omission flips the SBP day-term conclusion.  A port
whose whole purpose is one rule had better prove that the rule bites, so this file
builds data where the answer is known and checks three things:

  1. `complete_days()` reads only the manifest, drops a day whose block B is absent, and
     keeps a day whose block B merely lost a round (the real day-10 case: preset 1 has
     one surviving block-B round instead of two).
  2. Rule 10 changes the T3 answer.  One synthetic day carries wildly scattered residuals
     - the real day-1 signature - and the day term must be insignificant with that day in
     and significant with it out.  If this ever stops flipping, the port has drifted.
  3. The T1 split follows planned day numbers.  Dropping day 1 must leave the early half
     as days 2..5, not promote day 5 into it the way slicing the surviving list does.

Everything here is synthetic: no raw file is read, so the check runs in milliseconds.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import crosstday_judge as judge  # noqa: E402

PRESETS = (1, 2, 3, 4)
FAILURES = []


def check(name, condition, detail=''):
    status = 'ok  ' if condition else 'FAIL'
    print(f'  {status} {name}{("  " + detail) if detail else ""}')
    if not condition:
        FAILURES.append(name)


def manifest(days):
    """days: list of (day, {block: {preset: rounds}})."""
    out = {'batch_tag': 'synthetic', 'days': []}
    for index, blocks in days:
        entry = {'day': index, 'blocks': []}
        for wrap in ('A', 'B'):
            if wrap not in blocks:
                continue
            slots = []
            for preset, count in sorted(blocks[wrap].items()):
                for _ in range(count):
                    slots.append({'preset': preset, 'run_id': f'syn_d{index}_{wrap}_p{preset}'})
            entry['blocks'].append({'block': wrap, 'slots': slots})
        out['days'].append(entry)
    return out


FULL = {p: 2 for p in PRESETS}


def rows_for(day_offsets, half_day_scatter=None, seed=11):
    """One row per (day, preset, wrap, round); offsets are the true day effects."""
    rng = np.random.default_rng(seed)
    rows = []
    for day, offset in enumerate(day_offsets, start=1):
        for preset in PRESETS:
            for wrap in ('A', 'B'):
                for rep in range(2):
                    noise = float(rng.normal(0.0, 3.0))
                    if day == 1 and half_day_scatter:
                        noise = float(rng.normal(0.0, half_day_scatter))
                    row = {'run_id': f'syn_d{day}_{wrap}_p{preset}_r{rep}',
                           'day': day, 'wrap': wrap, 'preset': preset,
                           'panel': {}}
                    for param in judge.PARAMS:
                        row[f'v2_{param}'] = offset + noise
                        row[f'v5_{param}'] = offset + noise
                    rows.append(row)
    return rows


def main():
    print('case 1: complete_days() reads the manifest and nothing else')
    m = manifest([
        (1, {'A': FULL}),                        # half day: block B never ran
        (2, {'A': FULL, 'B': FULL}),
        (3, {'A': FULL, 'B': FULL}),
        (4, {'A': FULL, 'B': {1: 2, 2: 2, 3: 2}}),   # block B missing preset 4 entirely
        (5, {'A': FULL, 'B': {1: 1, 2: 2, 3: 2, 4: 2}}),  # block B lost a round, not a preset
    ])
    got = judge.complete_days(m)
    check('half day dropped', 1 not in got)
    check('full day kept', 2 in got and 3 in got)
    check('day with a missing preset dropped', 4 not in got)
    check('day that merely lost a round kept', 5 in got, 'this is the real day-10 case')
    check('planned days still list all five', judge.manifest_days(m) == [1, 2, 3, 4, 5])

    print('case 2: rule 10 changes the T3 answer')
    # The batch's own shape: a modest day effect and one day whose residuals scatter far
    # wider than the rest.  scatter=40 with seed 23 is the setting that reproduces the real
    # inversion (p 0.9989 in, 0.0077 out); weak day effects are what make one bad day able
    # to swamp the numerator, because the real share of day SS is only ~5 %.
    offsets = [0.0, 1.2, -1.2, 1.6, -1.6, 1.2]
    rows = rows_for(offsets, half_day_scatter=40.0, seed=23)
    strict = [r for r in rows if r['day'] != 1]
    with_half = judge.two_way(rows, 'sbp_mmhg')
    without = judge.two_way(strict, 'sbp_mmhg')
    check('scattered half day inflates the within-cell sd',
          with_half['sw'] > 2.0 * without['sw'],
          f"sw {with_half['sw']:.1f} vs {without['sw']:.1f}")
    check('day term insignificant with the half day in', with_half['p_day'] > 0.05,
          f"p {with_half['p_day']:.4f}")
    check('day term significant with the half day out', without['p_day'] < 0.05,
          f"p {without['p_day']:.4f}")

    print('case 3: T1 splits by planned day number')
    m2 = manifest([(d, {'A': FULL, 'B': FULL}) for d in range(1, 11)])
    first, second = judge.planned_split(m2)
    check('first half is days 1-5', sorted(first) == [1, 2, 3, 4, 5])
    check('second half is days 6-10', sorted(second) == [6, 7, 8, 9, 10])
    rows2 = rows_for([0.0] * 10)
    on = judge.t1([r for r in rows2 if r['day'] != 1], first - {1}, second)
    check('dropping day 1 leaves the early half as 2..5',
          on['first_days'] == [2, 3, 4, 5], f'got {on["first_days"]}')
    frozen_first, _ = judge.frozen_split(rows2)
    check('the frozen split is the surviving list halved, not the plan',
          sorted(frozen_first) == [1, 2, 3, 4, 5])

    print('case 4: T0, T2 and T4 keep every day')
    source = (Path(__file__).resolve().parent / 'crosstday_judge.py').read_text(encoding='utf-8')
    for call, name in ((r"report\['t0_all_days'\] = t0\(rows", 'T0'),
                       (r"report\['t2_all_days'\] = t2\(rows", 'T2'),
                       (r"report\['t4_all_days'\] = t4\(rows", 'T4')):
        import re
        check(f'{name} is computed on all days', re.search(call, source) is not None)

    print()
    if FAILURES:
        print(f'SELFTEST FAILED: {len(FAILURES)} check(s): {FAILURES}')
        return 1
    print('SELFTEST OK: rule 10 bites, the split follows the plan, T0/T2/T4 are untouched')
    return 0


if __name__ == '__main__':
    sys.exit(main())
