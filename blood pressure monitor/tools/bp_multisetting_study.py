"""Read-only feature inventory and fit-readiness audit across BP presets."""

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from bp_capture import decode
from bp_oscillogram_study import analyze

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'data/reports/standard_bp_development_manifest_20261101.json'
GATE = ROOT / 'data/reports/standard_bp_envelope_gate_20261101.json'
OUTPUT = ROOT / 'data/reports/standard_bp_multisetting_study_20261101.json'
SETTINGS = ((120, 80), (150, 100), (200, 150))


def study(manifest_path=MANIFEST, gate_path=GATE):
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes.decode('utf-8-sig'))
    gate = json.loads(gate_path.read_text(encoding='utf-8-sig'))
    if gate['manifest_sha256'] != hashlib.sha256(manifest_bytes).hexdigest():
        raise ValueError('gate/manifest hash mismatch')
    by_id = {row['run_id']: row for row in gate['runs']}
    if len(by_id) != len(gate['runs']) or set(by_id) != {row['run_id'] for row in manifest['runs']}:
        raise ValueError('gate/manifest run mismatch')
    groups = defaultdict(list)
    for row in manifest['runs']:
        setting = tuple(row['panel_setting_mmhg'])
        if setting not in SETTINGS:
            raise ValueError(f'unknown preset setting: {row["run_id"]}')
        gate_row = by_id[row['run_id']]
        if gate_row['outcome'] != row['outcome']:
            raise ValueError(f'gate outcome mismatch: {row["run_id"]}')
        if row['outcome'] == 'export_received' and (
                gate_row['verified_path'] != row['verified_path'] or
                gate_row['verified_sha256'] != row['verified_sha256']):
            raise ValueError(f'gate source mismatch: {row["run_id"]}')
        item = {'run_id': row['run_id'], 'outcome': row['outcome'],
                'pulse_volume_cc': row['panel_pulse_volume_profile_cc'],
                'envelope_decision': gate_row['envelope_decision'],
                'reasons': gate_row['reasons'], 'height_peak_mmhg': None,
                'area_peak_mmhg': None}
        if gate_row['envelope_decision'] == 'analyzable_candidate':
            source = ROOT / row['verified_path']
            content = source.read_bytes()
            if hashlib.sha256(content).hexdigest() != row['verified_sha256']:
                raise ValueError(f'verified hash mismatch: {row["run_id"]}')
            capture = decode(content.decode('utf-8-sig').splitlines())
            analysis = analyze(capture, upper_pressure=gate_row['upper_pressure_mmhg'],
                               bin_width_mmhg=10)
            for feature in ('height', 'area'):
                result = analysis[feature]
                if result['status'] != 'diagnostic_only' or result['robustness']['screen'] != 'pass':
                    raise ValueError(f'gate/feature mismatch: {row["run_id"]}')
                item[f'{feature}_peak_mmhg'] = result['gaussian']['peak_mmhg']
            item['clean_beats'] = analysis['clean_beats']
        groups[setting].append(item)
    summaries = []
    for setting in SETTINGS:
        rows = groups[setting]
        candidates = [r for r in rows if r['envelope_decision'] == 'analyzable_candidate']
        known_volumes = defaultdict(list)
        for row in candidates:
            if row['pulse_volume_cc'] is not None:
                known_volumes[row['pulse_volume_cc']].append(row['run_id'])
        comparable = max((len(ids) for ids in known_volumes.values()), default=0)
        reasons = []
        if not candidates:
            reasons.append('no_complete_envelope_candidate')
        if comparable < 2:
            reasons.append('no_repeated_candidate_with_recorded_same_pulse_volume')
        if setting == (200, 150):
            reasons.append('high_pressure_tail_or_bound_unresolved')
        reasons.append('cross_run_zero_comparability_unresolved')
        summaries.append({'panel_setting_mmhg': list(setting), 'attempts': len(rows),
                          'envelope_candidates': len(candidates),
                          'comparable_known_volume_repeats': comparable,
                          'height_peak_range_mmhg': [min(r['height_peak_mmhg'] for r in candidates),
                                                     max(r['height_peak_mmhg'] for r in candidates)] if candidates else None,
                          'feature_repeatability_ready': not reasons,
                          'fit_blockers': reasons, 'runs': rows})
    return {'schema': 'bp.multisetting_study/1',
            'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
            'gate_sha256': hashlib.sha256(gate_path.read_bytes()).hexdigest(),
            'scope': 'post hoc development features; panel values are settings, not dynamic reference pressure',
            'bp_model_fitted': False, 'bp_coefficients': None,
            'bp_model_blockers': ['no_independent_dynamic_pressure_reference',
                                  'rule_selection_runs_are_not_holdout_validation',
                                  'preset3_has_no_qualified_envelope'],
            'settings': summaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    parser.add_argument('--gate', type=Path, default=GATE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = study(args.manifest, args.gate)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(args.output),
                      'candidate_counts': {str(x['panel_setting_mmhg']): x['envelope_candidates']
                                           for x in result['settings']},
                      'bp_model_fitted': result['bp_model_fitted']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
