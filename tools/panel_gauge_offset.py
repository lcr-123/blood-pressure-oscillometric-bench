"""Pair the Tester's panel reading with its RS-232 `[GAUGE]` reading at the same instant.

The question
    2026-10-25 calibrated the MCU against the panel's `Measured` number. Every
    cross-check since 2026-11-10 compares against the RS-232 `[GAUGE]` string. If those
    two display paths differ by about 1%, then part of the -0.97 %/100 scale difference
    is a display-path offset instead of a sensor offset. `tools/panel_vs_gauge.py`
    records the raw material; this pairs it up.

How the pairing works
    The operator reads a whole number off the panel at some moment the script cannot
    observe. But it does not need to: the panel number is a pressure, and the MCU
    trace says at which instant the loop actually held that pressure. So for each
    reported number this searches the MCU `est` trace inside that point's window for
    the sample closest to the reported value, then looks up what `[GAUGE]` was
    reporting at that same wall clock.

    The offset that answers the question is `gauge - panel`. If the two display paths
    shared a value it would be zero. If the serial path is the one carrying the -1%
    scale error, it should come out near `-0.97% * pressure / 100`.

Why the whole window is searched, not a fixed lag
    An earlier version assumed the serial path lagged the MCU and compared at
    hand-picked lags. Measured on the third run, the gauge-minus-MCU spread is smallest
    at lag 0 (-1.75 mmHg at 150, -2.85 at 250, sd 0.30 in both). Shifting the serial
    trace later only widens the spread, so no lag correction is applied here; lag 0 is
    reported as a check.

Usage:
    python tools/panel_gauge_offset.py data/reports/panel_vs_gauge_20261111-212040.json \
        --panel 150:143,140 250:244,238

    Without --panel the script only reports the serial-path offset against the MCU and
    says what is missing.
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GAUGE_WINDOW_MS = 1200.0     # one `[GAUGE]` poll cycle is about 0.85 s, so allow one
MATCH_TOLERANCE_MMHG = 1.2   # a whole-number panel read cannot be pinned tighter
LAG_SWEEP_S = (-4, -2, -1, 0, 1, 2, 4, 8)


def load_report(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def parse_panel(specs):
    """`['150:143,140', '250:244,238']` -> {150: [143.0, 140.0], 250: [244.0, 238.0]}."""
    table = {}
    for spec in specs or []:
        head, _, tail = spec.partition(':')
        values = [float(v) for v in tail.replace(' ', '').split(',') if v]
        table[int(head)] = values
    return table


def value_at(trace, when_ms, window_ms=GAUGE_WINDOW_MS):
    near = [v for t, v in trace if abs(t - when_ms) <= window_ms]
    if not near:
        return None, 0
    return statistics.median(near), len(near)


def mcu_at(trace, when_ms, window_ms=120.0):
    near = [v for t, v in trace if abs(t - when_ms) <= window_ms]
    return (statistics.median(near) if near else None), len(near)


def match_panel_value(row, reported):
    """Find the instant the MCU held `reported` mmHg, inside this row's window."""
    trace = row.get('mcu_trace') or []
    if not trace:
        return None
    best = min(trace, key=lambda pair: abs(pair[1] - reported))
    when_ms, mcu = best
    if abs(mcu - reported) > MATCH_TOLERANCE_MMHG:
        return None
    return when_ms, mcu


def serial_offset(row, mcu_trace, gauge_trace):
    """gauge - mcu over the hold, at several lags. Lag 0 should minimise the spread."""
    if not mcu_trace or not gauge_trace:
        return []
    out = []
    for lag in LAG_SWEEP_S:
        diffs = []
        for t, v in gauge_trace:
            m, _ = mcu_at(mcu_trace, t - lag * 1000.0)
            if m is not None:
                diffs.append(v - m)
        if len(diffs) >= 5:
            out.append(dict(lag_s=lag, n=len(diffs),
                            median_mmhg=round(statistics.median(diffs), 2),
                            sd_mmhg=round(statistics.pstdev(diffs), 2)))
    return out


def analyse(report, panel):
    rows = []
    for row in report.get('rows', []):
        point = row['requested_mmhg']
        readings = panel.get(point)
        if readings is None and row.get('operator_panel_value') is not None:
            readings = [float(row['operator_panel_value'])]
        gauge_trace = row.get('gauge_trace') or []
        mcu_trace = row.get('mcu_trace') or []
        entry = dict(requested_mmhg=point,
                     panel_values=readings,
                     lags=serial_offset(row, mcu_trace, gauge_trace),
                     pairs=[])
        for reported in readings or []:
            hit = match_panel_value(row, reported)
            if hit is None:
                entry['pairs'].append(dict(panel=reported, matched=False,
                                           why='no MCU sample within '
                                               f'{MATCH_TOLERANCE_MMHG} mmHg of '
                                               f'{reported:g} in this window'))
                continue
            when_ms, mcu = hit
            gauge, gauge_n = value_at(gauge_trace, when_ms)
            pairs = dict(panel=reported, matched=True,
                         mcu_at_match_mmhg=round(mcu, 2),
                         seconds_after_pump_stop=round(
                             (when_ms - row['stop_ms']) / 1000.0, 2)
                         if row.get('stop_ms') else None,
                         gauge_at_match_mmhg=round(gauge, 2) if gauge is not None else None,
                         gauge_points_at_match=gauge_n,
                         gauge_minus_panel=round(gauge - reported, 2)
                         if gauge is not None else None,
                         gauge_minus_mcu=round(gauge - mcu, 2)
                         if gauge is not None else None)
            entry['pairs'].append(pairs)
        rows.append(entry)

    offsets = [p['gauge_minus_panel'] for row in rows for p in row['pairs']
               if p.get('gauge_minus_panel') is not None]
    lag0 = [lag for row in rows for lag in row['lags'] if lag['lag_s'] == 0]
    result = dict(
        source=str(report.get('started')),
        points=[row['requested_mmhg'] for row in rows],
        rows=rows,
        panel_pairs=len(offsets),
        gauge_minus_panel_median=round(statistics.median(offsets), 2) if offsets else None,
        gauge_minus_panel_range=[round(min(offsets), 2), round(max(offsets), 2)]
        if offsets else None,
        serial_lag0_median=round(statistics.median([x['median_mmhg'] for x in lag0]), 2)
        if lag0 else None,
    )
    if not offsets:
        result['verdict'] = ('no panel values paired, so the display-path question is '
                             'still open; the serial trace alone gives only the offset '
                             'against the MCU')
    else:
        result['verdict'] = (
            'gauge minus panel is '
            f'{result["gauge_minus_panel_median"]:+.2f} mmHg over '
            f'{result["panel_pairs"]} reading(s)')
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('report', help='a panel_vs_gauge_*.json written by the recorder')
    ap.add_argument('--panel', nargs='*', default=None,
                    help='panel readings as POINT:VALUE[,VALUE] e.g. 150:143,140')
    ap.add_argument('--json', help='also write the analysis here')
    args = ap.parse_args()

    report = load_report(args.report)
    result = analyse(report, parse_panel(args.panel))
    result['report'] = str(Path(args.report))

    print(f"source {result['source']}   points {result['points']}")
    for row in result['rows']:
        print(f"\n=== {row['requested_mmhg']} mmHg "
              f"(panel {row['panel_values']})")
        if row['lags']:
            spread_best = min(row['lags'], key=lambda x: x['sd_mmhg'])
            print(f"  serial path vs MCU: lag 0 median "
                  f"{[x['median_mmhg'] for x in row['lags'] if x['lag_s'] == 0][0]:+.2f} "
                  f"mmHg, smallest spread at lag {spread_best['lag_s']:+d} s")
        for pair in row['pairs']:
            if not pair['matched']:
                print(f"  panel {pair['panel']:6.1f}  UNMATCHED: {pair['why']}")
                continue
            after = pair['seconds_after_pump_stop']
            when = f'{after:+.2f} s after the pump stopped' if after is not None else ''
            if pair['gauge_at_match_mmhg'] is None:
                print(f"  panel {pair['panel']:6.1f}  mcu {pair['mcu_at_match_mmhg']:6.2f}"
                      f"  {when}   no gauge sample there")
            else:
                print(f"  panel {pair['panel']:6.1f}  mcu {pair['mcu_at_match_mmhg']:6.2f}"
                      f"  {when}   gauge {pair['gauge_at_match_mmhg']:6.1f}"
                      f" ({pair['gauge_points_at_match']} pts)"
                      f"   gauge-panel {pair['gauge_minus_panel']:+.2f}")

    print(f"\nverdict: {result['verdict']}")
    if result['gauge_minus_panel_range']:
        print(f"  range {result['gauge_minus_panel_range'][0]:+.2f} .. "
              f"{result['gauge_minus_panel_range'][1]:+.2f} mmHg")
    if result['serial_lag0_median'] is not None:
        print(f"  serial path alone sits {result['serial_lag0_median']:+.2f} mmHg "
              f"from the MCU at lag 0")

    if args.json:
        out = ROOT / args.json
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                       encoding='utf-8')
        print(f"\nwrote {args.json}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
