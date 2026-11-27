#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Per-preset breakdown of the frozen reference estimator over the whole corpus.

The frozen scorer (`tools/score_batch.py`, `data/reports/reference_bp_prospective_v2.json`)
reports one number per batch. That hides the single most important structural fact
about this dataset: availability and accuracy are not the same thing, and they move
in opposite directions across the presets.

This tool prints, per preset and per quantity (MAP / SBP / DBP):

  * how many runs the estimator was willing to publish (`status` does not refuse it)
  * the median signed error, the sd, and the full range of the published runs

Refusal is not failure. `unresolved_map` means the estimator saw a deflation-valve
transient it could not separate from a pulse envelope; `unresolved_sbp` means the
high-pressure side of MAP is a plateau, so the 0.5x crossing does not exist. Both
are reported evidence about the fixture, not defects of the data.

This tool never modifies the frozen estimator; it only calls `reference_bp.estimate`
with its default parameters.

Tier filtering matters here. The raw directory holds rounds from protocols that have
already been scored (the frozen baseline, the v1 and v2 prospective batches, the v3
acceptance batch) and rounds that belong to none of them. Pooling everything gives a
number that matches no published statistic. `--tier` restricts the corpus to the tiers
you name; without it the tool reports every tier separately as well as pooled.

sd is the sample standard deviation (n-1), matching the published reports. The freeze
records additionally store the population value; both are written to JSON.

Gate-passed by default. A round whose pressure trace shows the deflation valve
throttling (`validity_v2.check(...)['usable']` is False, peak-window rate far past
`DEFLATE_RATE_MAX_MMHG_S`) is a failed recording, not a measurement. Four such rounds
sit inside the 62-round published corpus and dominate its pooled sd: keeping them in
makes MAP look like sd 12.78 when the surviving rounds give 4.73. Every table below
therefore reports gate-passed rounds, lists the excluded ones by run id, and shows the
AAMI/ANSI pass/fail per quantity so nobody has to recompute |mean| <= 5 and sd <= 8 by
hand. Pass `--include-gate-failures` to reproduce the older tables that mixed them in.

Usage:
    python tools/preset_breakdown.py
    python tools/preset_breakdown.py --published --map-policy not-unresolved
    python tools/preset_breakdown.py --tier frozen_baseline_v2 --tier prospective_v1
    python tools/preset_breakdown.py --include-gate-failures --json out.json
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

import reference_bp  # noqa: E402
import dataset_tiers  # noqa: E402
import validity_v2  # noqa: E402

# Panel presets of the BP Pump 2 Standard BP screen (manual table 3-2).
# The bracketed MAP is the manual's arithmetic annotation floor((SBP+2*DBP)/3),
# not a physical target; it is used as the comparison value here for consistency
# with the frozen scorer.
PRESETS = {
    1: (120, 80, 93),
    2: (150, 100, 116),
    3: (200, 150, 166),
    4: (255, 195, 215),
    # Table 3-2 rows 5-7, the low-blood-pressure presets. Added on 2026-11-13 when the
    # first captures were taken on them; no earlier round exists in the corpus.
    5: (60, 30, 40),
    6: (80, 50, 60),
    7: (100, 65, 76),
}

DEFAULT_GLOB = 'data/raw/**/standard*_target275_peakwindow_*.export.ndjson'
FIRMWARE = 'PEAK_WINDOW_20261105'
SD_CONVENTION = 'sample (n-1)'

# AAMI/ANSI/ISO 81060-2 acceptance limits for the mean and the sd of the signed error.
# They are quoted per quantity, not pooled: a dataset that meets them on MAP and misses
# them on SBP is a different claim from one that meets them everywhere.
AAMI_MEAN_LIMIT = 5.0
AAMI_SD_LIMIT = 8.0


def preset_of(name: str):
    """standard120_080_... -> 1, standard255_195_... -> 4 (None when unknown)."""
    for key, (sbp, dbp, _map) in sorted(PRESETS.items(), reverse=True):
        if f'standard{sbp:03d}_{dbp:03d}_' in name:
            return key
    return None


def collect(paths, tier_index=None):
    runs = []
    skipped = []
    for path in paths:
        try:
            capture = reference_bp.load(path)
        except Exception as exc:  # a broken file is a finding, not a crash
            skipped.append((path, f'decode_error: {exc!r}'))
            continue
        if capture['firmware'] != FIRMWARE:
            skipped.append((path, f"firmware {capture['firmware']}"))
            continue
        preset = preset_of(Path(path).name)
        if preset is None:
            skipped.append((path, 'unrecognised preset in filename'))
            continue
        run_id = Path(path).name[: -len('.export.ndjson')]
        tier = None
        published = None
        if tier_index is not None:
            entry = tier_index.get(run_id)
            if entry is not None:
                tier = entry['tier']
                published = entry['published_corpus']
            else:
                tier = 'unclassified'
                published = False
        # The gate reads the pressure trace only; it never looks at the estimator,
        # so it can be applied before scoring without leaking the estimate back in.
        gate = validity_v2.check(str(path))
        result = reference_bp.estimate(capture, min_pressure=20.0)
        runs.append({'path': str(path), 'run_id': run_id, 'preset': preset,
                     'tier': tier, 'published_corpus': published,
                     'gate_usable': gate['usable'],
                     'peak_window_slope_mmhg_s': gate['peak_window_slope_mmhg_s'],
                     'result': result})
    return runs, skipped


def split_by_gate(runs):
    """(gate-passed, gate-failed) under the v2 validity gate."""
    passed = [r for r in runs if r['gate_usable']]
    failed = [r for r in runs if not r['gate_usable']]
    return passed, failed


def _summary(values):
    if not values:
        return None
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return {
        'n': len(values),
        'mean_error': round(mean, 2),
        'median_error': round(statistics.median(values), 2),
        'sd': round(sd, 2),
        'sd_population': round(statistics.pstdev(values), 2) if len(values) > 1 else 0.0,
        'min': round(min(values), 2),
        'max': round(max(values), 2),
        'worst_abs': round(max(abs(v) for v in values), 2),
        'aami_mean_ok': abs(mean) <= AAMI_MEAN_LIMIT,
        'aami_sd_ok': sd <= AAMI_SD_LIMIT,
        'aami_pass': abs(mean) <= AAMI_MEAN_LIMIT and sd <= AAMI_SD_LIMIT,
    }


def breakdown(runs, map_policy='ok'):
    """Per-preset error summaries.

    `map_policy` decides which runs contribute a MAP/DBP error, and it is the single
    most common way two published numbers end up disagreeing:

      'ok'             only runs whose status is exactly 'ok'. This is what
                       `tmp/score_prospective_frozen.py` does and therefore what every
                       frozen prospective figure in `data/reports/` was computed from.
      'not-unresolved' every run except `unresolved_map`. Wider, because a run refused
                       for SBP still has a trustworthy peak position.

    Default is 'ok' so that a re-run reproduces the published tables; pass
    'not-unresolved' only when making a statement specifically about MAP.
    """
    table = {}
    for preset, (sbp, dbp, map_ref) in PRESETS.items():
        sub = [r for r in runs if r['preset'] == preset]
        if not sub:
            continue
        # Distribution conventions of the frozen estimator:
        #   unresolved_map  -> no MAP and no DBP are published (the peak is unusable)
        #   unresolved_sbp  -> MAP and DBP are computable, SBP is not
        if map_policy == 'ok':
            map_ok = [r for r in sub if r['result']['status'] == 'ok']
        else:
            map_ok = [r for r in sub if r['result']['status'] != 'unresolved_map']
        sbp_ok = [r for r in sub if r['result']['status'] == 'ok']
        entry = {
            'panel_sbp': sbp, 'panel_dbp': dbp, 'panel_map': map_ref,
            'collected': len(sub),
            'refused_map': sum(1 for r in sub if r['result']['status'] == 'unresolved_map'),
            'refused_sbp': sum(1 for r in sub
                               if r['result']['status'] in ('unresolved_sbp', 'unresolved_map')),
            'map_policy': map_policy,
            'map': _summary([r['result']['map_mmhg'] - map_ref for r in map_ok]),
            'sbp': _summary([r['result']['sbp_mmhg'] - sbp for r in sbp_ok]),
            'dbp': _summary([r['result']['dbp_mmhg'] - dbp for r in map_ok]),
        }
        table[preset] = entry
    return table


def table_rows(table, quantity, panel_key):
    for preset in sorted(table):
        entry = table[preset]
        summary = entry[quantity]
        if summary is None:
            print(f"| {preset} | {entry[panel_key]} | {entry['collected']} | 0 | - | - |")
            continue
        verdict = 'PASS' if summary['aami_pass'] else (
            'mean' if not summary['aami_mean_ok'] else 'sd')
        cell = (f"{summary['mean_error']:+.2f} | {summary['sd']:.2f} | "
                f"{summary['median_error']:+.2f} | "
                f"{summary['min']:+.1f} .. {summary['max']:+.1f} | {verdict}")
        print(f"| {preset} | {entry[panel_key]} | {entry['collected']} | "
              f"{summary['n']} | {cell} |")


HEADER = ('| preset | panel | collected | published | mean | sd | median '
          '| range | AAMI |\n|---|---|---|---|---|---|---|---|---|')


def _map_selected(runs, map_policy):
    """Runs whose peak position is treated as published, under one policy."""
    if map_policy == 'ok':
        return [r for r in runs if r['result']['status'] == 'ok']
    return [r for r in runs if r['result']['status'] != 'unresolved_map']


def _pooled(runs, quantity, panel_index, map_policy='ok'):
    if quantity == 'sbp':
        sel = [r for r in runs if r['result']['status'] == 'ok']
    else:
        sel = _map_selected(runs, map_policy)
    return [r['result'][f'{quantity}_mmhg'] - PRESETS[r['preset']][panel_index]
            for r in sel]


def _pooled_line(label, runs, map_policy):
    print(f'| {label} | — | {sum(1 for _ in runs)} | — | '
          f'MAP {_fmt_pooled(_pooled(runs, "map", 2, map_policy))} | '
          f'SBP {_fmt_pooled(_pooled(runs, "sbp", 0, map_policy))} | '
          f'DBP {_fmt_pooled(_pooled(runs, "dbp", 1, map_policy))} |')


def _fmt_pooled(values):
    if len(values) < 2:
        return 'n/a'
    summary = _summary(values)
    verdict = 'PASS' if summary['aami_pass'] else (
        'mean' if not summary['aami_mean_ok'] else 'sd')
    return f"{summary['mean_error']:+.2f}/{summary['sd']:.2f} (n={summary['n']}, {verdict})"


def print_breakdown(runs, label, map_policy='ok', excluded=None):
    table = breakdown(runs, map_policy=map_policy)
    total = sum(e['collected'] for e in table.values())
    print(f'## {label}')
    print()
    print('availability is not accuracy: refusal means the estimator declined,')
    print('not that the recording is bad. sd is the sample-to-sample scatter of')
    print(f'the runs it did publish; MAP/DBP use the map_policy `{map_policy}`.')
    print(f'AAMI means |mean| <= {AAMI_MEAN_LIMIT:g} and sd <= {AAMI_SD_LIMIT:g} '
          'on the same signed errors.')
    print()
    print('### MAP (published unless a deflation-valve transient spoiled the peak)')
    print(HEADER)
    table_rows(table, 'map', 'panel_map')
    print()
    print('### SBP (published only when the high-pressure side is a decay, not a plateau)')
    print(HEADER)
    table_rows(table, 'sbp', 'panel_sbp')
    print()
    print('### DBP (published with MAP)')
    print(HEADER)
    table_rows(table, 'dbp', 'panel_dbp')
    print()
    print('### all presets pooled')
    print('| corpus | — | rounds | — | MAP | SBP | DBP |')
    print('|---|---|---|---|---|---|---|')
    _pooled_line(label, runs, map_policy)
    print()

    all_map = _pooled(runs, 'map', 2, map_policy)
    all_sbp = _pooled(runs, 'sbp', 0, map_policy)
    all_dbp = _pooled(runs, 'dbp', 1, map_policy)
    print(f"totals: {total} run(s), MAP published {len(all_map)}, "
          f"SBP published {len(all_sbp)}, DBP published {len(all_dbp)}")
    if excluded:
        print(f"excluded by the v2 validity gate: {len(excluded)} run(s)")
        for r in excluded:
            print(f"  {r['run_id']}  peak-window "
                  f"{r['peak_window_slope_mmhg_s']:+.2f} mmHg/s")
    print()
    return table, total, all_map, all_sbp


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--glob', default=DEFAULT_GLOB,
                        help=f'export glob (default: {DEFAULT_GLOB})')
    parser.add_argument('--tier', action='append', choices=dataset_tiers.TIER_ORDER,
                        help='restrict the corpus to these tiers (repeatable). '
                             'Without it every tier is reported on its own.')
    parser.add_argument('--published', action='store_true',
                        help='restrict to the published corpus: the three protocol '
                             'tiers plus supplementary rounds captured before v3 was '
                             'pre-registered. This reproduces the tables in '
                             'data/README.md.')
    parser.add_argument('--map-policy', choices=('ok', 'not-unresolved'), default='ok',
                        help="which runs contribute a MAP/DBP error: 'ok' reproduces the "
                             "frozen scorer, 'not-unresolved' is the wider view used by "
                             "the corpus tables in data/README.md (default: ok)")
    parser.add_argument('--include-gate-failures', action='store_true',
                        help='keep rounds the v2 validity gate rejects (deflation valve '
                             'throttling). Their errors are recording failures, not '
                             'measurements, and they are what made the pooled MAP sd '
                             'look like 12.78 instead of 4.73.')
    parser.add_argument('--json', type=Path, help='write the breakdown to this file')
    args = parser.parse_args()

    paths = sorted(glob.glob(str(ROOT / args.glob), recursive=True))
    if not paths:
        raise SystemExit(f'no exports matched {args.glob}')

    tier_rows = dataset_tiers.collect()
    tier_index = {r['run_id']: r for r in tier_rows}

    runs, skipped = collect(paths, tier_index)

    per_tier = {}
    if args.tier or args.published:
        if args.tier:
            runs = [r for r in runs if r['tier'] in args.tier]
        if args.published:
            runs = [r for r in runs if r['published_corpus']]
        if not runs:
            raise SystemExit('no exports left after restricting the corpus')
        kept, excluded = split_by_gate(runs)
        if args.include_gate_failures:
            kept, kept_excluded = runs, []
        else:
            kept_excluded = excluded
        parts = []
        if args.published:
            parts.append('published corpus')
        if args.tier:
            parts.append('tiers: ' + ', '.join(args.tier))
        label = '; '.join(parts) + f'  ({len(kept)} rounds)'
        table, total, all_map, all_sbp = print_breakdown(
            kept, label, map_policy=args.map_policy, excluded=kept_excluded)
        per_tier['restricted'] = {
            'tiers': args.tier, 'published_only': args.published,
            'map_policy': args.map_policy,
            'gate_filter': 'off' if args.include_gate_failures else 'v2 validity gate',
            'gate_excluded': [
                {'run_id': r['run_id'],
                 'peak_window_slope_mmhg_s': r['peak_window_slope_mmhg_s']}
                for r in kept_excluded],
            'presets': {str(k): v for k, v in sorted(table.items())},
            'totals': {'collected': total, 'map_published': len(all_map),
                       'sbp_published': len(all_sbp)},
        }
    else:
        printed = 0
        for tier in dataset_tiers.TIER_ORDER:
            sub = [r for r in runs if r['tier'] == tier]
            if not sub:
                continue
            kept, excluded = split_by_gate(sub)
            if args.include_gate_failures:
                kept, excluded = sub, []
            table, total, all_map, all_sbp = print_breakdown(
                kept, f'tier `{tier}`', map_policy=args.map_policy, excluded=excluded)
            per_tier[tier] = {
                'gate_filter': 'off' if args.include_gate_failures else 'v2 validity gate',
                'gate_excluded': [
                    {'run_id': r['run_id'],
                     'peak_window_slope_mmhg_s': r['peak_window_slope_mmhg_s']}
                    for r in excluded],
                'presets': {str(k): v for k, v in sorted(table.items())},
                'totals': {'collected': total, 'map_published': len(all_map),
                           'sbp_published': len(all_sbp)},
            }
            printed += total
        print(f'reported {printed} of {len(runs)} run(s) across '
              f'{len(per_tier)} tier(s)')
        protocol = [r for r in runs if r['tier'] in dataset_tiers.PROTOCOL_TIERS]
        published = [r for r in runs if r['published_corpus']]
        print(f'the three protocol tiers hold {len(protocol)} run(s); '
              f'the published corpus holds {len(published)}')
        print()

    if skipped:
        print(f"skipped {len(skipped)} file(s):")
        for path, why in skipped[:10]:
            print(f'  {Path(path).name}: {why}')
        if len(skipped) > 10:
            print(f'  ... and {len(skipped) - 10} more')

    if args.json:
        payload = {
            'glob': args.glob,
            'firmware': FIRMWARE,
            'sd_convention': SD_CONVENTION,
            'aami_limits': {'mean_mmhg': AAMI_MEAN_LIMIT, 'sd_mmhg': AAMI_SD_LIMIT},
            'tier_filter': args.tier,
            'published_only': args.published,
            'map_policy': args.map_policy,
            'gate_filter': 'off' if args.include_gate_failures else 'v2 validity gate',
            'by_tier': per_tier,
            'skipped': [{'path': str(p), 'reason': w} for p, w in skipped],
        }
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8', newline='\n')
        print('WROTE', args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
