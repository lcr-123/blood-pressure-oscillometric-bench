"""Judge a cross-day batch, with protocol §4 rule 10 actually implemented.

Why this file exists
--------------------
`tmp/crosstday_analyse_20261116.py` is the judge whose sha256 is recorded in
`data/protocols/reference_bp_batch_crosstday_v1.md` appendix A, so it is frozen and
must never be edited: the reproducibility of the first cross-day batch depends on that
hash.  But it never implements §4 rule 10, which says

    10. 块B 未完成的日子不排除块A：该日按 half_day=True 记账，T2 用它之外的日子算，
        T1/T3 只用完整日。

It feeds every surviving day into T1 and T3.  On the 2026-11-16..25 batch that is not a
cosmetic difference: the day-1 half day carries 14 block-A rounds whose model residuals
scatter at 32.4 mmHg (against 14.9 for the other block-A rounds), which pulls the
within-cell sd from 15.86 up to 17.21 and pushes the SBP day term from p = 0.0313
(reproduced) to p = 0.0572 (not reproduced).  Same data, opposite published conclusion.

So this module is a faithful port of the frozen judge with two deliberate changes and
nothing else:

  1. `complete_days()` derives the complete-day set from the manifest alone, before any
     estimate is computed, and T1/T3 receive only those days (rule 10).
  2. `planned_split()` splits by planned day *number* (the first half of the days the
     manifest planned), not by slicing the list of surviving days, which would move a
     day from the late half into the early half whenever an earlier day drops out.

T0, T2 and T4 keep using every surviving day, exactly as before, because rule 10 says
they should: rule 10 only narrows T1/T3.

Use `--rule10 off` to reproduce the frozen judge bit for bit (that is the regression
check), `--rule10 on` to get the protocol's reading, and `--rule10 both` to publish the
two side by side.

Usage
    python tools/crosstday_judge.py --rule10 both --json tmp/out.json
    python tools/crosstday_judge.py --rule10 off --json tmp/off.json   # must equal the frozen run
"""
import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import covered_bp  # noqa: E402
import reference_bp  # noqa: E402
import validity_v2  # noqa: E402

RAW = ROOT / 'data' / 'raw' / 'development_20261101'
DEFAULT_MANIFEST = ROOT / 'tmp' / 'omniprobe' / 'crosstday_manifest.json'

LIMIT_MMHG = 5.0
SD_LIMIT_MMHG = 8.0
WRAP_DETECTABLE_MMHG = 1.81      # protocol §2.1, 80% detection power of this design
PARAMS = ('map_mmhg', 'sbp_mmhg', 'dbp_mmhg')
LABELS = {'map_mmhg': 'MAP', 'sbp_mmhg': 'SBP', 'dbp_mmhg': 'DBP'}


# ---------------------------------------------------------------- distributions

def t975(df):
    """Two-sided 95% Student t quantile by Cornish-Fisher (accuracy ~1e-3 for df >= 10)."""
    if df < 1:
        return float('nan')
    if df == 1:
        return 12.7062
    if df == 2:
        return 4.3027
    z = 1.959964
    g1 = (z ** 3 + z) / 4.0
    g2 = (5 * z ** 5 + 16 * z ** 3 + 3 * z) / 96.0
    g3 = (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / 384.0
    g4 = (79 * z ** 9 + 776 * z ** 7 + 1482 * z ** 5 - 1920 * z ** 3 - 945 * z) / 92160.0
    return z + g1 / df + g2 / df ** 2 + g3 / df ** 3 + g4 / df ** 4


def betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    log_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - log_beta) / a
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x)
    return 1.0 - betainc(b, a, 1 - x)


def _betacf(a, b, x, iterations=200, eps=3e-12):
    tiny = 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, iterations + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def f_sf(f, d1, d2):
    """P(F > f) via the regularized incomplete beta, no scipy dependency."""
    if not math.isfinite(f) or f <= 0:
        return 1.0
    x = d2 / (d2 + d1 * f)
    return betainc(d2 / 2.0, d1 / 2.0, x)


# ---------------------------------------------------------------- rule 10 inputs

def manifest_days(manifest):
    """Every day index the manifest planned, complete or not."""
    out = []
    for day in manifest.get('days', []):
        value = day.get('day')
        if value is not None:
            out.append(int(value))
    return sorted(out)


def day_slot_counts(manifest):
    """(day, block) -> {preset: number of slots that left a run_id}."""
    counts = defaultdict(lambda: defaultdict(int))
    for day in manifest.get('days', []):
        index = day.get('day')
        if index is None:
            continue
        for block in day.get('blocks', []):
            wrap = block.get('block')
            for slot in block.get('slots', []):
                if not slot.get('run_id'):
                    continue
                preset = slot.get('preset')
                if preset is None:
                    continue
                counts[(int(index), wrap)][int(preset)] += 1
    return counts


def complete_days(manifest):
    """§4 rule 10: a day is complete when block B finished and both blocks kept every preset.

    The predicate deliberately reads only the manifest - i.e. what the operator actually
    recorded - and never the estimates, so it cannot be bent after the answers are in.
    A day is complete when, for every preset in the design, both block A and block B hold
    at least one surviving round.  A half day (block B absent) fails by construction.
    """
    counts = day_slot_counts(manifest)
    presets = sorted({p for block in counts.values() for p in block})
    complete = []
    for index in manifest_days(manifest):
        a = counts.get((index, 'A'), {})
        b = counts.get((index, 'B'), {})
        if not b:
            continue
        if all(a.get(p, 0) >= 1 for p in presets) and all(b.get(p, 0) >= 1 for p in presets):
            complete.append(index)
    return complete


def planned_split(manifest):
    """Protocol §3 T1: the first five planned days against the rest, by day number.

    The frozen judge instead halves the *surviving* day list by index, so dropping an
    early day silently promotes a late day into the early half.
    """
    days = manifest_days(manifest)
    if len(days) < 4:
        return set(), set()
    split = len(days) // 2
    return set(days[:split]), set(days[split:])


# ---------------------------------------------------------------- collection

def preset_of(run_id, metadata):
    value = metadata.get('panel_preset')
    if value:
        return int(value)
    return covered_bp.preset_of(run_id)


def exclusion_reason(export_path, metadata, run_id):
    """Apply §4 rules 1-9; return None when the round counts."""
    if metadata.get('outcome') != 'export_received':
        return 'outcome:' + str(metadata.get('outcome'))
    if not metadata.get('closeout_confirmed'):
        return 'closeout_not_confirmed'
    if metadata.get('panel_state_established') is False:
        return 'panel_state_not_established'
    gate = validity_v2.check(str(export_path))
    if not gate.get('usable'):
        return 'validity_v2:' + ';'.join(gate.get('reasons') or [])
    return None


def incumbent(export_path):
    """Frozen v2 answer, with the panel values subtracted out into errors."""
    try:
        capture = reference_bp.load(export_path)
    except Exception as exc:                     # rule 1: strict decode
        return {'status': 'decode_error', 'error': repr(exc)}
    return reference_bp.estimate(capture)


def collect(manifest):
    rounds = []
    exclusions = []
    for day in manifest.get('days', []):
        batch_day = day.get('day')
        for block in day.get('blocks', []):
            wrap = block.get('block')
            for slot in block.get('slots', []):
                run_id = slot.get('run_id')
                if not run_id:
                    continue
                export = RAW / f'{run_id}.export.ndjson'
                meta_path = RAW / f'{run_id}.metadata.json'
                metadata = json.loads(meta_path.read_text(encoding='utf-8')) \
                    if meta_path.is_file() else {}
                if not export.is_file():
                    exclusions.append({'run_id': run_id, 'reason': 'export_missing'})
                    continue
                reason = exclusion_reason(export, metadata, run_id)
                if reason:
                    exclusions.append({'run_id': run_id, 'reason': reason})
                    continue
                row = {'run_id': run_id, 'day': int(metadata.get('batch_day') or batch_day or 0),
                       'wrap': wrap, 'preset': preset_of(run_id, metadata),
                       'panel': {'map_mmhg': metadata.get('panel_map_mmhg'),
                                 'sbp_mmhg': metadata.get('panel_sbp_mmhg'),
                                 'dbp_mmhg': metadata.get('panel_dbp_mmhg')}}
                v2 = incumbent(export)
                v5 = covered_bp.covered_estimate(export)
                row['v2_status'] = v2.get('status')
                row['v5_status'] = v5.get('status')
                for param in PARAMS:
                    panel = row['panel'].get(param)
                    if panel is None:
                        continue
                    row[f'v2_{param}'] = (None if v2.get(param) is None
                                          else float(v2[param]) - float(panel))
                    row[f'v5_{param}'] = (None if v5.get(param) is None
                                          else float(v5[param]) - float(panel))
                rounds.append(row)
    return rounds, exclusions


# ---------------------------------------------------------------- models

def two_way(rows, param, prefix='v2'):
    """Additive day + preset model on one parameter; returns residual sd, day effects,
    and the F test for the day term.  Verbatim port of the frozen implementation."""
    usable = [r for r in rows if r.get(f'{prefix}_{param}') is not None]
    if len(usable) < 8:
        return None
    days = sorted({r['day'] for r in usable})
    presets = sorted({r['preset'] for r in usable})
    if len(days) < 2 or len(presets) < 2:
        return None
    day_index = {d: i for i, d in enumerate(days)}
    preset_index = {p: i for i, p in enumerate(presets)}
    columns = 1 + (len(days) - 1) + (len(presets) - 1)
    X = np.zeros((len(usable), columns))
    y = np.zeros(len(usable))
    for row_index, r in enumerate(usable):
        X[row_index, 0] = 1.0
        di, pi = day_index[r['day']], preset_index[r['preset']]
        if di:
            X[row_index, di] = 1.0
        if pi:
            X[row_index, len(days) - 1 + pi] = 1.0
        y[row_index] = r[f'{prefix}_{param}']
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    fitted = X @ beta
    residual = y - fitted
    ss_res = float((residual ** 2).sum())
    df_res = len(usable) - np.linalg.matrix_rank(X)
    sw2 = ss_res / df_res if df_res > 0 else float('nan')
    ss_tot = float(((y - y.mean()) ** 2).sum())
    X0 = np.column_stack([X[:, 0]] + [X[:, len(days) - 1 + i] for i in range(1, len(presets))])
    beta0, *_ = np.linalg.lstsq(X0, y, rcond=None)
    ss_res0 = float(((y - X0 @ beta0) ** 2).sum())
    df_day = len(days) - 1
    ss_day = ss_res0 - ss_res
    f_day = (ss_day / df_day) / sw2 if sw2 > 0 and df_day > 0 else float('nan')
    p_day = f_sf(f_day, df_day, df_res)
    day_effects = {days[i]: float(beta[i]) for i in range(1, len(days))}
    day_effects[days[0]] = 0.0
    se_day = []
    for i in range(1, len(days)):
        cov = np.linalg.pinv(X.T @ X) * sw2
        se_day.append(math.sqrt(max(cov[i, i], 0.0)))
    var_coef = float(np.var([day_effects[d] for d in days], ddof=1)) if len(days) > 2 else 0.0
    noise = float(np.mean([s ** 2 for s in se_day])) if se_day else 0.0
    sb2 = max(0.0, var_coef - noise)
    return {'days': days, 'presets': presets, 'sw': math.sqrt(max(sw2, 0.0)),
            'sb': math.sqrt(sb2), 'day_effects': day_effects,
            'f_day': float(f_day), 'p_day': float(p_day),
            'df_day': int(df_day), 'df_res': int(df_res), 'n': len(usable),
            'ss_day_share': float(ss_day / ss_tot) if ss_tot > 0 else None}


def t0(rows, prefix='v2'):
    """Per (preset, parameter) cell: mean, sd, day-clustered CI, and the verdict rule."""
    by_preset = defaultdict(list)
    for r in rows:
        by_preset[r['preset']].append(r)
    out = {}
    for preset, group in sorted(by_preset.items()):
        days = sorted({r['day'] for r in group})
        cells = {}
        for param in PARAMS:
            values = [r.get(f'{prefix}_{param}') for r in group]
            model = two_way(rows, param, prefix)
            sw = (model or {}).get('sw')
            sb = (model or {}).get('sb')
            clean = [v for v in values if v is not None]
            if len(clean) < 2 or sw is None or len(days) < 2:
                cells[param] = {'n': len(clean), 'verdict': 'not enough data'}
                continue
            n = len(clean)
            mean = float(np.mean(clean))
            sd = float(np.std(clean, ddof=1))
            se = math.sqrt(sw ** 2 / n + sb ** 2 / len(days))
            half = t975(len(days) - 1) * se
            inside = abs(mean) + half <= LIMIT_MMHG
            cells[param] = {'n': n, 'days': len(days), 'mean': mean, 'sd': sd,
                            'se_clustered': se, 'ci95': [mean - half, mean + half],
                            'half_width': half,
                            'aami_mean_ok': abs(mean) <= LIMIT_MMHG,
                            'aami_sd_ok': sd <= SD_LIMIT_MMHG,
                            'claimable_within_5': bool(inside),
                            'verdict': ('PASS (claimable)' if (inside and sd <= SD_LIMIT_MMHG)
                                        else ('FAIL' if abs(mean) - half > LIMIT_MMHG
                                              else 'undecided'))}
        out[preset] = cells
    return out


def frozen_split(rows):
    """How the frozen judge splits: halve the list of *surviving* days by index."""
    days = sorted({r['day'] for r in rows})
    if len(days) < 4:
        return set(), set()
    split = len(days) // 2
    return set(days[:split]), set(days[split:])


def t1(rows, first, second, prefix='v2'):
    """§3 T1.  `first` / `second` are day sets, supplied by planned_split()."""
    early = [r[f'{prefix}_sbp_mmhg'] for r in rows
             if r['day'] in first and r.get(f'{prefix}_sbp_mmhg') is not None]
    late = [r[f'{prefix}_sbp_mmhg'] for r in rows
            if r['day'] in second and r.get(f'{prefix}_sbp_mmhg') is not None]
    if len(early) < 4 or len(late) < 4:
        return {'verdict': 'not enough rounds'}
    d = -float(np.mean(early))
    mean_wo = float(np.mean(late))
    mean_with = mean_wo + d
    sd_late = float(np.std(late, ddof=1))
    if abs(d) < 0.5:
        ok = abs(mean_wo) <= LIMIT_MMHG and sd_late <= SD_LIMIT_MMHG
        return {'verdict': 'PASS' if ok else 'FAIL', 'rule': 'no offset needed',
                'offset_fitted': d, 'late_mean_without': mean_wo,
                'late_mean_with': mean_with, 'late_sd': sd_late,
                'first_days': sorted(first), 'second_days': sorted(second),
                'n_early': len(early), 'n_late': len(late)}
    improvement = abs(mean_wo) - abs(mean_with)
    ok = (abs(mean_with) <= LIMIT_MMHG and sd_late <= SD_LIMIT_MMHG
          and improvement >= 0.5)
    return {'verdict': 'PASS' if ok else 'FAIL', 'rule': 'offset must transfer',
            'offset_fitted': d, 'late_mean_without': mean_wo,
            'late_mean_with': mean_with, 'late_sd': sd_late,
            'improvement': improvement,
            'first_days': sorted(first), 'second_days': sorted(second),
            'n_early': len(early), 'n_late': len(late)}


def t2(rows, prefix='v2'):
    pairs = defaultdict(lambda: {'A': [], 'B': []})
    for r in rows:
        value = r.get(f'{prefix}_sbp_mmhg')
        if value is None or r['wrap'] not in ('A', 'B'):
            continue
        pairs[(r['day'], r['preset'])][r['wrap']].append(value)
    deltas, weights = [], []
    per_cell = []
    for (day, preset), blocks in sorted(pairs.items()):
        if not blocks['A'] or not blocks['B']:
            continue
        delta = float(np.mean(blocks['B']) - np.mean(blocks['A']))
        weight = min(len(blocks['A']), len(blocks['B']))
        deltas.append(delta)
        weights.append(weight)
        per_cell.append({'day': day, 'preset': preset, 'delta_sbp': delta,
                         'n_a': len(blocks['A']), 'n_b': len(blocks['B'])})
    if not deltas:
        return {'verdict': 'no paired cell'}
    arr = np.array(deltas, dtype=float)
    w = np.array(weights, dtype=float)
    delta_wrap = float((arr * w).sum() / w.sum())
    n_eff = float(w.sum() ** 2 / (w ** 2).sum())
    if len(arr) > 1:
        weighted_var = float((w * (arr - delta_wrap) ** 2).sum() / w.sum())
        se = math.sqrt(weighted_var / n_eff)
    else:
        se = float('nan')
    half = t975(max(int(round(n_eff)) - 1, 1)) * se
    if abs(delta_wrap) >= WRAP_DETECTABLE_MMHG:
        verdict = 'cuff wrapping is a nameable mechanism'
        statement = ('wrapping the cuff shifts SBP by %.2f mmHg (95%% CI %.2f..%.2f); '
                     'it explains at least part of the day step'
                     % (delta_wrap, delta_wrap - half, delta_wrap + half))
    else:
        verdict = 'wrapping excluded above the detection limit'
        statement = ('rewrapping the cuff shifts SBP by at most %.2f mmHg at this '
                     'design\'s 80%% detection power (measured %.2f, 95%% CI %.2f..%.2f)'
                     % (WRAP_DETECTABLE_MMHG, delta_wrap, delta_wrap - half, delta_wrap + half))
    return {'verdict': verdict, 'statement': statement, 'delta_wrap_mmhg': delta_wrap,
            'ci95': [delta_wrap - half, delta_wrap + half],
            'detectable_mmhg': WRAP_DETECTABLE_MMHG, 'cells': per_cell}


def t4(rows):
    out = {}
    for prefix, name in (('v2', 'frozen_v2'), ('v5', 'covered_bp')):
        published = [r for r in rows if r.get(f'{prefix}_sbp_mmhg') is not None]
        silent = [r for r in published
                  if abs(r[f'{prefix}_sbp_mmhg']) > 20 or
                  (r.get(f'{prefix}_map_mmhg') is not None and abs(r[f'{prefix}_map_mmhg']) > 20)]
        out[name] = {'rounds': len(rows), 'published': len(published),
                     'publish_rate': len(published) / len(rows) if rows else None,
                     'silent_over_20': len(silent),
                     'per_preset': t0(rows, prefix)}
    return out


def model_block(rows, prefix='v2'):
    out = {}
    for param in ('sbp_mmhg', 'map_mmhg', 'dbp_mmhg'):
        out[f'model_{param}'] = two_way(rows, param, prefix)
    return out


# ---------------------------------------------------------------- driver

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument('--json', type=Path, default=None)
    ap.add_argument('--rule10', choices=('off', 'on', 'both'), default='on',
                    help='off reproduces the frozen judge; on applies protocol §4 rule 10')
    args = ap.parse_args()
    if not args.manifest.is_file():
        raise SystemExit(f'{args.manifest} not found: run the batch first')
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    rows, exclusions = collect(manifest)
    if not rows:
        raise SystemExit('no round survived the exclusion rules; nothing to judge')

    complete = complete_days(manifest)
    planned = manifest_days(manifest)
    dropped = [d for d in planned if d not in complete]
    strict = [r for r in rows if r['day'] in complete]
    first, second = planned_split(manifest)
    first_on, second_on = first & set(complete), second & set(complete)

    print(f'batch {manifest.get("batch_tag")}: {len(rows)} round(s) over '
          f'{len({r["day"] for r in rows})} day(s), presets {sorted({r["preset"] for r in rows})}',
          flush=True)
    print(f'excluded: {len(exclusions)}', flush=True)
    print(f'rule 10: planned days {planned}, complete days {complete}, '
          f'dropped from T1/T3 {dropped}', flush=True)
    print(f'rule 10: {len(strict)} of {len(rows)} round(s) reach T1/T3', flush=True)
    print(f'T1 split by planned day number: first {sorted(first_on)}, second {sorted(second_on)}',
          flush=True)

    report = {'batch_tag': manifest.get('batch_tag'), 'rounds': len(rows),
              'days': sorted({r['day'] for r in rows}),
              'presets': sorted({r['preset'] for r in rows}),
              'exclusions': exclusions, 'rule10': args.rule10,
              'rule10_complete_days': complete, 'rule10_dropped_days': dropped,
              'rule10_rounds_t1t3': len(strict),
              't1_split_first': sorted(first_on), 't1_split_second': sorted(second_on)}

    for label, subset in (('all days', rows), ('rule 10 (complete days)', strict)):
        for param in ('sbp_mmhg', 'map_mmhg', 'dbp_mmhg'):
            model = two_way(subset, param, 'v2')
            if model is None:
                continue
            print(f'\n[{LABELS[param]}] two-way day + preset, {label}', flush=True)
            print('  sw %.3f mmHg (within cell), sb %.3f mmHg (between day), n %d'
                  % (model['sw'], model['sb'], model['n']), flush=True)
            print('  day term F(%d,%d) = %.2f, p = %.4g, share of total SS %.1f%%'
                  % (model['df_day'], model['df_res'], model['f_day'], model['p_day'],
                     100.0 * (model['ss_day_share'] or 0.0)), flush=True)

    report.update(model_block(rows, 'v2'))
    report.update({f'{key}_rule10': value
                   for key, value in model_block(strict, 'v2').items()})
    report['t0_all_days'] = t0(rows, 'v2')
    report['t2_all_days'] = t2(rows, 'v2')
    report['t4_all_days'] = t4(rows)

    # The frozen judge's own reading: every surviving day, split by index.
    off = t1(rows, *frozen_split(rows))
    off['split_source'] = 'frozen: half of the surviving day list, by index'
    on = t1(strict, first_on, second_on)
    on['split_source'] = 'protocol: planned day number, complete days only'
    report['t1_off'] = off
    report['t1_on'] = on
    report['t1'] = {'off': off, 'on': on}[args.rule10 if args.rule10 in ('off', 'on') else 'on']

    print('\n[T1] additive SBP offset transfer', flush=True)
    print('  frozen reading (all days, index split):    '
          + json.dumps(off, ensure_ascii=False), flush=True)
    print('  protocol rule 10 (complete days, planned): '
          + json.dumps(on, ensure_ascii=False), flush=True)
    if args.rule10 == 'both':
        share = ('same verdict' if off['verdict'] == on['verdict']
                 else 'VERDICT DIFFERS: %s vs %s' % (off['verdict'], on['verdict']))
        print('  ' + share, flush=True)

    report['t2'] = report['t2_all_days']
    print('\n[T2] cuff rewrapping', flush=True)
    print('  ' + report['t2'].get('statement', report['t2']['verdict']), flush=True)

    report['t4'] = report['t4_all_days']
    print('\n[T4] both estimators', flush=True)
    for name, block in report['t4'].items():
        print('  %-12s published %d/%d (%.3f), silent>20 %d'
              % (name, block['published'], block['rounds'],
                 block['publish_rate'] or 0.0, block['silent_over_20']), flush=True)

    report['t0'] = report['t0_all_days']
    print('\n[T0] cells, frozen v2, day-clustered, all days', flush=True)
    for preset, cells in report['t0'].items():
        for param, cell in cells.items():
            if cell.get('verdict') in (None, 'not enough data'):
                continue
            print('  P%d %-3s n=%2d mean %+6.2f sd %5.2f CI[%+6.2f,%+6.2f] %s'
                  % (preset, LABELS[param], cell['n'], cell['mean'], cell['sd'],
                     cell['ci95'][0], cell['ci95'][1], cell['verdict']), flush=True)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
        print('\nWROTE', args.json, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
