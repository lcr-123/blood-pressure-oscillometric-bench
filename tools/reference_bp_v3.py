#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Freeze-v3 estimator: tools/reference_bp.py with exactly one constant changed.

The frozen v2 record pins the sha256 of `tools/reference_bp.py`. Changing
`DEFAULT_MAP_SMOOTHING_S` inside that file would break v2 verification, and a holdout
whose frozen artifacts no longer verify is not a holdout. So v3 is a thin module that
re-exports the v2 implementation and overrides only the MAP median-window default.

Everything else -- the algorithm, the plateau test, the transient test, the sustained
-crossing rule, the ratio sweep -- comes from v2 by import, so the two versions cannot
drift apart in any way except the one constant this file exists to change.

Why 3 s and not something else: see
`data/protocols/reference_bp_freeze_v3_candidate.md`. In one sentence, a 3 s median
window is the only change measured on the 62-run corpus that refuses the round whose
deflate valve never throttled (MAP 202.9 against a panel 116) instead of publishing it.
That is a safety argument, not an accuracy one, and the candidate carries a pre-committed
acceptance test that must run on rounds captured after this freeze.

Usage:
    python tools/reference_bp_v3.py <export.ndjson> [...]
    python tools/reference_bp_v3.py --json out.json <export.ndjson>

Exit code is 0 even when a run cannot yield a pressure: "no answer" is a valid
dataset observation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import reference_bp as _v2  # noqa: E402

VERSION = 'reference_bp_v3'

# The one difference from v2. 2.0 s in v2.
DEFAULT_MAP_SMOOTHING_S = 3.0

# Re-exported unchanged so a caller can read the whole effective configuration
# from this module without also importing v2.
DEFAULT_SBP_RATIO = _v2.DEFAULT_SBP_RATIO
DEFAULT_DBP_RATIO = _v2.DEFAULT_DBP_RATIO
DEFAULT_SKIP_START_S = _v2.DEFAULT_SKIP_START_S
RATIO_SWEEP = _v2.RATIO_SWEEP
PLATEAU_FRACTION = _v2.PLATEAU_FRACTION
PLATEAU_REFUSE_RATIO = _v2.PLATEAU_REFUSE_RATIO
MIN_ENVELOPE_V = _v2.MIN_ENVELOPE_V
TRANSIENT_FACTOR = _v2.TRANSIENT_FACTOR
SBP_SUSTAINED_SAMPLES = _v2.SBP_SUSTAINED_SAMPLES
DBP_SUSTAINED_SAMPLES = _v2.DBP_SUSTAINED_SAMPLES

load = _v2.load


def estimate(capture, sbp_ratio=DEFAULT_SBP_RATIO, dbp_ratio=DEFAULT_DBP_RATIO,
             min_pressure=20.0, skip_start_s=DEFAULT_SKIP_START_S,
             map_smoothing_s=DEFAULT_MAP_SMOOTHING_S):
    """Identical to v2 except that the window default is 3 s."""
    return _v2.estimate(capture, sbp_ratio, dbp_ratio, min_pressure,
                        skip_start_s, map_smoothing_s)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('exports', nargs='+', help='bp.capture/4 export file(s)')
    parser.add_argument('--sbp-ratio', type=float, default=DEFAULT_SBP_RATIO)
    parser.add_argument('--dbp-ratio', type=float, default=DEFAULT_DBP_RATIO)
    parser.add_argument('--min-pressure', type=float, default=20.0)
    parser.add_argument('--skip-start-s', type=float, default=DEFAULT_SKIP_START_S)
    parser.add_argument('--map-smoothing-s', type=float, default=DEFAULT_MAP_SMOOTHING_S)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args()

    reports = []
    for export in args.exports:
        try:
            capture = load(export)
        except Exception as exc:
            reports.append({'export': str(export), 'status': 'decode_error',
                            'error': repr(exc)})
            print(f'{Path(export).name}: DECODE ERROR {exc}', file=sys.stderr)
            continue
        report = {'export': str(export), 'n': capture['n'],
                  'firmware': capture['firmware'],
                  'duration_s': round(capture['duration_s'], 2),
                  'checksum': capture['checksum'], 'estimator': VERSION}
        report.update(estimate(capture, args.sbp_ratio, args.dbp_ratio,
                               args.min_pressure, args.skip_start_s,
                               args.map_smoothing_s))
        reports.append(report)
        print(f"{Path(export).name}: status={report['status']} "
              f"MAP={report.get('map_mmhg')} SBP={report.get('sbp_mmhg')} "
              f"DBP={report.get('dbp_mmhg')}")
    if args.json:
        args.json.write_text(json.dumps(reports, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
        print('WROTE', args.json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
