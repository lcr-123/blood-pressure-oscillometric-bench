"""How much headroom above its own SBP does each preset actually have?

The oscillometric ratio method finds SBP by walking up from MAP until the envelope reaches
0.5x its peak. That search needs deflation data ABOVE SBP, where the envelope is supposed
to be small, otherwise the crossing is decided by whatever the first seconds of deflation
happen to look like.

Every run in this dataset was inflated to the same target (275-278 mmHg), but the panel's
own SBP differs by preset - 120 for Preset 1, 255 for Preset 4. So the headroom shrinks
monotonically with the preset, and on Preset 4 it is almost nothing: the record starts 6
mmHg above SBP, which is 2 s of data. That is the real reason Preset 4's SBP is unstable,
and it is not something a ratio constant can fix.

Output columns: panel SBP, where deflation starts, the headroom, the fraction of the peak
envelope already present at the start, and how many seconds the record spends above SBP.

Usage:
    python tools/sbp_headroom.py [exports...]
    python tools/sbp_headroom.py --all
"""
import argparse
import glob
import os
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_bp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

PRESETS = {
    'standard120_080': dict(number=1, sbp=120.0, dbp=80.0, map=93.0),
    'standard150_100': dict(number=2, sbp=150.0, dbp=100.0, map=116.0),
    'standard200_150': dict(number=3, sbp=200.0, dbp=150.0, map=166.0),
    'standard255_195': dict(number=4, sbp=255.0, dbp=195.0, map=215.0),
    # Manual table 3-2 rows 5-7. Headroom for these is large (target stays 275),
    # so the interesting number there is not clearance but the very low MAP.
    'standard060_030': dict(number=5, sbp=60.0, dbp=30.0, map=40.0),
    'standard080_050': dict(number=6, sbp=80.0, dbp=50.0, map=60.0),
    'standard100_065': dict(number=7, sbp=100.0, dbp=65.0, map=76.0),
}

INTERVAL_S = 0.025
SKIP_START_S = 2.0
MIN_PRESSURE = 20.0
MAP_SMOOTHING_S = 2.0
FLOOR_MMHG = 20.0


def rolling_median(values, window):
    window = max(3, int(window) | 1)
    half = window // 2
    out = np.empty_like(values)
    for i in range(len(values)):
        out[i] = np.median(values[max(0, i - half): i + half + 1])
    return out


def measure(path, panel_sbp):
    cap = reference_bp.load(path)
    pressure = np.array(cap['pressure'])
    smooth = np.array([v if v is not None else 0.0 for v in cap['smooth']])
    first = int(round(SKIP_START_S / INTERVAL_S))
    usable = [i for i in range(first, len(pressure))
              if pressure[i] >= MIN_PRESSURE and smooth[i] > 0.0]
    if len(usable) < 50:
        return None
    peak_series = rolling_median(smooth, MAP_SMOOTHING_S / INTERVAL_S)
    map_index = max(usable, key=lambda i: peak_series[i])
    level = peak_series[map_index]

    above = sum(1 for i in range(first, len(pressure)) if pressure[i] > panel_sbp)
    return dict(
        export=Path(path).name,
        start_mmhg=round(float(pressure[first]), 1),
        headroom_mmhg=round(float(pressure[first]) - panel_sbp, 1),
        seconds_above_sbp=round(above * INTERVAL_S, 1),
        envelope_at_start_percent=round(float(smooth[first] / level) * 100.0, 1),
        map_mmhg=round(float(pressure[map_index]), 1),
        duration_s=round(float(cap['duration_s']), 1),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exports', nargs='*')
    ap.add_argument('--all', action='store_true',
                    help='every PEAK_WINDOW_20261105 export under data/raw')
    args = ap.parse_args()

    paths = args.exports
    if args.all:
        paths = sorted(glob.glob(str(ROOT / 'data' / 'raw' / '**' / '*.export.ndjson'),
                                 recursive=True))

    grouped = {}
    for path in paths:
        name = os.path.basename(path)
        key = next((k for k in PRESETS if name.startswith(k)), None)
        if key is None:
            continue
        try:
            cap = reference_bp.load(path)
        except Exception:                                  # noqa: BLE001
            continue
        if cap['firmware'] != 'PEAK_WINDOW_20261105':
            continue
        row = measure(path, PRESETS[key]['sbp'])
        if row:
            grouped.setdefault(key, []).append(row)

    print(f"{'preset':>14} {'n':>3} {'panel SBP':>9} {'deflate start':>13} "
          f"{'headroom':>9} {'env@start':>10} {'sec>SBP':>8}")
    for key in PRESETS:
        rows = grouped.get(key, [])
        if not rows:
            continue
        panel = PRESETS[key]
        starts = [r['start_mmhg'] for r in rows]
        head = [r['headroom_mmhg'] for r in rows]
        env = [r['envelope_at_start_percent'] for r in rows]
        secs = [r['seconds_above_sbp'] for r in rows]
        print(f"{key:>14} {len(rows):>3} {panel['sbp']:>9.0f} "
              f"{np.median(starts):>13.0f} {np.median(head):>9.0f} "
              f"{np.median(env):>9.0f}% {np.median(secs):>7.1f}s")

    print()
    print('reading: headroom is the distance from where deflation starts to the panel SBP,')
    print('so it bounds how much data exists in the region where the envelope must be low.')
    print('Preset 4 has almost none, which is why its SBP crossing sits in the first seconds.')


if __name__ == '__main__':
    main()
