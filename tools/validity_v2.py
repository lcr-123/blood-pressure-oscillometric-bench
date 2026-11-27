"""Capture-validity gate, version 2.

Purpose: decide whether a capture is fit to be scored at all. This is deliberately
separate from the estimator, which answers "what pressure does this waveform
imply". A round can decode perfectly and still be unfit, because the fixture
failed to generate the pressure profile it claims to generate.

Why one criterion and not two:

  peak-window deflation rate   |slope| > 4.0 mmHg/s   USED
  neighbourhood median         > 10 mV               REJECTED

The neighbourhood-median criterion was rejected on measurement: normal development
rounds reach 11.14 mV and normal prospective rounds reach 10.32 mV, so a 10 mV
threshold would refuse healthy captures. The deflate-rate criterion has a fivefold
margin instead: normal rounds top out at 2.63 mmHg/s (development) and 1.91
(prospective), while the two observed valve failures were 13.35 and 15.49.

The threshold is derived from the development set alone: its maximum is 2.63, so
4.0 sits comfortably above anything the fixture produces when it works.

This gate reads only the pressure trace. It never looks at the estimator output, so
enabling it cannot bias the estimator's error statistics.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import reference_bp  # noqa: E402

VERSION = 'validity_v2'
PEAK_LOW_MMHG = 200.0
PEAK_HIGH_MMHG = 245.0
DEFLATE_RATE_MAX_MMHG_S = 4.0
MIN_PEAK_WINDOW_POINTS = 40
NORMAL_RATE_OBSERVED = (1.56, 2.63)      # (min, max) across 38 healthy rounds
FAILURE_RATE_OBSERVED = (13.35, 15.49)   # the two observed valve failures


def peak_window_slope(capture):
    """OLS slope of cuff pressure against time inside 200-245 mmHg."""
    pressure = np.asarray(capture['pressure'], dtype=float)
    interval = capture['interval_ms'] / 1000.0
    time = np.arange(len(pressure)) * interval
    window = (pressure >= PEAK_LOW_MMHG) & (pressure <= PEAK_HIGH_MMHG)
    if window.sum() < MIN_PEAK_WINDOW_POINTS:
        return float('nan'), int(window.sum())
    return float(np.polyfit(time[window], pressure[window], 1)[0]), int(window.sum())


def check(export_path):
    """Return a verdict dict for one export. Never raises for a readable capture."""
    verdict = {
        'export': str(export_path),
        'gate': VERSION,
        'rate_limit_mmhg_s': DEFLATE_RATE_MAX_MMHG_S,
        'usable': True,
        'reasons': [],
    }
    try:
        capture = reference_bp.load(Path(export_path))
    except Exception as exc:  # decode failure is already an exclusion rule
        verdict.update(usable=False, reasons=[f'decode failure: {exc}'])
        return verdict

    slope, n_window = peak_window_slope(capture)
    verdict['peak_window_points'] = n_window
    verdict['peak_window_slope_mmhg_s'] = None if np.isnan(slope) else round(slope, 3)
    verdict['duration_s'] = round(capture['duration_s'], 2)

    if np.isnan(slope):
        verdict.update(usable=False,
                       reasons=[f'only {n_window} points inside '
                                f'{PEAK_LOW_MMHG:.0f}-{PEAK_HIGH_MMHG:.0f} mmHg, cannot '
                                'establish the deflation rate'])
        return verdict

    if abs(slope) > DEFLATE_RATE_MAX_MMHG_S:
        verdict.update(
            usable=False,
            reasons=[f'peak-window deflation ran at {slope:+.2f} mmHg/s against a limit of '
                     f'{DEFLATE_RATE_MAX_MMHG_S:.1f}; healthy rounds measured '
                     f'{NORMAL_RATE_OBSERVED[0]:.2f}..{NORMAL_RATE_OBSERVED[1]:.2f}, so the '
                     'deflate valve was not throttling and the round does not represent the '
                     'intended pressure profile'])
    return verdict


def main():
    if len(sys.argv) < 2:
        raise SystemExit('usage: python tmp/validity_v2.py <export.ndjson> [...] [--json out]')
    args = sys.argv[1:]
    out = None
    if '--json' in args:
        index = args.index('--json')
        out = Path(args[index + 1])
        args = args[:index] + args[index + 2:]

    verdicts = [check(path) for path in args]
    for verdict in verdicts:
        name = Path(verdict['export']).name
        state = 'USABLE' if verdict['usable'] else 'REJECT'
        slope = verdict.get('peak_window_slope_mmhg_s')
        slope_text = 'n/a' if slope is None else f'{slope:+.2f}'
        print(f'{name}: {state}  peak_slope={slope_text} mmHg/s')
        for reason in verdict['reasons']:
            print(f'   {reason}')

    if out:
        out.write_text(json.dumps(verdicts, ensure_ascii=False, indent=2) + '\n',
                       encoding='utf-8')
        print('WROTE', out)


if __name__ == '__main__':
    main()
