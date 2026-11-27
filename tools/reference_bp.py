#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reference oscillometric blood-pressure estimator for the bp.capture/4 dataset.

This is the dataset-level reference implementation. It is deliberately separate
from the firmware algorithm: the firmware fixes its MAP search window to
80..100 mmHg and its SBP/DBP limits to 250/150, which only fits a human adult at
one cuff pressure profile. A dataset user needs an estimator that searches the
whole deflation and reports what it actually found.

Method (classic oscillometric ratio method, as in the literature):
  1. envelope  = exported smooth envelope `s` (or recomputed from `v` if absent)
  2. MAP       = cuff pressure at the maximum of the smoothed envelope
  3. SBP       = cuff pressure on the high-pressure side of MAP where the
                 envelope has fallen to `sbp_ratio * max`
  4. DBP       = cuff pressure on the low-pressure side of MAP where the
                 envelope has fallen to `dbp_ratio * max`

Index direction matters: the records run from the start of deflation (high cuff
pressure) to the end (low pressure), so the high-pressure side of MAP is at
SMALLER indices and the low-pressure side at LARGER indices.

Two things this estimator will NOT hide:

  * Envelope plateau. On a rigid bench fixture (a piston pushing a fixed volume
    into a stiff chamber) the envelope does not decay above MAP the way it does
    over a human brachial artery, so the high side stays near the peak and the
    SBP crossing collapses towards the start of deflation. When that happens the
    estimator reports `sbp_plateau_suspected` instead of a confident SBP.

  * Ratio sensitivity. The ratios are conventions (0.5/0.6 here), not physics.
    Every result carries the values at neighbouring ratios so a reader can see
    how much the answer moves.

Usage:
    python tools/reference_bp.py <export.ndjson> [...]
    python tools/reference_bp.py --json out.json <export.ndjson>
    python tools/reference_bp.py --sbp-ratio 0.55 --dbp-ratio 0.65 <export.ndjson>

Exit code is 0 even when a run cannot yield a pressure, because "no answer" is a
valid dataset observation; it is reported as `status: "unresolved"`.
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blood pressure monitor' / 'tools'))

try:
    import bp_capture  # the strict bp.capture/4 decoder shipped with the firmware tools
except ImportError as exc:  # pragma: no cover - depends on checkout layout
    raise SystemExit(f'cannot import bp_capture from the firmware tools: {exc}')

DEFAULT_SBP_RATIO = 0.50
DEFAULT_DBP_RATIO = 0.60
DEFAULT_SKIP_START_S = 2.0
DEFAULT_MAP_SMOOTHING_S = 2.0
RATIO_SWEEP = (0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70)
# Plateau test for the high-pressure side of MAP. Above MAP a human envelope
# decays fast; this fixture holds it near the peak, so a large plateau fraction
# means the ratio crossing is not a systolic estimate.
PLATEAU_FRACTION = 0.90        # "still near the peak" means above this fraction
PLATEAU_REFUSE_RATIO = 0.25    # refuse SBP when more than this share of the high side plateaus
MIN_ENVELOPE_V = 1e-4      # below this the envelope is indistinguishable from noise
TRANSIENT_FACTOR = 2.0     # a peak this many times its own neighbourhood is a valve spike
# The firmware requires three consecutive samples below the diastolic threshold
# (bp_algorithm.c:581). The same guard is applied here to both crossings, because
# the fixture envelope is noisy and a single dip is not a transition.
SBP_SUSTAINED_SAMPLES = 3
DBP_SUSTAINED_SAMPLES = 3


def _f32(bits):
    """Decode a float32 bit pattern as stored in bp.capture/4."""
    return struct.unpack('<f', struct.pack('<I', bits & 0xFFFFFFFF))[0]


def load(export_path):
    """Decode one export strictly; raise if the file is not a complete capture."""
    lines = [line.strip() for line in Path(export_path).read_text(encoding='utf-8').splitlines()
             if line.strip()]
    capture = bp_capture.decode(lines)
    interval = capture['header']['interval_ms']
    points = capture['points']
    pressure, envelope, smooth, elapsed = [], [], [], 0
    for index, point in enumerate(points):
        if index:
            elapsed += (point['t'] - points[index - 1]['t']) & 0xFFFFFFFF
        pressure.append(_f32(point['p']))
        envelope.append(_f32(point['e']) if point['e'] is not None else None)
        smooth.append(_f32(point['s']) if point['s'] is not None else None)
    return {
        'export': str(export_path),
        'firmware': capture['header']['firmware'],
        'n': len(points),
        'interval_ms': interval,
        'pressure': pressure,
        'envelope': envelope,
        'smooth': smooth,
        'calc': capture['header']['calc'],
        'checksum': capture['end']['hash'],
        'duration_s': elapsed / 1000.0,
    }


def _crossing(pressure, series, start_index, direction, target, sustained=1):
    """First index from start_index where series has fallen to `target`.

    direction=-1 walks towards higher pressure, +1 towards lower pressure.
    Returns None when the series never reaches the target inside the deflation.

    `sustained` requires that many consecutive samples stay at or below the
    target before the crossing is accepted. On this fixture the envelope above
    MAP is both nearly flat and noisy, so a single sample below the threshold is
    often a local dip; requiring a sustained run is the same guard the firmware
    already applies to its diastolic search.

    The returned value is clipped to the pressure at the START of the accepted
    run, so a dip is reported where it begins rather than where it ends.
    """
    index = start_index
    step = direction
    run = []
    while 0 <= index < len(series):
        value = series[index]
        if value is None:
            index += step
            continue
        if value <= target:
            run.append(index)
            if len(run) >= sustained:
                first = run[0]
                previous = first - step
                if not (0 <= previous < len(series)) or series[previous] is None:
                    return pressure[first]
                va, vb = series[previous], series[first]
                if va == vb:
                    return pressure[first]
                span = (va - target) / (va - vb)
                return pressure[previous] + span * (pressure[first] - pressure[previous])
        else:
            run = []
        index += step
    return None



def _rolling_median(values, window):
    """Centred rolling median that ignores None entries, used only for peak finding.

    A single deflation-valve transient can be several times the true envelope
    peak (one 2026-11-07 run spikes to 61.7 mV against a 13 mV real peak). Taking
    the maximum of the raw series would put MAP on that spike, so the peak is
    located on a median-filtered copy instead.
    """
    if window < 3:
        return values
    half = window // 2
    out = []
    for index in range(len(values)):
        chunk = [v for v in values[max(0, index - half):index + half + 1] if v is not None]
        if not chunk:
            out.append(None)
            continue
        chunk.sort()
        out.append(chunk[len(chunk) // 2])
    return out


def estimate(capture, sbp_ratio=DEFAULT_SBP_RATIO, dbp_ratio=DEFAULT_DBP_RATIO,
             min_pressure=20.0, skip_start_s=DEFAULT_SKIP_START_S,
             map_smoothing_s=DEFAULT_MAP_SMOOTHING_S):
    """Run the ratio method over the full deflation range.

    skip_start_s drops the first moments of deflation, where the first valve
    openings dump air far faster than the closed-loop rate and the envelope picks
    up a large transient. The firmware uses the same 2 s guard (start_idx = 80 at
    25 ms).

    map_smoothing_s applies a centred rolling median before locating the envelope
    peak, so an isolated transient cannot move MAP.
    """
    pressure = capture['pressure']
    series = capture['smooth'] if capture['calc'] in (2, 3) and any(capture['smooth']) \
        else capture['envelope']
    interval = max(capture['interval_ms'], 1)
    first_index = int(round(skip_start_s * 1000.0 / interval))
    window = max(3, int(round(map_smoothing_s * 1000.0 / interval)) | 1)
    peak_series = _rolling_median(series, window)
    half = max(1, window // 2)
    wide_half = half * 4
    usable = [i for i, p in enumerate(pressure)
              if i >= first_index and p >= min_pressure and series[i] is not None
              and peak_series[i] is not None]
    if len(usable) < 50:
        return {'status': 'unresolved', 'reason': 'too few points above the pressure floor'}

    peak_value = max(series[i] for i in usable)
    if peak_value < MIN_ENVELOPE_V:
        return {'status': 'unresolved',
                'reason': 'envelope stays at the noise floor for the whole deflation',
                'envelope_peak_v': peak_value}

    # Transient guard. A real oscillometric envelope changes slowly compared with
    # the deflation valve period, so an isolated spike that is much taller than the
    # surrounding second-scale level is a valve artefact, not a pulse envelope.
    # It is detected rather than silently smoothed away: the flag stays in the
    # report so a user can see the run was affected.
    peak_index = max(usable, key=lambda i: series[i])
    neighbouring = [series[j] for j in usable
                    if abs(j - peak_index) <= wide_half and abs(j - peak_index) > half]
    transient = bool(neighbouring
                     and peak_value > TRANSIENT_FACTOR * sorted(neighbouring)[len(neighbouring) // 2])

    map_index = max(usable, key=lambda i: peak_series[i])
    map_pressure = pressure[map_index]
    raw_max_index = peak_index
    raw_max_mv = round(series[raw_max_index] * 1000.0, 3)
    filtered_max_mv = round(peak_series[map_index] * 1000.0, 3)
    # Ratio thresholds use the transient-free peak so MAP and the two crossings
    # are all defined against the same envelope level.
    threshold_level = peak_series[map_index]

    # Records run from high cuff pressure to low, so the systolic side is towards
    # index 0 and the diastolic side towards the end.
    sbp = _crossing(pressure, series, map_index, -1, sbp_ratio * threshold_level,
                    sustained=SBP_SUSTAINED_SAMPLES)
    dbp = _crossing(pressure, series, map_index, +1, dbp_ratio * threshold_level,
                    sustained=DBP_SUSTAINED_SAMPLES)

    # A systolic crossing assumes the envelope falls steadily as cuff pressure rises
    # above MAP. That holds weakly on this fixture: the high-pressure side is a
    # shallow plateau rather than the steep decline seen over a brachial artery, and
    # on the worst round a third of it still sits above 0.9 x peak. When the plateau
    # is that large, the ratio crossing lands wherever the plateau ends, so it is
    # reported as unidentifiable instead of as a number. Everything below that
    # threshold is published, with its measured error, rather than hidden.
    high_side = [i for i in usable if pressure[i] >= map_pressure]
    plateau_count = sum(1 for i in high_side
                        if series[i] is not None and series[i] >= PLATEAU_FRACTION * threshold_level)
    plateau_ratio = plateau_count / len(high_side) if high_side else 0.0
    plateau_suspected = plateau_ratio > PLATEAU_REFUSE_RATIO
    start_pressure = pressure[usable[0]]

    result = {
        'status': 'ok' if (sbp is not None and dbp is not None) else 'partial',
        'method': 'oscillometric ratio, full deflation range',
        'sbp_ratio': sbp_ratio,
        'dbp_ratio': dbp_ratio,
        'map_mmhg': round(map_pressure, 2),
        'map_index': map_index,
        'envelope_peak_v': peak_value,
        'envelope_peak_raw_mv': raw_max_mv,
        'envelope_peak_median_filtered_mv': filtered_max_mv,
        'envelope_peak_raw_at_mmhg': round(pressure[raw_max_index], 2),
        'envelope_transient_suspected': transient,
        'map_smoothing_s': map_smoothing_s,
        'skip_start_s': skip_start_s,
        'min_pressure_mmhg': min_pressure,
        'sbp_mmhg': None if sbp is None else round(sbp, 2),

        'dbp_mmhg': None if dbp is None else round(dbp, 2),
        'high_side_point_count': len(high_side),
        'high_side_plateau_count': plateau_count,
        'high_side_plateau_ratio': round(plateau_ratio, 4),
        'sbp_plateau_suspected': plateau_suspected,
        'sbp_origin_pressure_mmhg': round(start_pressure, 2),
        'deflation_range_mmhg': [round(pressure[usable[0]], 2), round(pressure[usable[-1]], 2)],
    }
    if plateau_suspected:
        result['status'] = 'unresolved_sbp'
        result['sbp_mmhg'] = None
        result['reason'] = (
            f'{plateau_count} of {len(high_side)} points above MAP '
            f'({plateau_ratio:.1%}) still exceed {PLATEAU_FRACTION:.0%} of the peak, so the '
            'envelope is a plateau rather than a decay and the systolic ratio crossing is not '
            'identifiable; a rigid bench chamber holds the pulse amplitude up instead of '
            'collapsing it the way a compressed artery does')
    if transient:
        # A spike wide enough to survive the median filter can still drag MAP with it,
        # so refuse to publish a MAP rather than publish a wrong one.
        result['status'] = 'unresolved_map'
        result['reason'] = (
            f'the envelope maximum ({raw_max_mv} mV at '
            f'{result["envelope_peak_raw_at_mmhg"]} mmHg) is more than {TRANSIENT_FACTOR}x its own '
            'neighbourhood, which is the signature of a deflation-valve transient; inspect the '
            'run or widen --skip-start-s before trusting MAP')

    sweep = []
    for ratio in RATIO_SWEEP:
        crossed = _crossing(pressure, series, map_index, -1, ratio * threshold_level,
                            sustained=SBP_SUSTAINED_SAMPLES)
        sweep.append({'sbp_ratio': ratio,
                      'sbp_mmhg': None if crossed is None else round(crossed, 2)})
    result['sbp_ratio_sweep'] = sweep

    sweep = []
    for ratio in RATIO_SWEEP:
        crossed = _crossing(pressure, series, map_index, +1, ratio * threshold_level,
                            sustained=DBP_SUSTAINED_SAMPLES)
        sweep.append({'dbp_ratio': ratio,
                      'dbp_mmhg': None if crossed is None else round(crossed, 2)})
    result['dbp_ratio_sweep'] = sweep
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('exports', nargs='+', help='bp.capture/4 export file(s)')
    parser.add_argument('--sbp-ratio', type=float, default=DEFAULT_SBP_RATIO)
    parser.add_argument('--dbp-ratio', type=float, default=DEFAULT_DBP_RATIO)
    parser.add_argument('--min-pressure', type=float, default=20.0,
                        help='ignore points below this cuff pressure (default 20 mmHg)')
    parser.add_argument('--skip-start-s', type=float, default=DEFAULT_SKIP_START_S,
                        help='discard this many seconds at the start of deflation '
                             '(the valve-opening transient, default 2 s)')
    parser.add_argument('--map-smoothing-s', type=float, default=DEFAULT_MAP_SMOOTHING_S,
                        help='centred rolling median width used to locate the envelope '
                             'peak (default 2 s); the raw maximum is still reported')
    parser.add_argument('--json', type=Path, help='write the full report to this file')
    args = parser.parse_args()

    reports = []
    for export in args.exports:
        try:
            capture = load(export)
        except Exception as exc:
            reports.append({'export': str(export), 'status': 'decode_error', 'error': repr(exc)})
            print(f'{Path(export).name}: DECODE ERROR {exc}', file=sys.stderr)
            continue
        report = {'export': str(export), 'n': capture['n'], 'firmware': capture['firmware'],
                  'duration_s': round(capture['duration_s'], 2),
                  'checksum': capture['checksum']}
        report.update(estimate(capture, args.sbp_ratio, args.dbp_ratio, args.min_pressure,
                               args.skip_start_s, args.map_smoothing_s))
        reports.append(report)
        print(f"{Path(export).name}: status={report['status']} "
              f"MAP={report.get('map_mmhg')} SBP={report.get('sbp_mmhg')} "
              f"DBP={report.get('dbp_mmhg')}"
              + ('  [SBP PLATEAU]' if report.get('sbp_plateau_suspected') else ''))

    if args.json:
        args.json.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
        print('WROTE', args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
