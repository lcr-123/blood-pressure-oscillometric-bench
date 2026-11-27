"""Bound the pressure axis against the reference instrument's own specification.

What this does
    Reads `tools/bp_static_crosscheck.py` output files (two independent pressure
    channels measured at sealed hold points) and turns them into the one number a
    paper can actually state: the worst-case disagreement plus the reference's
    uncertainty.

Why no third instrument
    Metrology does not require a "true" reference, only a traceable specification
    on the comparison standard. BP Pump 2 (standard accuracy version) is specified
    at 0-300 mmHg as +/-0.5% of reading +/-1 mmHg, and both channels look at the
    same sealed node, so their measured disagreement can be compared against that
    specification directly. See data/reports/pressure_axis_accuracy_20261111.md.

Two difference conventions, and why both are reported
    The capture tool stores `difference_mmhg` as the mean of the per-window
    differences (bp_static_crosscheck.py:269), while `mcu_mmhg` and `tester_mmhg`
    are medians of the same windows. Those do not satisfy
    difference == tester - mcu; on the 2026-11-10 data they differ by up to
    0.37 mmHg, which moves the fitted slope from -0.99 +/- 0.17 pp (stored field)
    to -0.98 +/- 0.09 pp (medians). Both are correct; quoting either without
    naming the convention invites a contradiction later. The bound itself is
    reported from whichever convention gives the larger number.

Which points to include
    Two of the 2026-11-10 sweeps waited only 6 s before sampling, so they still
    contain compression heat and are not static points -- `--settle-min 10`
    drops them. The high-pressure points added on 2026-11-11 (236-265 mmHg) were
    only reachable with a short hold, so they carry a real pressure drift; they
    are kept, but `--max-drift` is available to exclude points that were still
    falling fast. The recommended call is `--settle-min 8 --max-drift 0.3`: it
    keeps the sweep requested at 272/275 mmHg (which reached 264.9) and drops the
    one 194 mmHg point that was still settling at 0.49 mmHg/s. Across the useful
    subsets the bound stays inside 4.8-6.1 mmHg and the slope inside
    -0.85..-1.04 pp/100, which is the point of running more than one subset.
    Without the drift filter the bound is 6.1 rather than 5.7, because that one
    unsettled point is the worst point in the set.

Usage:
    python tools/pressure_axis_bound.py --settle-min 8 --max-drift 0.3 "data/reports/static_crosscheck_*.json"
    python tools/pressure_axis_bound.py --settle-min 10 "data/reports/static_crosscheck_*.json"
    python tools/pressure_axis_bound.py --settle-min 90 "data/reports/static_crosscheck_*.json"
    python tools/pressure_axis_bound.py --json out.json --settle-min 8 --max-drift 0.3 "data/reports/static_crosscheck_*.json"
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

# BP Pump 2 standard accuracy version, 0-300 mmHg (Operators Manual, specifications).
SPEC_FRACTION = 0.005
SPEC_FLOOR_MMHG = 1.0
SPEC_MAX_MMHG = 300.0

CONVENTIONS = ("median", "stored")


def spec_mmhg(reading: float) -> float:
    """Reference instrument uncertainty at a given reading."""
    return SPEC_FRACTION * abs(reading) + SPEC_FLOOR_MMHG


def _slope_stats(xs: list[float], ys: list[float]) -> dict:
    """Least-squares fit y = a*x + b with the slope's standard error."""
    n = len(xs)
    if n < 3:
        raise SystemExit(f'need at least 3 points to fit, got {n}')
    mx = statistics.fmean(xs)
    my = statistics.fmean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0.0:
        raise SystemExit('all points share one pressure; cannot fit a slope')
    a = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    b = my - a * mx
    residuals = [y - (a * x + b) for x, y in zip(xs, ys)]
    ss_res = sum(r * r for r in residuals)
    ss_tot = sum((y - my) ** 2 for y in ys)
    dof = n - 2
    s2 = ss_res / dof if dof > 0 else float('nan')
    se_a = math.sqrt(s2 / sxx) if dof > 0 else float('nan')
    # two-sided 95% t quantile, small table -- n is never large here
    t95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
           7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}.get(dof, 1.96)
    return dict(
        n=n,
        slope_pp_per_100=round(a * 100.0, 4),
        slope_se_pp=round(se_a * 100.0, 4),
        slope_ci95_pp=round(t95 * se_a * 100.0, 4),
        intercept_mmhg=round(b, 4),
        r2=round(1.0 - ss_res / ss_tot, 6) if ss_tot else None,
        resid_max_abs=round(max(abs(r) for r in residuals), 4),
        resid_sd=round(statistics.stdev(residuals), 4) if n > 2 else None,
        residuals=[round(r, 4) for r in residuals],
    )


def row_drift_mmhg_s(row: dict, window_seconds: float) -> float | None:
    """How fast the loop was still falling during the hold, in mmHg/s.

    Each point holds `repeats` windows back to back; `mcu_first` and `mcu_last`
    are the first and last sample of a window. A point that was still bleeding
    down when it was measured gives a disagreement that is not a static one, so
    this is worth reporting next to the difference.
    """
    windows = row.get('windows') or []
    if len(windows) < 2:
        return None
    span = (len(windows) - 1) * window_seconds + window_seconds
    drop = windows[0]['mcu_first'] - windows[-1]['mcu_last']
    return drop / span if span > 0 else None


def load_points(paths: list[Path],
                max_drift: float | None = None,
                settle_min: float | None = None) -> tuple[list[dict], list[dict]]:
    """Flatten every crosscheck report into one point per row.

    Returns (kept, dropped). `dropped` fills up when `max_drift` or `settle_min`
    rejects a point, so the caller can say exactly what was left out and why.
    """
    points, dropped = [], []
    for path in paths:
        data = json.loads(path.read_text(encoding='utf-8'))
        window_seconds = data.get('window_seconds') or 12.0
        settle = data.get('settle_seconds')
        for row in data.get('rows', []):
            mcu = row.get('mcu_mmhg')
            tester = row.get('tester_mmhg')
            if mcu is None or tester is None:
                continue
            drift = row_drift_mmhg_s(row, window_seconds)
            point = dict(
                source=path.name,
                settle_seconds=settle,
                requested_mmhg=row.get('requested_mmhg'),
                mcu_mmhg=mcu,
                tester_mmhg=tester,
                stored_diff_mmhg=row.get('difference_mmhg'),
                drift_mmhg_s=None if drift is None else round(drift, 4),
            )
            if settle_min is not None and (settle is None or settle < settle_min):
                point['drop_reason'] = (
                    f'settled only {settle if settle is not None else "unknown"} s')
                dropped.append(point)
            elif max_drift is not None and drift is not None and abs(drift) > max_drift:
                point['drop_reason'] = f'still falling at {drift:+.3f} mmHg/s'
                dropped.append(point)
            else:
                points.append(point)
    points.sort(key=lambda p: p['mcu_mmhg'])
    dropped.sort(key=lambda p: p['mcu_mmhg'])
    return points, dropped


def analyse(points: list[dict], dropped: list[dict] | None = None) -> dict:
    """Evaluate every convention and keep the worse bound."""
    if len(points) < 3:
        raise SystemExit(f'need at least 3 points, got {len(points)}')

    xs = [p['mcu_mmhg'] for p in points]
    by_convention = {}
    for convention in CONVENTIONS:
        diffs = []
        for p in points:
            if convention == 'median':
                diffs.append(p['tester_mmhg'] - p['mcu_mmhg'])
            else:
                stored = p['stored_diff_mmhg']
                if stored is None:
                    raise SystemExit(
                        f"{p['source']} has no difference_mmhg; the 'stored' "
                        'convention needs it')
                diffs.append(stored)
        stats = _slope_stats(xs, diffs)
        worst_total = max(abs(d) + spec_mmhg(p['tester_mmhg'])
                          for d, p in zip(diffs, points))
        inside = sum(1 for d, p in zip(diffs, points)
                     if abs(d) <= spec_mmhg(p['tester_mmhg']))
        ratios = [abs(d) / spec_mmhg(p['tester_mmhg'])
                  for d, p in zip(diffs, points)]
        by_convention[convention] = dict(
            differences=[round(d, 4) for d in diffs],
            fit=stats,
            within_spec=f'{inside}/{len(points)}',
            worst_ratio=round(max(ratios), 4),
            worst_total_mmhg=round(worst_total, 4),
        )

    worst_conv = max(by_convention,
                     key=lambda c: by_convention[c]['worst_total_mmhg'])
    worst = by_convention[worst_conv]

    table = []
    for p, d_median, d_stored in zip(points,
                                     by_convention['median']['differences'],
                                     by_convention['stored']['differences']):
        spec = spec_mmhg(p['tester_mmhg'])
        table.append(dict(
            mcu_mmhg=p['mcu_mmhg'],
            tester_mmhg=p['tester_mmhg'],
            settle_seconds=p.get('settle_seconds'),
            drift_mmhg_s=p.get('drift_mmhg_s'),
            diff_median_mmhg=round(d_median, 2),
            diff_stored_mmhg=round(d_stored, 2),
            spec_mmhg=round(spec, 2),
            ratio_median=round(abs(d_median) / spec, 4),
            ratio_stored=round(abs(d_stored) / spec, 4),
            worst_total_median_mmhg=round(abs(d_median) + spec, 4),
            worst_total_stored_mmhg=round(abs(d_stored) + spec, 4),
        ))

    pressure_span = (min(p['mcu_mmhg'] for p in points),
                     max(p['mcu_mmhg'] for p in points))
    tester_span = (min(p['tester_mmhg'] for p in points),
                   max(p['tester_mmhg'] for p in points))
    return dict(
        points=len(points),
        sources=sorted({p['source'] for p in points}),
        pressure_span_mmhg=[round(pressure_span[0], 2),
                            round(pressure_span[1], 2)],
        tester_span_mmhg=[round(tester_span[0], 2), round(tester_span[1], 2)],
        span_within_spec=pressure_span[1] <= SPEC_MAX_MMHG,
        excluded_points=dropped or [],
        by_convention=by_convention,
        worst_convention=worst_conv,
        table=table,
        declaration=(
            f"Pressure axis, {pressure_span[0]:.0f}-{pressure_span[1]:.0f} mmHg: "
            f"worst case no more than +/-{worst['worst_total_mmhg']:.1f} mmHg "
            f"(reference BP Pump 2, specified +/-0.5% of reading +/-1 mmHg); "
            f"under that convention {worst['within_spec']} points sit inside the "
            f"specification and the worst is {worst['worst_ratio']:.2f}x it. "
            f"The other convention ({'median' if worst_conv == 'stored' else 'stored'}) "
            f"gives "
            f"{by_convention['median' if worst_conv == 'stored' else 'stored']['worst_total_mmhg']:.1f} "
            f"mmHg."
        ),
        caveats=[
            'This is agreement with BP Pump 2, not absolute truth: the reference '
            'carries its own specification.',
            'Static and slow-ramp pressures only. The reference channel runs at '
            'about 1.9 Hz here, under two samples per beat, so per-beat waveforms '
            'cannot be checked this way.',
            'The calibration was fitted over 0-235 mmHg; acquisition runs to 275. '
            'Points above 235 rest on that slope extrapolated, and they were only '
            'reachable with a short hold (8-20 s), so 268-275 mmHg still has no '
            'measurement at all.',
            'Temperature drift, pressure hysteresis and long-term offset stability '
            'are unmeasured.',
        ],
    )


def expand(specs: list[str]) -> list[Path]:
    """Accept globs as well as plain paths, because PowerShell does not expand them
    when they are handed to a native command."""
    out: list[Path] = []
    for spec in specs:
        if any(ch in spec for ch in '*?['):
            import glob as _glob
            hits = sorted(Path(p) for p in _glob.glob(spec))
            if not hits:
                raise SystemExit(f'no file matches {spec}')
            out.extend(hits)
        else:
            out.append(Path(spec))
    seen, unique = set(), []
    for path in out:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description='Bound the pressure axis from the reference specification.')
    ap.add_argument('paths', nargs='+',
                    help='static_crosscheck_*.json files or globs')
    ap.add_argument('--json', type=Path, help='write the full analysis here')
    ap.add_argument('--max-drift', type=float, default=None, metavar='MMHG_S',
                    help='drop points whose hold was still falling faster than '
                         'this, e.g. 0.2')
    ap.add_argument('--settle-min', type=float, default=None, metavar='SECONDS',
                    help='drop sweeps that waited less than this before sampling; '
                         'the 6 s sweeps from 2026-11-10 are still full of '
                         'compression heat, use 90')
    args = ap.parse_args(argv)

    paths = expand(args.paths)
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        raise SystemExit(f'no such file(s): {missing}')

    points, dropped = load_points(paths, args.max_drift, args.settle_min)
    result = analyse(points, dropped)
    result['max_drift_mmhg_s'] = args.max_drift
    result['settle_min_seconds'] = args.settle_min

    print(f"points {result['points']}  MCU span "
          f"{result['pressure_span_mmhg'][0]:.1f}-"
          f"{result['pressure_span_mmhg'][1]:.1f} mmHg  (Tester "
          f"{result['tester_span_mmhg'][0]:.1f}-"
          f"{result['tester_span_mmhg'][1]:.1f} mmHg)")
    print(f"sources {', '.join(result['sources'])}")
    if dropped:
        print(f"dropped {len(dropped)} point(s):")
        for p in dropped:
            print(f"  {p['mcu_mmhg']:7.2f} mmHg from {p['source']}: {p['drop_reason']}")
    print()
    header = (f"{'MCU':>8} {'Tester':>8} {'drift/s':>8} {'diff(med)':>10} "
              f"{'diff(stored)':>13} {'spec':>7} {'worst':>7}")
    print(header)
    print('-' * len(header))
    for row in result['table']:
        # the bound takes the larger of the two conventions at every point, so
        # the displayed worst total and the OUT flag use the same choice
        worst_total = max(row['worst_total_median_mmhg'],
                          row['worst_total_stored_mmhg'])
        ratio = max(row['ratio_median'], row['ratio_stored'])
        flag = '' if ratio <= 1.0 else '  OUT'
        drift = row.get('drift_mmhg_s')
        drift_text = f'{drift:+8.3f}' if drift is not None else f'{"n/a":>8}'
        print(f"{row['mcu_mmhg']:8.2f} {row['tester_mmhg']:8.2f} {drift_text} "
              f"{row['diff_median_mmhg']:+10.2f} {row['diff_stored_mmhg']:+13.2f} "
              f"{row['spec_mmhg']:7.2f} {worst_total:7.2f}{flag}")
    print("\n'worst' = |diff| + spec, taking the larger of the two conventions; "
          "OUT marks the points where the difference alone exceeds the "
          "reference's specification.")
    print()
    for convention, block in result['by_convention'].items():
        fit = block['fit']
        print(f"[{convention}] slope {fit['slope_pp_per_100']:+.4f} pp/100 mmHg "
              f"(SE {fit['slope_se_pp']:.4f}, 95% CI +/-{fit['slope_ci95_pp']:.3f}), "
              f"intercept {fit['intercept_mmhg']:+.4f}, R2 {fit['r2']}")
        print(f"{'':>{len(convention) + 2}} within spec {block['within_spec']}, "
              f"worst {block['worst_ratio']:.2f}x, "
              f"residual max {fit['resid_max_abs']:.3f} sd {fit['resid_sd']:.3f}, "
              f"worst total {block['worst_total_mmhg']:.2f} mmHg")
    print()
    print(f"worst convention: {result['worst_convention']}")
    print()
    print(result['declaration'])
    print()
    for caveat in result['caveats']:
        print(f'  - {caveat}')

    if args.json:
        args.json.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                             encoding='utf-8')
        print(f'\nwrote {args.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
