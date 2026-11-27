"""Compute the loop gas volume from a three-plateau syringe run, offline.

Run after tmp/syringe_volume_20261109.py has finished:

    python tmp/syringe_analyze_20261109.py <name> [--g1 0] [--g2 9] [--g3 18]

Why offline, and why nothing here trusts a human clock. Four earlier attempts failed for the same
reason each time: the instant a pressure was written down drifted away from the instant the plunger
actually moved. At 6.5 mmHg/min a 20 s gap is 2 mmHg, which is 5 percent of a 40 mmHg step and
therefore 5 percent of the volume. The bridge log carries a timestamp on every pressure line, so
both plateaus are fitted as straight lines and evaluated at one common instant. The human never
supplies a pressure.

The physics, P absolute in mmHg, g the plunger graduation in mL, one closed volume of gas:

    P1_abs * (V + g1) = P2_abs * (V + g2)
    V = (P2_abs * g2 - P1_abs * g1) / (P1_abs - P2_abs)

Between two plateaus the moles and the temperature are unchanged (that is why the script waits 90 s
for the compression heat to dissipate). The leak is not wished away: it is a constant slope on each
plateau, so it is fitted and then removed by evaluating both fits at the same instant.

Pull instants are found in the pressure trace itself, not taken from the operator, so a mislabelled
event cannot corrupt the answer. Event times from the acquisition report are printed alongside as a
cross-check.
"""
import argparse
import json
import re
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OMNI = ROOT / 'tmp' / 'omniprobe'
ATM = 760.0
SLOPE = 81.529
INTERCEPT = -20.03
PRESSURE = re.compile(
    r'\[Pressure\] raw=(\d+) ads=(\d+)mV sensor=(\d+)mV est=([\d.]+)mmHg (VALID|UNCAL)')

TAIL_S = 25.0        # length of the fitted plateau tail before each pull
EDGE_S = 1.0         # keep clear of the pull itself

parser = argparse.ArgumentParser()
parser.add_argument('name')
parser.add_argument('--g1', type=float, default=None)
parser.add_argument('--g2', type=float, default=None)
parser.add_argument('--g3', type=float, default=None)
parser.add_argument('--json-out', default=None)
args = parser.parse_args()

log_path = OMNI / f'{args.name}.ndjson'
events_path = OMNI / f'{args.name}.events.json'
for path in (log_path, events_path):
    if not path.exists():
        raise SystemExit(f'missing {path}')

report = json.loads(events_path.read_text(encoding='utf-8'))
graduations = dict(report.get('graduations_ml', {}))
for key, value in (('g1', args.g1), ('g2', args.g2), ('g3', args.g3)):
    if value is not None:
        graduations[key] = value
g1 = float(graduations.get('g1', 0.0))
g2 = float(graduations.get('g2', 9.0))
g3 = float(graduations.get('g3', 18.0))

# --- samples straight from the bridge log ---------------------------------------
samples = []
with open(log_path, encoding='utf-8') as handle:
    for line in handle:
        line = line.strip()
        if not line.startswith('{'):
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get('type') != 'text':
            continue
        for entry in record.get('lines', []):
            match = PRESSURE.search(entry.get('text', ''))
            if not match:
                continue
            samples.append(dict(t=entry['timestamp'] / 1000.0,
                                raw=int(match.group(1)),
                                ads=int(match.group(2)),
                                sensor=int(match.group(3)),
                                est=float(match.group(4))))

if len(samples) < 200:
    raise SystemExit(f'only {len(samples)} pressure samples in {log_path.name}: the log is short')

samples.sort(key=lambda s: s['t'])
t = np.array([s['t'] for s in samples])
raw = np.array([s['raw'] for s in samples], dtype=float)
sensor = np.array([s['sensor'] for s in samples], dtype=float)
p = sensor / 1000.0 * SLOPE + INTERCEPT          # true pressure, bypassing the clamp at 0
t -= t[0]
print(f'log {log_path.name}: {len(samples)} samples over {t[-1]:.1f} s, '
      f'max gap {np.max(np.diff(t)):.3f} s')
print(f'pressure {p.min():.1f} .. {p.max():.1f} mmHg true (gauge)')
print()

# --- find the pulls in the trace -------------------------------------------------
# A pull is a step, not a slope: the plunger moves in a second or two, so the pressure falls tens of
# mmHg within half a second and then stays down. Comparing a 0.5 s trailing median against a 0.5 s
# median taken 1 s earlier is immune both to single-sample spikes and to the leak, which moves 0.05
# mmHg in that time.
def running_median(values, window):
    half = max(1, window // 2)
    padded = np.concatenate([values[:half][::-1], values, values[-half:][::-1]])
    return np.array([np.median(padded[i:i + window]) for i in range(len(values))])


smoothed = running_median(p, 9)          # 9 samples = 0.45 s at 20 Hz
lag = 20                                  # 1.0 s
pulls = []
for i in range(lag, len(smoothed)):
    drop = smoothed[i - lag] - smoothed[i]
    if drop < 12.0:
        continue
    if pulls and (t[i] - pulls[-1]) < 8.0:
        continue
    pulls.append(float(t[i]))
print(f'pulls detected in the trace: {len(pulls)}')
for i, when in enumerate(pulls, start=1):
    idx = int(np.searchsorted(t, when))
    before = p[max(0, idx - 40):idx]
    after = p[idx:idx + 40]
    print(f'  pull {i} at t = {when:6.1f} s: '
          f'{np.median(before) if len(before) else float("nan"):7.2f} -> '
          f'{np.median(after) if len(after) else float("nan"):7.2f} mmHg')
recorded = [e for e in report.get('events', []) if e.get('label', '').startswith('pull_')]
if recorded:
    t0_epoch = samples[0]['t']
    print('  report says the pulls were at: ' + ', '.join(
        f"{e['label']} t={e['t_before_ms'] / 1000.0 - t0_epoch:.1f} s" for e in recorded
        if 't_before_ms' in e))
print()

if not pulls:
    raise SystemExit('no pull found in the trace: nothing changed volume, so no equation exists')


def fit_tail(t_end, label):
    """Fit the last TAIL_S seconds before t_end, skipping EDGE_S to stay clear of the pull."""
    lo = t_end - TAIL_S
    hi = t_end - EDGE_S
    mask = (t >= lo) & (t <= hi)
    if mask.sum() < 100:
        raise SystemExit(f'{label}: only {mask.sum()} samples in [{lo:.1f}, {hi:.1f}] s')
    tt = t[mask]
    pp = p[mask]
    rr = raw[mask]
    slope, intercept = np.polyfit(tt, pp, 1)
    resid = pp - (slope * tt + intercept)
    # Hand noise is high frequency; the leak is a slope. Detrend the counts first, otherwise the
    # 25 s span of the leak (about 190 counts) dwarfs the noise and every plateau looks bad.
    raw_slope, raw_intercept = np.polyfit(tt, rr, 1)
    raw_resid = rr - (raw_slope * tt + raw_intercept)
    return dict(label=label, n=int(mask.sum()), t_lo=float(tt[0]), t_hi=float(tt[-1]),
                median=float(np.median(pp)), slope=float(slope), intercept=float(intercept),
                residual_sd=float(np.std(resid)),
                noise_p2p_counts=float(np.max(raw_resid) - np.min(raw_resid)),
                raw_span_counts=float(rr.max() - rr.min()))


# Evaluate every fit at one instant, so the leak cancels. The chosen instant is the start of the
# post-pull window: backward extrapolation is then zero and forward extrapolation stays small.
plateaus = []
instant = []
for i, when in enumerate(pulls):
    plateaus.append(fit_tail(when, f'before pull {i + 1}'))
for i in range(len(pulls)):
    lo = pulls[i] + EDGE_S
    hi = pulls[i + 1] - EDGE_S if i + 1 < len(pulls) else t[-1]
    centre = lo + (hi - lo) / 2.0
    instant.append((lo, hi, centre))

print('plateau fits (tail before each pull)')
for fit in plateaus:
    print(f'  {fit["label"]}: n={fit["n"]:4d}  median {fit["median"]:7.2f} mmHg  '
          f'rate {fit["slope"]:+.3f} mmHg/s  residual sd {fit["residual_sd"]:.2f} mmHg  '
          f'noise p2p {fit["noise_p2p_counts"]:.0f} counts')
print()

# --- quality gates ---------------------------------------------------------------
qc = []
for fit in plateaus:
    if fit['residual_sd'] > 1.0:
        qc.append(f'{fit["label"]}: residual {fit["residual_sd"]:.2f} mmHg is not a straight '
                  f'line, so the gas was still settling or the volume changed mid-window')
    # 25 counts detrended peak-to-peak = about 0.35 mmHg. Hands-off noise measures 11-19 counts over
    # 1.2 s here; a hand on the plunger was 332 counts. 25 sits clear of both.
    if fit['noise_p2p_counts'] > 25.0:
        qc.append(f'{fit["label"]}: detrended noise {fit["noise_p2p_counts"]:.0f} counts means a '
                  f'hand was on the rig, so the plateau carries mechanical noise')
    if fit['median'] < 0.0:
        qc.append(f'{fit["label"]}: {fit["median"]:.1f} mmHg is below atmosphere, so the leak was '
                  f'sucking air in and the closed-volume assumption fails')
if plateaus and max(abs(f['slope']) for f in plateaus) > 0.4:
    qc.append(f'drift up to {max(abs(f["slope"]) for f in plateaus):.2f} mmHg/s - larger than '
              f'0.10-0.15 seen before, so check the plumbing before believing the number')
if qc:
    print('QUALITY GATES - failed')
    for item in qc:
        print(f'  FAIL  {item}')
    print('  the volume below is still computed, but it is not evidence until these are fixed')
else:
    print('QUALITY GATES - all pass (straight, quiet, above atmosphere, leak in range)')
print()


def solve(index_before, index_after, g_before, g_after, t_eval=None, rate_scale=1.0):
    """Evaluate both plateau fits at one instant and solve for V."""
    fit_before = plateaus[index_before]
    t_ref = instant[index_before][0] if t_eval is None else t_eval
    p_before = fit_before['intercept'] + fit_before['slope'] * rate_scale * t_ref
    if index_after < len(plateaus):
        fit_after = plateaus[index_after]
        p_after = fit_after['intercept'] + fit_after['slope'] * rate_scale * t_ref
    else:
        # No tail fit exists after the final pull: use its centre window directly.
        lo, hi, _ = instant[index_after] if index_after < len(instant) else (t[-1] - 10, t[-1], t[-1])
        mask = (t >= lo) & (t <= hi)
        seg = p[mask]
        if len(seg) < 40:
            raise SystemExit('the last plateau is too short to fit')
        tt = t[mask]
        slope, intercept = np.polyfit(tt, seg, 1)
        fit_after = dict(label='after final pull', slope=slope, intercept=intercept,
                         median=float(np.median(seg)), n=int(mask.sum()), t_lo=float(tt[0]),
                         t_hi=float(tt[-1]), residual_sd=float(np.std(seg - (slope * tt + intercept))),
                         noise_p2p_counts=float('nan'))
        plateaus.append(fit_after)
        p_after = intercept + slope * rate_scale * t_ref
    a1 = ATM + p_before
    a2 = ATM + p_after
    volume = (a2 * g_after - a1 * g_before) / (a1 - a2)
    return volume, p_before, p_after


if len(pulls) >= 1:
    after_lo, after_hi, after_centre = instant[0]
    print(f'the post-pull window for plateau B is {after_lo:.1f} .. {after_hi:.1f} s '
          f'(centre {after_centre:.1f} s)')

equations = []
g_sequence = [g1, g2, g3]
labels = ['A', 'B', 'C']
usable = min(len(pulls), len(g_sequence) - 1)
if len(pulls) > usable:
    print(f'note: {len(pulls)} pulls seen but only {len(g_sequence)} graduations were given, '
          f'so the last {len(pulls) - usable} are ignored')
for i in range(usable):
    g_before = g_sequence[i]
    g_after = g_sequence[i + 1]
    try:
        volume, p_before, p_after = solve(i, i + 1, g_before, g_after)
    except SystemExit as exc:
        print(f'  {labels[i]}-{labels[i + 1]}: skipped - {exc}')
        continue
    t_ref = instant[i][0]
    naive = ((ATM + plateaus[i]['median']) * g_after
             - (ATM + plateaus[i + 1]['median']) * g_before) \
        / ((ATM + plateaus[i]['median']) - (ATM + plateaus[i + 1]['median']))
    equations.append(dict(pair=f'{labels[i]}-{labels[i + 1]}', volume_cc=round(volume, 1),
                          uncorrected_cc=round(naive, 1), g_before=g_before, g_after=g_after,
                          p_before=round(p_before, 2), p_after=round(p_after, 2),
                          t_eval_s=round(t_ref, 2)))
    print(f'  {labels[i]}-{labels[i + 1]}: {g_before:g} -> {g_after:g} mL   '
          f'P {p_before:7.2f} -> {p_after:7.2f} mmHg at t {t_ref:6.1f} s   '
          f'V = {volume:6.1f} cc   (uncorrected {naive:6.1f}, '
          f'leak correction {naive - volume:+.1f} cc)')
print()

if equations:
    print('SENSITIVITY (how much each assumption is worth)')
    for i, eq in enumerate(equations):
        values = [solve(i, i + 1, eq['g_before'], eq['g_after'], rate_scale=s)[0]
                  for s in (0.0, 0.5, 1.0, 1.5)]
        print(f'  {eq["pair"]} leak scale 0/0.5/1/1.5 -> '
              + ' / '.join(f'{v:6.1f}' for v in values) + ' cc')
        base = eq['t_eval_s']
        shifts = [solve(i, i + 1, eq['g_before'], eq['g_after'], t_eval=base + d)[0]
                  for d in (-10.0, -5.0, 0.0, 5.0, 10.0)]
        print(f'  {eq["pair"]} eval time -10/-5/0/+5/+10 s -> '
              + ' / '.join(f'{v:6.1f}' for v in shifts) + ' cc')
    print()

    values = [eq['volume_cc'] for eq in equations]
    print(f'SUMMARY: {len(values)} equation(s), V = '
          + ', '.join(f'{v:.1f}' for v in values) + ' cc')
    if len(values) > 1:
        print(f'         spread {max(values) - min(values):.1f} cc about mean '
              f'{sum(values) / len(values):.1f} cc')
    if qc:
        print('         WARNING: quality gates failed, see above')
    print()
    print('This V is the TOTAL gas volume of the loop: cuff + tubing + tee + valve dead space +')
    print('sensor port + the syringe hub, at the instant of the pull. The manual quotes 310 mL for')
    print('its own manikin (20 cc chamber + 290 cc canister) and that is a total as well, so the')
    print('two are comparable. It is NOT the cuff inflation volume on its own.')

payload = dict(name=args.name, graduations_ml=dict(g1=g1, g2=g2, g3=g3),
               pulls=[round(v, 2) for v in pulls],
               fits=[{k: v for k, v in fit.items() if k != 'intercept'} for fit in plateaus],
               equations=equations, quality_failures=qc)
out = Path(args.json_out) if args.json_out else OMNI / f'{args.name}.volume.json'
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=float) + '\n',
               encoding='utf-8')
print()
print('WROTE', out.relative_to(ROOT))
