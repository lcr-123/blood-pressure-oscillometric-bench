"""Verify data/checksums.sha256 against the files on disk.

Checks three things, not just digests:
  - every listed file exists and its digest matches;
  - no path is listed twice (a duplicate line is a generator bug, not a pass --
    it used to be silently accepted because the digests agreed);
  - every .ndjson/.json/.md/.png/.csv file under the two covered directories is
    listed, so a newly added file cannot go unrecorded.
Exit code 0 only when all three hold.
"""
import hashlib
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = ROOT / 'data' / 'checksums.sha256'
TARGETS = [ROOT / 'data' / 'raw' / 'development_20261101',
           ROOT / 'data' / 'reports']
# Keep this list identical to tools/build_checksums.py PATTERNS. `*.ndjson` is
# absent on purpose: per-sample telemetry is gitignored, so it cannot appear in a
# manifest that is supposed to describe what a clone receives.
PATTERNS = ('*.export.ndjson', '*.metadata.json', '*.md', '*.png',
            '*.json', '*.csv')
SKIP_NAMES = ('checksums.sha256',)

bad = missing = ok = 0
seen = []
for line in manifest.read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if not line:
        continue
    digest, _, relative = line.partition('  ')
    seen.append(relative)
    path = ROOT / relative
    if not path.exists():
        print('MISSING', relative)
        missing += 1
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != digest:
        print('MISMATCH', relative, 'expected', digest[:12], 'got', actual[:12])
        bad += 1
    else:
        ok += 1

dups = sorted(name for name, n in Counter(seen).items() if n > 1)
for name in dups:
    print('DUPLICATE', name, Counter(seen)[name], 'times')

listed = set(seen)
on_disk = set()
for folder in TARGETS:
    for pattern in PATTERNS:
        on_disk.update(folder.glob(pattern))
unlisted = sorted(p.relative_to(ROOT).as_posix()
                  for p in on_disk if p.name not in SKIP_NAMES) 
unlisted = [p for p in unlisted if p not in listed]
for name in unlisted:
    print('UNLISTED', name)

print(f'ok={ok} mismatched={bad} missing={missing} '
      f'duplicates={len(dups)} unlisted={len(unlisted)} unique={len(listed)}')
sys.exit(1 if bad or missing or dups or unlisted else 0)
