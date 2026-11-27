#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the run_id -> panel MAP table that the scoring tools compare against.

`tools/v3_acceptance.py` and friends need to know what the BP Pump 2 was set to for each
round. That number lives in the round's own metadata, so it must never be typed by hand:
a stale or mis-typed table silently changes every error in the report.

Usage:
    python tools/panel_map.py --json tmp/omniprobe/panel_map_20261111.json
    python tools/panel_map.py                       # print the table

The map is derived, so it is fine to regenerate it whenever new rounds arrive; the
metadata files stay the single source of truth.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GLOB = 'data/raw/**/*.metadata.json'


def build(pattern=DEFAULT_GLOB):
    """Return {run_id: panel_map_mmhg} plus the rounds that cannot be used.

    `panel_map_mmhg` is the number printed in brackets on the Tester's Standard BP screen
    (Table 3-2 of the manual). It is an arithmetic annotation, `floor((SBP+2*DBP)/3)`,
    not a physical target - which is exactly why it has to be quoted from the metadata
    rather than recomputed here.
    """
    table, skipped = {}, []
    for path in sorted(ROOT.glob(pattern)):
        try:
            meta = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            skipped.append((path.name, f'unreadable: {exc}'))
            continue
        run_id = meta.get('run_id')
        value = meta.get('panel_map_mmhg')
        if not run_id:
            skipped.append((path.name, 'no run_id'))
        elif value is None:
            skipped.append((path.name, 'no panel_map_mmhg'))
        else:
            table[run_id] = int(value)
    return table, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--glob', default=DEFAULT_GLOB, help='metadata glob, relative to the repo root')
    parser.add_argument('--json', type=Path, help='write the table here')
    args = parser.parse_args()

    table, skipped = build(args.glob)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(table, ensure_ascii=False, indent=2, sort_keys=True) + '\n',
                             encoding='utf-8')
        print(f'{len(table)} rounds -> {args.json}')
    else:
        for run_id in sorted(table):
            print(f'{table[run_id]:4d}  {run_id}')
        print(f'{len(table)} rounds')
    for name, why in skipped:
        print(f'SKIP {name}: {why}', file=sys.stderr)
    return 0


if __name__ == '__main__':
    sys.exit(main())
