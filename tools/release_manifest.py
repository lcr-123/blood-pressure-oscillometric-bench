"""Record the identity of a staged release package in git, without its bytes.

`dist/` is gitignored: the staged package duplicates bytes that already live in
`data/raw/`, so committing it would grow the git pack by 30 MB and add no
information. What has to be versioned is the *identity* of the package — which
rounds it holds, which documents it ships, and the two commands that rebuild and
verify it. A third party who downloads the package can then check that the 62
run_ids in their hands are the same set this commit names.

The round list is derived, never typed: the published set comes from
`data/manifest.json`, and the package contents are cross-asserted against it.

    python tools/release_manifest.py --package dist/bp_waveforms_20261126 \
        --out data/release/published_corpus_20261126.json
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git_commit():
    """The commit the package was built from, or None outside a git checkout."""
    try:
        return subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                              capture_output=True, text=True, check=True
                              ).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package', required=True, help='staged package directory')
    ap.add_argument('--out', default='data/release/published_corpus_<date>.json',
                    help='output JSON path, relative to the repository root')
    ap.add_argument('--date', default='20261126', help='date stamp for the default name')
    args = ap.parse_args()

    package = Path(args.package)
    if not package.is_absolute():
        package = (ROOT / package).resolve()
    listing_path = package / 'release.json'
    if not listing_path.is_file():
        sys.exit(f'refusing to record: {listing_path} missing '
                 f'(run tools/release_package.py first)')

    out = Path(args.out.replace('<date>', args.date))
    if not out.is_absolute():
        out = ROOT / out

    listing = json.loads(listing_path.read_text(encoding='utf-8'))
    manifest = json.loads((ROOT / 'data' / 'manifest.json').read_text(encoding='utf-8'))
    published = sorted((r for r in manifest['rows'] if r.get('published_corpus')),
                       key=lambda r: r['run_id'])

    exports = {p.name[:-len('.export.ndjson')]: p
               for p in (package / 'data' / 'raw').glob('*.export.ndjson')}
    expected = {r['run_id'] for r in published}
    if set(exports) != expected:
        missing = sorted(expected - set(exports))
        extra = sorted(set(exports) - expected)
        sys.exit(f'refusing to record: package does not match the manifest; '
                 f'missing {missing[:3]} extra {extra[:3]}')

    rounds = [{'run_id': row['run_id'],
               'date': row['date'],
               'preset': row['preset'],
               'tier': row['tier'],
               'gate': row['gate'],
               'export_bytes': exports[row['run_id']].stat().st_size}
              for row in published]

    payload = {
        'package': package.name,
        'built_from_commit': git_commit(),
        'generated_from_manifest': 'data/manifest.json',
        'rebuild': f'python tools/release_package.py --out {package.relative_to(ROOT).as_posix()}',
        'verify': f'python tools/verify_release_package.py {package.relative_to(ROOT).as_posix()}',
        'rounds': len(rounds),
        'files': listing['files'],
        'bytes': listing['bytes'],
        'with_telemetry': listing['with_telemetry'],
        'tiers': listing['tiers'],
        'gate': listing['gate'],
        'axis': listing['axis'],
        'licence': {'data': 'CC BY 4.0', 'code': 'MIT',
                    'files': ['data/LICENSE', 'LICENSE.md', 'LICENSE']},
        'contents': rounds,
    }

    out.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + '\n'
    data = text.encode('utf-8')
    assert not data.startswith(b'\xef\xbb\xbf')
    out.write_bytes(data)
    print(f'wrote {out.relative_to(ROOT).as_posix()} {len(data)} B, '
          f'{len(rounds)} round(s), {payload["files"]} file(s), '
          f'{payload["bytes"] / 1e6:.1f} MB')


if __name__ == '__main__':
    main()
