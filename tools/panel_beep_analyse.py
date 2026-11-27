"""Pair the operator's beep-cued panel readings with the two traces, and say who agrees.

Why this exists
    `tools/panel_beep_hold.py` produces a report with a `cues` list: one entry per beep,
    each carrying the `[GAUGE]` median and the MCU `est` median for that instant. The
    operator reports the panel number for each beep in order. This script puts the three
    columns side by side and decides whether the panel follows the serial path or the MCU
    path. That decision is the whole point of the experiment: the 2026-10-25 calibration
    used the panel, every cross-check since 2026-11-10 uses `[GAUGE]`, so if the two
    display paths differed by about 1% then part of the -0.97 %/100 scale difference would
    be a display artefact rather than a sensor one.

How to read the output
    `panel - serial` near zero means the panel and the stored JSON string are the same
    number, i.e. one display path. The residual is bounded by the panel's 1 mmHg
    resolution, so a median of 0.00 with an occasional -1.00 is the expected signature of
    "same number, rounded". `panel - mcu` is then just the serial-versus-MCU offset seen
    through the panel, and should match the dense `serial - MCU` block below it.

Usage:
    python tools/panel_beep_analyse.py data/reports/panel_beep_20261111-220931.json \
        --panel 232,226,223,221,220,218 --json data/reports/panel_beep_offset_20261111.json
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def summarise(values):
    if not values:
        return None
    return dict(n=len(values), median=round(statistics.median(values), 2),
                mean=round(statistics.fmean(values), 2),
                sd=round(statistics.pstdev(values), 2),
                min=round(min(values), 2), max=round(max(values), 2))


def pairs_against_mcu(report, window_ms=200.0):
    """Every `[GAUGE]` sample after the pump stop, minus the MCU median at that instant."""
    stop = report['stop_ms']
    mcu = report['mcu_trace']
    out = []
    for t, value in report['gauge_trace']:
        if t < stop:
            continue
        near = [v for tt, v in mcu if abs(tt - t) <= window_ms]
        if near:
            out.append((round((t - stop) / 1000.0, 2), value - statistics.median(near)))
    return out


def analyse(report, panel):
    cues = report.get('cues') or []
    if len(panel) != len(cues):
        raise SystemExit(f'the report has {len(cues)} cues but {len(panel)} panel values '
                         f'were given; they have to match one for one')
    rows = []
    for cue, value in zip(cues, panel):
        rows.append(dict(index=cue['index'],
                         after_pump_stop_s=cue['after_pump_stop_s'],
                         mcu_mmhg=cue['mcu_mmhg'],
                         gauge_mmhg=cue['gauge_mmhg'],
                         panel_mmhg=value,
                         panel_minus_mcu=round(value - cue['mcu_mmhg'], 2),
                         panel_minus_gauge=round(value - cue['gauge_mmhg'], 2)))
    dense = pairs_against_mcu(report)
    panel_minus_gauge = [r['panel_minus_gauge'] for r in rows]
    panel_minus_mcu = [r['panel_minus_mcu'] for r in rows]
    serial_minus_mcu = [d for _, d in dense]

    exact = sum(1 for d in panel_minus_gauge if abs(d) < 0.5)
    verdict = None
    if abs(statistics.median(panel_minus_gauge)) <= 0.5:
        verdict = ('the panel and the [GAUGE] string are the same number: the display '
                   'path is not a separate measurement. The scale difference measured '
                   'against the Tester lives in its sensor, not in how the number is shown.')
    elif abs(statistics.median(panel_minus_mcu)) <= 0.5:
        verdict = ('the panel follows the MCU, not the [GAUGE] string: the serial path '
                   'would then be a re-scaled copy, and part of the -0.97 %/100 would be '
                   'a display-path artefact.')
    return dict(report=report.get('started'), point_mmhg=report.get('point_mmhg'),
                rows=rows,
                panel_minus_gauge=summarise(panel_minus_gauge),
                panel_minus_mcu=summarise(panel_minus_mcu),
                panel_equals_gauge_count=f'{exact}/{len(rows)}',
                serial_minus_mcu_dense=summarise(serial_minus_mcu),
                verdict=verdict)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('report', help='data/reports/panel_beep_*.json')
    ap.add_argument('--panel', required=True,
                    help='comma separated panel readings in cue order, e.g. 232,226,223,221,220,218')
    ap.add_argument('--json', help='write the analysis here')
    args = ap.parse_args()

    path = Path(args.report)
    if not path.is_absolute():
        path = ROOT / path
    report = json.loads(path.read_text(encoding='utf-8'))
    panel = [float(v) for v in args.panel.split(',') if v.strip()]
    result = analyse(report, panel)

    print(f"report {path.name}   point {result['point_mmhg']} mmHg")
    print(f"{'cue':>3} {'after stop':>11} {'MCU':>8} {'serial':>8} {'panel':>7} "
          f"{'panel-MCU':>10} {'panel-serial':>13}")
    for row in result['rows']:
        print(f"{row['index']:>3} {row['after_pump_stop_s']:>10.2f}s {row['mcu_mmhg']:>8.2f} "
              f"{row['gauge_mmhg']:>8.1f} {row['panel_mmhg']:>7.0f} "
              f"{row['panel_minus_mcu']:>+10.2f} {row['panel_minus_gauge']:>+13.2f}")
    for key, label in (('panel_minus_gauge', 'panel - serial'),
                       ('panel_minus_mcu', 'panel - MCU'),
                       ('serial_minus_mcu_dense', 'serial - MCU (whole hold)')):
        stats = result[key]
        if stats:
            print(f"{label:>26}: median {stats['median']:+.2f}  mean {stats['mean']:+.2f}  "
                  f"sd {stats['sd']:.2f}  range {stats['min']:+.2f}..{stats['max']:+.2f}  "
                  f"n={stats['n']}")
    print(f"panel == serial exactly: {result['panel_equals_gauge_count']}")
    print(f"verdict: {result['verdict']}")

    if args.json:
        out = Path(args.json)
        if not out.is_absolute():
            out = ROOT / out
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'wrote {out.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
