"""How many times does the DBP threshold get crossed? Identifiability, not accuracy.

The question this answers is not "how do we make DBP better". It is "is the DBP crossing
point even uniquely defined on this fixture". The oscillometric ratio method assumes the
envelope descends monotonically, crosses the 0.6x level once, and that crossing is DBP.
On this rig the smoothed envelope under MAP is noisy enough that the level is crossed
twenty to forty times, so "the first 3 consecutive samples below the threshold" is a pick
among dozens of candidates, and a small perturbation can move it by 20-30 mmHg.

Output per file: MAP pressure, threshold, the number of disjoint below-threshold regions,
where the first sustained crossing lands, and what fraction of the lower limb sits below
the threshold. High region counts mean the crossing is an artefact of where the dip
happens to be deep enough, not a measurement of the arterial pressure-volume relation.

Usage:
    python tools/dbp_identifiability.py <export.ndjson> [more exports...]
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reference_bp  # noqa: E402

INTERVAL_S = 0.025
SKIP_START_S = 2.0
MIN_PRESSURE = 20.0
DBP_RATIO = 0.6
SUSTAINED = 3
MAP_SMOOTHING_S = 2.0


def rolling_median(values, window):
    window = max(3, int(window) | 1)
    half = window // 2
    out = np.empty_like(values)
    for i in range(len(values)):
        out[i] = np.median(values[max(0, i - half): i + half + 1])
    return out


def analyse(path):
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
    threshold = DBP_RATIO * level

    lower = [i for i in usable if i > map_index]
    below = np.array([smooth[i] <= threshold for i in lower])
    regions = 0
    previous = False
    for flag in below:
        if flag and not previous:
            regions += 1
        previous = flag

    crossing = None
    for k in range(len(lower) - SUSTAINED):
        if all(below[k + j] for j in range(SUSTAINED)):
            crossing = lower[k]
            break

    return dict(
        export=Path(path).name,
        n=cap['n'],
        map_mmhg=round(float(pressure[map_index]), 2),
        threshold_mv=round(float(threshold) * 1000.0, 3),
        below_regions=int(regions),
        first_crossing_mmhg=round(float(pressure[crossing]), 2) if crossing else None,
        fraction_below_percent=round(float(below.mean()) * 100.0, 1) if len(below) else None,
        lower_limb_points=int(len(lower)),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exports', nargs='+')
    args = ap.parse_args()

    print(f"{'export':>48} {'MAP':>7} {'thr_mV':>7} {'regions':>8} "
          f"{'first_DBP':>10} {'below_%':>8}")
    for path in args.exports:
        try:
            row = analyse(path)
        except Exception as exc:                            # noqa: BLE001
            print(f'{Path(path).name:>48}  failed: {exc}')
            continue
        if row is None:
            print(f'{Path(path).name:>48}  too few usable points')
            continue
        first = f"{row['first_crossing_mmhg']:.1f}" if row['first_crossing_mmhg'] else 'none'
        print(f"{row['export'][-48:]:>48} {row['map_mmhg']:>7.1f} {row['threshold_mv']:>7.2f} "
              f"{row['below_regions']:>8} {first:>10} "
              f"{row['below_percent'] if 'below_percent' in row else row['fraction_below_percent']:>8.1f}")


if __name__ == '__main__':
    main()
