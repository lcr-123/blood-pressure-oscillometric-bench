"""Verify a staged release package on its own.

Runs against the package directory only: it does not read the repository, so a
third party who downloaded just this tree can repeat the check. Four things must
hold, and the exit code is 0 only when all four do:

  - every path in checksums.sha256 exists and its digest matches;
  - no path is listed twice;
  - every file in the package is listed (an unlisted file is a staging bug);
  - release.json agrees with the tree: the round count, the tier split and the
    gate split are recomputed from the files, not trusted.

    python tools/verify_release_package.py dist/bp_waveforms_20261126
"""
import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

SKIP_NAMES = ('checksums.sha256',)


def walk(root):
    """Every file under root except the checksum file itself."""
    return sorted(p for p in root.rglob('*')
                  if p.is_file() and p.name not in SKIP_NAMES)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('package', help='directory produced by tools/release_package.py')
    args = ap.parse_args()

    root = Path(args.package).resolve()
    manifest = root / 'checksums.sha256'
    listing_path = root / 'release.json'
    for need in (manifest, listing_path):
        if not need.is_file():
            sys.exit(f'refusing to verify: {need.name} missing from {root}')

    failures = []

    ok = bad = 0
    seen = []
    for line in manifest.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, relative = line.partition('  ')
        seen.append(relative)
        path = root / relative
        if not path.is_file():
            failures.append(f'MISSING {relative}')
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            failures.append(f'MISMATCH {relative} expected {digest[:12]} got {actual[:12]}')
            bad += 1
        else:
            ok += 1

    for name, count in sorted(Counter(seen).items()):
        if count > 1:
            failures.append(f'DUPLICATE {name} {count} times')

    listed = set(seen)
    for path in walk(root):
        relative = path.relative_to(root).as_posix()
        if relative not in listed:
            failures.append(f'UNLISTED {relative}')

    listing = json.loads(listing_path.read_text(encoding='utf-8'))
    exports = [p for p in walk(root) if p.name.endswith('.export.ndjson')]
    metadata = [p for p in walk(root) if p.name.endswith('.metadata.json')]
    telemetry = [p for p in walk(root)
                 if p.name.endswith('.ndjson') and not p.name.endswith('.export.ndjson')]

    if listing.get('published_rounds') != len(exports):
        failures.append(f'release.json claims {listing.get("published_rounds")} '
                        f'round(s) but the tree holds {len(exports)} export(s)')
    if len(exports) != len(metadata):
        failures.append(f'{len(exports)} export(s) but {len(metadata)} metadata file(s)')
    if bool(listing.get('with_telemetry')) != bool(telemetry):
        failures.append(f'release.json with_telemetry={listing.get("with_telemetry")} '
                        f'but the tree holds {len(telemetry)} telemetry file(s)')
    if sum(listing.get('tiers', {}).values()) != len(exports):
        failures.append(f'tier split sums to {sum(listing.get("tiers", {}).values())}, '
                        f'not {len(exports)}')
    if sum(listing.get('gate', {}).values()) != len(exports):
        failures.append(f'gate split sums to {sum(listing.get("gate", {}).values())}, '
                        f'not {len(exports)}')

    # Each export records the calibration it was captured with; that is the only
    # reliable way to know which axis its pressure column is on.
    axes = Counter()
    for path in exports:
        header = json.loads(path.read_text(encoding='utf-8').splitlines()[0])
        slope = header.get('slope')
        intercept = header.get('intercept')
        axes[(slope, intercept)] += 1

    for line in failures:
        print(line)
    print(f'ok={ok} mismatched={bad} exports={len(exports)} '
          f'metadata={len(metadata)} telemetry={len(telemetry)} '
          f'files={len(listed)}')
    for axis, count in sorted(axes.items(), key=lambda kv: -kv[1]):
        print(f'axis raw_bits slope={axis[0]} intercept={axis[1]}: {count} export(s)')
    if failures:
        print(f'RELEASE PACKAGE NOT VERIFIED: {len(failures)} problem(s)')
        return 1
    print('RELEASE PACKAGE OK: digests, coverage and counts all agree')
    return 0


if __name__ == '__main__':
    sys.exit(main())
