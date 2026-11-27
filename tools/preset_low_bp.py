"""Score the three low-blood-pressure presets from their manifests.

Why this exists
    Presets 5 (60/30), 6 (80/50) and 7 (100/65) were never captured before 2026-11-13.
    They sit at the low end of the panel's Table 3-2, where the oscillometric envelope
    peak falls in the middle of the deflation instead of near the top, so they are the
    best candidates for a preset that can actually carry a blood-pressure claim.

What it reports, per preset
    yield        how many captures publish all three values (status == 'ok')
    bias/sd      mean and sample sd of each error against the panel setting
    AAMI         |mean| <= 5.0 and sd <= 8.0, per quantity
    gate         the measured peak-window deflation rate against the v2 normal band
    shape        envelope peak position against the panel MAP, and the plateau ratio

What it never does
    It does not filter out a capture because its answer looks wrong: only the v2
    validity gate may drop a capture, and that gate reads the pressure trace alone.

Two entry points
    --manifest     read a batch manifest (what the collector wrote; those live under tmp/
                   during a session, so this is for a batch somebody archived)
    --from-raw     discover every matching export under data/raw/ directly, so the numbers
                   in a report can be rebuilt from the tracked data alone. In this mode the
                   firmware's own verdict is also tabulated from the round log, because
                   "calculation failed" versus "valid but wrong" is part of the record.

Usage
    python tools/preset_low_bp.py [--manifest ... | --from-raw --preset 5]
    python tools/preset_low_bp.py --from-raw --preset 5 --preset 6 --preset 7 \
        --json data/reports/preset_low_bp_20261113.json
"""
import argparse
import glob
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import reference_bp                    # noqa: E402
import validity_v2                     # noqa: E402

AAMI_MEAN_LIMIT = 5.0
AAMI_SD_LIMIT = 8.0
RAW = ROOT / 'data' / 'raw' / 'development_20261101'
PANEL = {
    5: (60, 30, 40, 0.75),
    6: (80, 50, 60, 0.71),
    7: (100, 65, 76, 0.69),
    1: (120, 80, 93, 0.68),
    2: (150, 100, 116, 0.65),
    3: (200, 150, 166, 0.60),
    4: (255, 195, 215, 0.55),
}


def preset_of(run_id):
    head = run_id.split('_target275_')[0].split('_')
    table = {'120_080': 1, '150_100': 2, '200_150': 3, '255_195': 4,
             '060_030': 5, '080_050': 6, '100_065': 7, '120_80': 1, '150_100': 2,
             '200_150': 3, '255_195': 4}
    return table.get(f'{head[0][len("standard"):]}_{head[1]}')


VERDICTS_JSON = ROOT / 'data' / 'device_verdicts.json'


def _verdicts_table():
    """Device verdicts extracted from telemetry, if that file is present.

    Per-sample telemetry is no longer tracked (it is 2.2 GB and no estimator
    reads it), so the `[BP] ...` line that this function needs is only
    available two ways: from `data/device_verdicts.json`, which
    tools/extract_device_verdicts.py produces, or from a local telemetry log
    that a reader happens to still have. Prefer the tracked table.
    """
    if not VERDICTS_JSON.exists():
        return {}
    try:
        return json.loads(VERDICTS_JSON.read_text(encoding='utf-8')).get('verdicts', {})
    except (OSError, json.JSONDecodeError):
        return {}


def device_verdict(run_id):
    """The firmware's own answer for one round, read from the bridge log.

    `bp_algorithm.c:534-541` pins the MAP search window to 80..100 mmHg, so on the low
    presets the board either prints "calculation failed" or a value that looks valid and is
    wrong. Both outcomes belong in the report, so both are recorded here verbatim.
    """
    recorded = _verdicts_table().get(run_id)
    if recorded:
        found = {k: v for k, v in recorded.items() if k != 'preset'}
        return found
    log = RAW / f'{run_id}.ndjson'
    if not log.exists():
        return {'kind': 'no_log'}
    text = log.read_text(encoding='utf-8', errors='replace')
    match = re.search(r'\[BP\] SBP=(\d+) DBP=(\d+) Pulse=(\d+) bpm valid=1', text)
    if match:
        return {'kind': 'valid', 'sbp': int(match.group(1)),
                'dbp': int(match.group(2)), 'pulse_bpm': int(match.group(3))}
    if '[BP] calculation failed' in text:
        return {'kind': 'calculation_failed'}
    return {'kind': 'no_result'}



def summarise(values):
    if not values:
        return None
    mean = statistics.fmean(values)
    sd = statistics.stdev(values) if len(values) > 1 else 0.0
    return {'n': len(values), 'mean': round(mean, 2), 'sd': round(sd, 2),
            'median': round(statistics.median(values), 2),
            'min': round(min(values), 2), 'max': round(max(values), 2),
            'aami_mean_ok': abs(mean) <= AAMI_MEAN_LIMIT,
            'aami_sd_ok': sd <= AAMI_SD_LIMIT,
            'aami_pass': abs(mean) <= AAMI_MEAN_LIMIT and sd <= AAMI_SD_LIMIT}


def load_manifest(path):
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    rows = []
    for entry in doc.get('rounds', []):
        run_id = entry.get('run_id')
        if not run_id:
            continue
        export = RAW / f'{run_id}.export.ndjson'
        if not export.exists():
            continue
        rows.append((run_id, export))
    return rows


def discover(preset):
    """Every exported round of one preset, found under data/raw/ without a manifest."""
    rows = []
    for path in sorted(glob.glob(str(RAW / 'standard*.export.ndjson'))):
        run_id = Path(path).name[:-len('.export.ndjson')]
        if preset_of(run_id) == preset:
            rows.append((run_id, Path(path)))
    return rows


def analyse(rows):
    preset = preset_of(rows[0][0])
    panel_sbp, panel_dbp, panel_map, volume = PANEL[preset]

    captured, dropped, scored = 0, [], []
    for run_id, export in rows:
        captured += 1
        check = validity_v2.check(str(export))
        if not check['usable']:
            dropped.append({'run_id': run_id, 'why': 'v2 gate',
                            'slope': check.get('peak_window_slope_mmhg_s'),
                            'reasons': check.get('reasons'),
                            'device': device_verdict(run_id)})
            continue
        capture = reference_bp.load(str(export))
        result = reference_bp.estimate(capture)
        scored.append({
            'run_id': run_id,
            'status': result['status'],
            'map_mmhg': result['map_mmhg'],
            'sbp_mmhg': result['sbp_mmhg'],
            'dbp_mmhg': result['dbp_mmhg'],
            'map_error': None if result['map_mmhg'] is None else round(result['map_mmhg'] - panel_map, 2),
            'sbp_error': None if result['sbp_mmhg'] is None else round(result['sbp_mmhg'] - panel_sbp, 2),
            'dbp_error': None if result['dbp_mmhg'] is None else round(result['dbp_mmhg'] - panel_dbp, 2),
            'envelope_peak_raw_mv': result.get('envelope_peak_raw_mv'),
            'envelope_peak_at_mmhg': result.get('envelope_peak_raw_at_mmhg'),
            'high_side_plateau_ratio': result.get('high_side_plateau_ratio'),
            'peak_window_slope_mmhg_s': check.get('peak_window_slope_mmhg_s'),
            'device': device_verdict(run_id),
        })

    published = [r for r in scored if r['status'] == 'ok']
    out = {
        'preset': preset,
        'panel': {'sbp_mmhg': panel_sbp, 'dbp_mmhg': panel_dbp,
                  'map_mmhg': panel_map, 'pulse_volume_cc': volume},
        'captured': captured,
        'gate_dropped': dropped,
        'scored': len(scored),
        'published_all_three': len(published),
        'status_counts': {s: sum(1 for r in scored if r['status'] == s)
                          for s in sorted({r['status'] for r in scored})},
        'yield': round(len(published) / captured, 3) if captured else 0.0,
    }
    for key, panel_key in (('map', 'map_mmhg'), ('sbp', 'sbp_mmhg'), ('dbp', 'dbp_mmhg')):
        values = [r[f'{key}_error'] for r in scored
                  if r[f'{key}_error'] is not None and not r['status'].startswith('unresolved_map')]
        out[key] = summarise(values)
    out['peak_at_mmhg'] = summarise([r['envelope_peak_at_mmhg'] for r in scored
                                     if r['envelope_peak_at_mmhg'] is not None])
    out['plateau_ratio'] = summarise([r['high_side_plateau_ratio'] for r in scored
                                      if r['high_side_plateau_ratio'] is not None])
    out['peak_slope'] = summarise([r['peak_window_slope_mmhg_s'] for r in scored
                                   if r['peak_window_slope_mmhg_s'] is not None])
    # The board's own answers, which is what a user of this rig would actually see.
    # Gate-dropped rounds count too: the board still printed an answer for some of them
    # (e.g. the single-point-dropout export), and the point of this section is what a
    # user reading the screen would have believed.
    kinds = {}
    device_rows = []
    for row in scored:
        device_rows.append((row['run_id'], row['device']))
    for row in dropped:
        device_rows.append((row['run_id'], row['device']))
    for _, device in device_rows:
        kinds[device['kind']] = kinds.get(device['kind'], 0) + 1
    out['device_kinds'] = kinds
    out['device_valid_rows'] = [{'run_id': run_id,
                                 'sbp': device['sbp'],
                                 'dbp': device['dbp'],
                                 'pulse_bpm': device['pulse_bpm'],
                                 'sbp_error': device['sbp'] - panel_sbp,
                                 'dbp_error': device['dbp'] - panel_dbp}
                                for run_id, device in device_rows
                                if device['kind'] == 'valid']
    out['rows'] = scored
    return out


def print_preset(doc):
    panel = doc['panel']
    print(f"\n## Preset {doc['preset']}: {panel['sbp_mmhg']}/{panel['dbp_mmhg']} "
          f"(MAP {panel['map_mmhg']}), {panel['pulse_volume_cc']:.2f} cc")
    print(f"  captured {doc['captured']}, gate dropped {len(doc['gate_dropped'])}, "
          f"scored {doc['scored']}, all three published {doc['published_all_three']} "
          f"({doc['yield'] * 100:.1f}%)")
    print(f"  status counts: {doc['status_counts']}")
    print(f"  | quantity | n | mean | sd | AAMI |")
    for key in ('map', 'sbp', 'dbp'):
        s = doc[key]
        if not s:
            print(f'  | {key.upper():8s} | 0 | - | - | no data |')
            continue
        verdict = 'PASS' if s['aami_pass'] else (
            'mean' if not s['aami_mean_ok'] else 'sd')
        print(f"  | {key.upper():8s} | {s['n']:2d} | {s['mean']:+6.2f} | {s['sd']:5.2f} | {verdict} |")
    if doc['peak_at_mmhg']:
        p = doc['peak_at_mmhg']
        print(f"  envelope peak at {p['median']:.1f} mmHg (median), panel MAP {panel['map_mmhg']}")
    if doc['plateau_ratio']:
        p = doc['plateau_ratio']
        print(f"  plateau ratio median {p['median']:.3f}, max {p['max']:.3f}")
    if doc['peak_slope']:
        p = doc['peak_slope']
        print(f"  peak-window slope {p['min']:.2f} .. {p['max']:.2f} mmHg/s (median {p['median']:.2f})")
    print(f"  firmware verdict: {doc['device_kinds']}")
    for row in doc['device_valid_rows']:
        print(f"    {row['run_id'][-15:]}  SBP {row['sbp']:3d} ({row['sbp_error']:+4.0f})  "
              f"DBP {row['dbp']:3d} ({row['dbp_error']:+4.0f})  pulse {row['pulse_bpm']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', action='append')
    ap.add_argument('--from-raw', action='store_true',
                    help='discover rounds under data/raw/ instead of reading a manifest')
    ap.add_argument('--preset', type=int, action='append', choices=sorted(PANEL),
                    help='with --from-raw, which presets to score (default 5, 6, 7)')
    ap.add_argument('--json')
    args = ap.parse_args()

    results = []
    if args.from_raw:
        for preset in (args.preset or [5, 6, 7]):
            rows = discover(preset)
            if not rows:
                print(f'SKIP preset {preset}: no exported captures under {RAW}')
                continue
            doc = analyse(rows)
            print_preset(doc)
            results.append(doc)
    else:
        if args.manifest:
            manifests = args.manifest
        else:
            # The low-preset batches were scored from collector manifests that
            # live under tmp/ and are not tracked, so the historical default
            # (v4_p5a/p6a/p7a_manifest.json under data/protocols/v4_batches)
            # does not exist in a clone. Skipping every input and exiting 0
            # would look like a passing run, so say what to do instead.
            manifests = [
                str(ROOT / 'data' / 'protocols' / 'v4_batches' / f'v4_p{n}a_manifest.json')
                for n in (5, 6, 7)]
            if not any(Path(p).exists() for p in manifests):
                print('no manifest to read: the low-preset batch manifests were'
                      ' written to tmp/ during collection and are not tracked.',
                      file=sys.stderr)
                print('use --from-raw to discover the same rounds under data/raw,'
                      ' or pass --manifest <path> explicitly.', file=sys.stderr)
                return 2
        for path in manifests:
            if not Path(path).exists():
                print(f'SKIP {path}: not found')
                continue
            rows = load_manifest(path)
            if not rows:
                print(f'SKIP {path}: no exported captures')
                continue
            doc = analyse(rows)
            print_preset(doc)
            results.append(doc)

    if args.json and results:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({'aami_limits': {'mean': AAMI_MEAN_LIMIT, 'sd': AAMI_SD_LIMIT},
                                   'discovered_from_raw': bool(args.from_raw),
                                   'presets': results}, ensure_ascii=False, indent=2) + '\n',
                       encoding='utf-8')
        print('\nWROTE', out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
