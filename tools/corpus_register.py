"""Emit one row per round: the machine-readable index of the corpus.

Why this exists
    Until now the corpus could only be enumerated by globbing data/raw/ and parsing run
    ids, and every table in data/reports/ was rebuilt by a different script. A reader who
    wants "all rounds, with firmware and verdicts" had nothing to read. This writes that
    table once, from the files themselves, so the numbers in the reports can be checked
    against a single artefact.

What it does not do
    It runs no estimator of its own. The map/sbp/dbp columns come from each round's
    metadata (`analysis` = freeze v2, `analysis_v5` = tools/covered_bp.py), which those
    metadata files record when they are patched. A round whose metadata has no analysis
    is listed with empty verdict columns and `analysis_state='not_run'`, not silently
    dropped: the table is an index, not a filter.

Columns
    run_id, date, clock, preset, panel_sbp/dbp/map, tier, published_corpus, dataset_role,
    firmware_hex (first 12), batch_tag, batch_day, wrap_block, gate,
    v2_status, v2_map/sbp/dbp + errors, v5_status, v5_map/sbp/dbp + errors,
    valve_flow, valve_working_point, export_sha256

Usage
    python tools/corpus_register.py [--out data/manifest.csv] [--json data/manifest.json]
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import dataset_tiers  # noqa: E402

RAW = ROOT / 'data' / 'raw' / 'development_20261101'
PANELS = {1: (120, 80, 93), 2: (150, 100, 116), 3: (200, 150, 166), 4: (255, 195, 215),
          5: (60, 30, 40), 6: (80, 50, 60), 7: (100, 65, 76)}

COLUMNS = [
    'run_id', 'date', 'clock', 'preset', 'panel_sbp', 'panel_dbp', 'panel_map',
    'tier', 'published_corpus', 'dataset_role', 'outcome', 'firmware_hex12', 'batch_tag',
    'batch_day', 'wrap_block',
    'gate', 'gate_slope_mmhg_s',
    'v2_status', 'v2_map', 'v2_sbp', 'v2_dbp', 'v2_map_err', 'v2_sbp_err', 'v2_dbp_err',
    'v5_status', 'v5_map', 'v5_sbp', 'v5_dbp', 'v5_map_err', 'v5_sbp_err', 'v5_dbp_err',
    'valve_flow_mmhg_per_open_ms', 'valve_working_point', 'analysis_state',
    'export_sha256',
]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def split_stamp(run_id):
    tail = run_id.rsplit('_', 1)[-1]
    if '-' not in tail:
        return '', ''
    day, clock = tail.split('-', 1)
    return day, clock


def gate_state(export):
    """Run the v2 validity gate on the export and report its verdict and slope.

    The gate rides on the pressure trace only (tools/validity_v2.py), so it can be
    recomputed at index time; the capture script does not record it in the metadata,
    which is why it has to be recomputed here rather than copied.
    """
    import validity_v2
    try:
        check = validity_v2.check(export)
    except Exception:  # noqa: BLE001 - an undecodable export is still an index row
        return 'UNDECODABLE', ''
    usable = check.get('usable')
    slope = check.get('peak_window_slope_mmhg_s')
    return ('USABLE' if usable else 'REJECTED'), ('' if slope is None else slope)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='data/manifest.csv')
    ap.add_argument('--json', default='data/manifest.json')
    args = ap.parse_args()

    rows = dataset_tiers.collect()
    by_run = {row['run_id']: row for row in rows}
    exports = sorted(RAW.glob('standard*.export.ndjson'))

    records = []
    missing_meta = []
    for export in exports:
        run_id = export.name[:-len('.export.ndjson')]
        meta_path = RAW / f'{run_id}.metadata.json'
        if not meta_path.is_file():
            missing_meta.append(run_id)
            meta = {}
        else:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
        tier_row = by_run.get(run_id, {})
        preset = tier_row.get('preset')
        panel = PANELS.get(preset, ('', '', ''))
        date, clock = split_stamp(run_id)

        v2 = meta.get('analysis') or {}
        v5 = meta.get('analysis_v5') or {}
        gate, slope = gate_state(export)

        records.append({
            'run_id': run_id,
            'date': date,
            'clock': clock,
            'preset': preset,
            'panel_sbp': panel[0],
            'panel_dbp': panel[1],
            'panel_map': panel[2],
            'tier': tier_row.get('tier', ''),
            'published_corpus': tier_row.get('published_corpus', ''),
            'dataset_role': meta.get('dataset_role', ''),
            'outcome': meta.get('outcome', ''),
            'firmware_hex12': (meta.get('firmware_hex_sha256') or '')[:12],
            'batch_tag': meta.get('batch_tag', ''),
            'batch_day': meta.get('batch_day', ''),
            'wrap_block': meta.get('wrap_block', ''),
            'gate': gate,
            'gate_slope_mmhg_s': slope,
            'v2_status': v2.get('status', ''),
            'v2_map': v2.get('map_mmhg', ''),
            'v2_sbp': v2.get('sbp_mmhg', ''),
            'v2_dbp': v2.get('dbp_mmhg', ''),
            'v2_map_err': v2.get('map_error_mmhg', ''),
            'v2_sbp_err': v2.get('sbp_error_mmhg', ''),
            'v2_dbp_err': v2.get('dbp_error_mmhg', ''),
            'v5_status': v5.get('status', ''),
            'v5_map': v5.get('map_mmhg', ''),
            'v5_sbp': v5.get('sbp_mmhg', ''),
            'v5_dbp': v5.get('dbp_mmhg', ''),
            'v5_map_err': v5.get('map_error_mmhg', ''),
            'v5_sbp_err': v5.get('sbp_error_mmhg', ''),
            'v5_dbp_err': v5.get('dbp_error_mmhg', ''),
            'valve_flow_mmhg_per_open_ms': meta.get('valve_flow_mmhg_per_open_ms', ''),
            'valve_working_point': meta.get('valve_working_point', ''),
            'analysis_state': ('scored' if v2 else 'not_run'),
            'export_sha256': sha256(export),
        })

    out = Path(args.out)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({key: record[key] for key in COLUMNS})

    out_json = Path(args.json)
    if not out_json.is_absolute():
        out_json = ROOT / out_json
    out_json.write_text(json.dumps({'rounds': len(records), 'columns': COLUMNS,
                                    'missing_metadata': missing_meta,
                                    'rows': records}, ensure_ascii=False, indent=2) + '\n',
                        encoding='utf-8')

    scored = sum(1 for record in records if record['analysis_state'] == 'scored')
    print(f'{len(records)} export(s); {scored} with a freeze-v2 verdict in metadata, '
          f'{len(records) - scored} without')
    if missing_meta:
        print(f'{len(missing_meta)} export(s) without metadata: '
              + ', '.join(missing_meta[-5:]))
    print('WROTE', out)
    print('WROTE', out_json)
    return 0


if __name__ == '__main__':
    sys.exit(main())
