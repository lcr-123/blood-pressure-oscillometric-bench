"""Generate data/checksums.sha256 over the published dataset files.

Each file is hashed exactly once. The earlier generator (tmp/build_checksums_20261107.py,
not versioned) globbed overlapping patterns in the same directory -- `*.ndjson` also matched
`*.export.ndjson`, and `*.json` also matched `*.metadata.json` -- so 856 raw files were
written twice. The duplicate lines carried identical digests, so tools/verify_checksums.py
still passed and the defect went unnoticed. This builder takes the union of the patterns
through a set, so overlap is harmless, and it also covers the .csv files under reports/
that the old pattern list never matched.

Scope changed on 2026-11-26: the manifest used to cover per-sample telemetry as well.
That telemetry is now gitignored (2.2 GB, read by no estimator), so the manifest covers
only what a clone receives: 645 exports, their metadata, and the reports.
"""
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [ROOT / 'data' / 'raw' / 'development_20261101',
           ROOT / 'data' / 'reports']
# `*.export.ndjson` is listed explicitly; plain `*.ndjson` is deliberately absent.
# Per-sample telemetry (2.2 GB) is no longer tracked -- no estimator reads it, and
# the one thing reports did read from it, the device's own [BP] verdict, is now
# extracted into data/device_verdicts.json. A checksum manifest must describe what
# a clone actually receives, so it cannot cover files that are gitignored.
PATTERNS = ('*.export.ndjson', '*.metadata.json', '*.md', '*.png',
            '*.json', '*.csv')
SKIP_NAMES = ('checksums.sha256',)

out = ROOT / 'data' / 'checksums.sha256'

paths = set()
for folder in TARGETS:
    for pattern in PATTERNS:
        paths.update(folder.glob(pattern))
paths = sorted(p for p in paths if p.name not in SKIP_NAMES)

lines = []
total = 0
for path in paths:
    relative = path.relative_to(ROOT).as_posix()
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    lines.append(f'{digest}  {relative}')
    total += path.stat().st_size

if len(lines) != len({line.split('  ', 1)[1] for line in lines}):
    sys.exit('refusing to write: duplicate paths in the manifest')

out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'{len(lines)} files, {total / 1e6:.1f} MB, wrote {out.relative_to(ROOT).as_posix()}')
