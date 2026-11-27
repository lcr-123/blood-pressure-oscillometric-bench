"""Recompute a freeze record's baseline on the pressure axis the record pins.

Why this exists
---------------
The three records written before 2026-11-26 (v1 / v2 / v3) hash `tools/` and the
validity gate, but they never pin the pressure axis. The axis is baked into every
export's `p` values by the firmware at capture time, so after the 2026-11-26 refit
(`cal write 81.529 -20.03`) `tools/verify_freeze.py` still reports those records
intact while the baseline numbers they record -- MAP sd 3.70, SBP sd 9.70, DBP sd
9.60 -- can no longer be produced by the current hardware.

A freeze record that cannot be recomputed cannot be checked. This tool closes that
gap: given a record it rebuilds the baseline over the record's own round set, on the
record's own axis, and reports both sd conventions. When the pinned axis differs from
the axis the captures were taken on, it also reports the capture-axis reading, so a
reader can see which of the two a recorded number came from.

Usage:
    python tools/freeze_baseline.py --record data/protocols/reference_bp_freeze_v6.json
    python tools/freeze_baseline.py --record ... --out data/reports/x.json
    python tools/freeze_baseline.py --record ... --print-record-axis
    python tools/freeze_baseline.py --axis-slope 82.326 --axis-intercept -19.887
    python tools/freeze_baseline.py --axis-slope 81.5286 --axis-intercept -20.0279 --no-capture-axis
"""
import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import covered_bp            # noqa: E402
import reference_bp          # noqa: E402
import validity_v2           # noqa: E402

RAW = ROOT / 'data' / 'raw' / 'development_20261101'
MANIFEST = ROOT / 'data' / 'manifest.json'
FIELDS = ('map_mmhg', 'sbp_mmhg', 'dbp_mmhg')
# covered_bp.PANEL is (sbp, dbp, map); FIELDS is (map, sbp, dbp). Keep them apart.
PANEL_AT = {'sbp_mmhg': 0, 'dbp_mmhg': 1, 'map_mmhg': 2}
# The axis the pre-2026-11-26 captures were taken on. Every export's `p` values are
# in this frame regardless of what the firmware is configured with today.
CAPTURE_AXIS = (82.326, -19.887)

_ORIGINAL_LOAD = reference_bp.load


def transform(axis, capture_axis=CAPTURE_AXIS):
    """Scale and shift that take a capture-frame pressure to `axis`.

    p_new = (1 + b) * p_old + a, written with slope/intercept pairs:
    p_new = (slope_new / slope_capture) * p_old
            + (intercept_new - intercept_capture * slope_new / slope_capture)
    """
    scale = axis[0] / capture_axis[0]
    return scale, axis[1] - capture_axis[1] * scale


def rounds_for_tier(tier):
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    out = []
    for row in manifest['rows']:
        if row.get('tier') != tier:
            continue
        path = RAW / (row['run_id'] + '.export.ndjson')
        if path.exists():
            out.append((row['run_id'], path))
    return sorted(out)


def score(rounds, axis, capture_axis=CAPTURE_AXIS):
    scale, shift = transform(axis, capture_axis)
    original = reference_bp.load

    def load(export_path):
        capture = original(export_path)
        if (scale, shift) != (1.0, 0.0):
            capture['pressure'] = [p * scale + shift for p in capture['pressure']]
        return capture

    reference_bp.load = load
    try:
        errors = {f: [] for f in FIELDS}
        detail = []
        gate_rejected = 0
        published = 0
        for run_id, path in rounds:
            meta_path = RAW / (run_id + '.metadata.json')
            meta = json.loads(meta_path.read_text(encoding='utf-8')) if meta_path.exists() else {}
            preset = meta.get('panel_preset')
            if preset is None or int(preset) not in covered_bp.PANEL:
                gate_rejected += 1
                detail.append({'run_id': run_id, 'status': 'no panel preset'})
                continue
            panel = covered_bp.PANEL[int(preset)]
            check = validity_v2.check(path)
            if not check['usable']:
                gate_rejected += 1
                detail.append({'run_id': run_id, 'status': 'gate_rejected',
                               'peak_window_slope_mmhg_s':
                                   check.get('peak_window_slope_mmhg_s'),
                               'reasons': check.get('reasons')})
                continue
            est = reference_bp.estimate(load(path))
            row = {'run_id': run_id, 'preset': int(preset), 'status': est.get('status')}
            if est.get('status') == 'ok':
                published += 1
                for field in FIELDS:
                    value = est.get(field)
                    if value is None:
                        continue
                    error = value - panel[PANEL_AT[field]]
                    errors[field].append(error)
                    row[field] = round(value, 2)
                    row[field.replace('_mmhg', '_err')] = round(error, 2)
            detail.append(row)
    finally:
        reference_bp.load = original

    summary = {}
    for field in FIELDS:
        values = errors[field]
        if not values:
            summary[field] = None
            continue
        summary[field] = {
            'n': len(values),
            'mean': round(statistics.fmean(values), 4),
            'population_sd': round(statistics.pstdev(values), 4),
            'sample_sd': round(statistics.stdev(values), 4) if len(values) > 1 else None,
            'max_abs': round(max(abs(v) for v in values), 4),
        }
    return {'axis': {'slope': axis[0], 'intercept': axis[1],
                     'capture_slope': capture_axis[0], 'capture_intercept': capture_axis[1],
                     'scale': round(scale, 10), 'shift': round(shift, 10)},
            'rounds': len(rounds),
            'gate_rejected': gate_rejected,
            'published': published,
            'summary': summary,
            'detail': detail}


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--record', help='freeze record JSON to read the axis and tier from')
    parser.add_argument('--tier', default=None,
                        help='manifest tier to score (default: the record baseline_tier, '
                             'else frozen_baseline_v2)')
    parser.add_argument('--axis-slope', type=float, help='override slope (ad-hoc mode)')
    parser.add_argument('--axis-intercept', type=float, help='override intercept (ad-hoc mode)')
    parser.add_argument('--capture-slope', type=float, default=CAPTURE_AXIS[0],
                        help='slope the captures were taken on (default 82.326)')
    parser.add_argument('--capture-intercept', type=float, default=CAPTURE_AXIS[1],
                        help='intercept the captures were taken on (default -19.887)')
    parser.add_argument('--no-capture-axis', action='store_true',
                        help='skip the second reading on the capture axis')
    parser.add_argument('--out', help='write the full JSON here')
    parser.add_argument('--json', action='store_true', help='print the JSON instead of a table')
    parser.add_argument('--print-record-axis', action='store_true',
                        help='print only the axis the record pins, then exit')
    args = parser.parse_args()

    record = None
    if args.record:
        record = json.loads(Path(args.record).read_text(encoding='utf-8'))
    if args.print_record_axis:
        if record is None:
            raise SystemExit('--print-record-axis needs --record')
        axis = record.get('pressure_axis')
        print(json.dumps(axis, ensure_ascii=False, indent=2) if axis
              else 'this record pins no pressure axis')
        return 0

    tier = args.tier or (record.get('baseline_tier') if record else None) or 'frozen_baseline_v2'
    capture_axis = (args.capture_slope, args.capture_intercept)

    if args.record and record.get('pressure_axis'):
        pinned = record['pressure_axis']
        axis = (pinned['slope'], pinned['intercept'])
        capture_axis = (pinned.get('capture_slope', capture_axis[0]),
                        pinned.get('capture_intercept', capture_axis[1]))
    elif args.axis_slope is not None and args.axis_intercept is not None:
        axis = (args.axis_slope, args.axis_intercept)
    else:
        raise SystemExit('give --record with a pressure_axis block, or --axis-slope/'
                         '--axis-intercept for an ad-hoc run')

    rounds = rounds_for_tier(tier)
    if not rounds:
        raise SystemExit(f'no rounds found for tier {tier}')

    current = score(rounds, axis, capture_axis)
    # The payload is a pure function of (tier, axis, capture axis, round set): no path,
    # no label, no timestamp. That way an ad-hoc run and a --record run over the same
    # inputs produce byte-identical files, which is what lets a record hash its own
    # baseline report and lets anyone recompute that hash.
    result = {'tier': tier,
              'pinned_axis': current['axis'],
              'rounds': current['rounds'],
              'gate_rejected': current['gate_rejected'],
              'published': current['published'],
              'summary_on_pinned_axis': current['summary'],
              'detail': current['detail']}
    if not args.no_capture_axis and (axis != tuple(capture_axis)):
        on_capture = score(rounds, capture_axis, capture_axis)
        result['summary_on_capture_axis'] = on_capture['summary']
        result['note'] = ('the captures were taken on slope %.3f intercept %.3f; '
                          'the pinned axis differs, so both readings are given and only '
                          'the pinned one is what this record claims'
                          % (capture_axis[0], capture_axis[1]))

    # Determinism: nothing time-stamped goes in, so the same inputs give the same bytes.
    payload = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    encoded = payload.encode('utf-8')

    if args.out:
        out = Path(args.out)
        out.write_bytes(encoded)
        try:
            shown = out.resolve().relative_to(ROOT)
        except ValueError:
            shown = out          # outside the repo, e.g. a temp file from verify_freeze
        print('WROTE %s  %d bytes  sha256 %s'
              % (shown, len(encoded), hashlib.sha256(encoded).hexdigest()))
    if args.json:
        print(payload, end='')
        return 0

    print('tier %s   rounds %d   gate_rejected %d   published %d'
          % (tier, current['rounds'], current['gate_rejected'], current['published']))
    print('pinned axis %.4f / %.3f  (captures taken on %.4f / %.3f)  scale %.8f  shift %+.5f'
          % (axis[0], axis[1], capture_axis[0], capture_axis[1],
             current['axis']['scale'], current['axis']['shift']))
    for heading, summary in (('pinned axis', result['summary_on_pinned_axis']),
                             ('capture axis', result.get('summary_on_capture_axis'))):
        if not summary:
            continue
        print('  [%s]' % heading)
        for field in FIELDS:
            cell = summary[field]
            if not cell:
                print('    %-9s --' % field)
                continue
            print('    %-9s n=%2d  mean %+7.3f  popsd %6.3f  samplesd %6.3f  max_abs %6.2f'
                  % (field, cell['n'], cell['mean'], cell['population_sd'],
                     cell['sample_sd'] if cell['sample_sd'] is not None else float('nan'),
                     cell['max_abs']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
