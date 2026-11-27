"""Verify that a frozen scoring configuration has not drifted.

Run before scoring any prospective round, and after any edit to tools/.

Three things are frozen and all three matter:

  * the estimator (tools/reference_bp.py) and its constants, which turns a waveform
    into a pressure;
  * the validity gate (tmp/validity_v2.py from freeze v2 onward), which decides
    whether a capture is scored at all;
  * from freeze v6 onward, the pressure axis the baseline was captured on and the
    tool that recomputes the baseline, which together make the recorded numbers
    checkable rather than merely asserted.

Freeze v1 had no gate. That is why one Preset 2 round whose deflate valve failed
was scored rather than refused, and why the record is kept unchanged instead of
being quietly patched: a holdout whose rules move after the fact is not a holdout.

The same reasoning is why v6 exists. The three records written before 2026-11-26
hash code but do not pin the axis, so after the 2026-11-26 refit they verified as
intact while none of them could reproduce the baseline numbers they record. Their
numbers were not wrong when written; they were simply never checkable. v6 pins the
axis and ships a determinism-guaranteed recomputation, so for v6 -- and only for v6,
because introducing a new failure mode into the older records would retroactively
break a published holdout -- this script re-runs the baseline and compares numbers.

Usage:
    python tools/verify_freeze.py            # check every freeze record
    python tools/verify_freeze.py --list     # list records only
    python tools/verify_freeze.py --name reference_bp_v6   # one record
"""
import hashlib
import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOLS = ROOT / 'data' / 'protocols'


def records():
    return sorted(PROTOCOLS.glob('reference_bp_freeze_v*.json'))


def hash_file(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def check_recompute(record, failures):
    """Re-run the baseline and compare it with the recorded numbers.

    Only records that declare `pressure_axis` and `recompute_method` are checked.
    The three earlier records cannot be: they pin neither, and their numbers are
    only reproducible on the axis they were captured on, which is not something
    the record states. Leaving them unchecked is deliberate -- see the docstring.
    """
    method = record.get('recompute_method')
    axis = record.get('pressure_axis')
    if not method and not axis:
        return
    if not method or not axis:
        # A record that declares one half of the mechanism and not the other has been
        # edited into a state where its baseline silently stops being checkable. Treat
        # that as drift rather than as a legacy record.
        failures.append('record declares '
                        + ('recompute_method' if method else 'pressure_axis')
                        + ' but not '
                        + ('pressure_axis' if method else 'recompute_method')
                        + ': its baseline would not be checked')
        return
    tool = ROOT / method['path']
    actual = hash_file(tool)
    if actual is None:
        failures.append(f'recompute tool missing: {method["path"]}')
        return
    if actual != method['sha256']:
        failures.append(f'recompute tool changed: frozen {method["sha256"][:16]}'
                        f' != current {actual[:16]}')
        return
    print(f'   ok  recompute tool {actual[:16]}')

    expected = record.get('baseline_report_sha256')
    if not expected:
        failures.append('record claims a recompute method but pins no baseline_report_sha256')
        return
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'baseline.json'
        command = [sys.executable, str(tool),
                   '--axis-slope', repr(axis['slope']),
                   '--axis-intercept', repr(axis['intercept']),
                   '--capture-slope', repr(axis.get('capture_slope', axis['slope'])),
                   '--capture-intercept', repr(axis.get('capture_intercept',
                                                         axis['intercept'])),
                   '--tier', record.get('baseline_tier', 'frozen_baseline_v2'),
                   '--out', str(out)]
        run = subprocess.run(command, capture_output=True, text=True)
        if run.returncode != 0:
            failures.append(f'baseline recomputation failed (exit {run.returncode}): '
                            f'{(run.stderr or run.stdout).strip()[:300]}')
            return
        got = hash_file(out)
    if got is None:
        failures.append('baseline recomputation produced no file')
        return
    if got != expected:
        failures.append(f'baseline not reproducible: record pins {expected[:16]}'
                        f' but recomputation gives {got[:16]}')
        return
    print(f'   ok  baseline reproduces {got[:16]}')


def check_record(record_path):
    record = json.loads(record_path.read_text(encoding='utf-8'))
    failures = []
    notes = []
    print(f'== {record["name"]}  ({record_path.name})')

    estimator = ROOT / record['estimator']['path']
    actual = hash_file(estimator)
    if actual is None:
        failures.append(f'estimator missing: {record["estimator"]["path"]}')
    elif actual != record['estimator']['sha256']:
        failures.append(f'estimator changed: frozen {record["estimator"]["sha256"][:16]}'
                        f' != current {actual[:16]}')
    else:
        print(f'   ok  estimator {actual[:16]}')

    report = record.get('baseline_report')
    if report:
        report_hash = hash_file(ROOT / report)
        if report_hash is None:
            notes.append(f'baseline report missing: {report}')
        elif report_hash != record['baseline_report_sha256']:
            failures.append(f'baseline report changed: frozen '
                            f'{record["baseline_report_sha256"][:16]} != current '
                            f'{report_hash[:16]}')
        else:
            print(f'   ok  baseline report {report_hash[:16]}')

    gate = record.get('validity_gate')
    if gate:
        gate_hash = hash_file(ROOT / gate['path'])
        if gate_hash is None:
            failures.append(f'validity gate missing: {gate["path"]}')
        elif gate_hash != gate['sha256']:
            failures.append(f'validity gate changed: frozen {gate["sha256"][:16]}'
                            f' != current {gate_hash[:16]}')
        else:
            print(f'   ok  validity gate {gate_hash[:16]}')
            sys.path.insert(0, str((ROOT / gate['path']).parent))
            try:
                module = __import__(Path(gate['path']).stem)
            except ImportError as exc:
                failures.append(f'cannot import validity gate: {exc}')
            else:
                for name, frozen in gate.get('constants', {}).items():
                    current = repr(getattr(module, name, '<missing>'))
                    if current != frozen:
                        failures.append(f'gate constant {name} changed: frozen {frozen}'
                                        f' != current {current}')
                if not failures:
                    print(f'   ok  {len(gate.get("constants", {}))} gate constants')
    else:
        notes.append('no validity gate in this record; captures are scored on decode '
                     'success alone')

    axis = record.get('pressure_axis')
    if axis:
        print(f'   --  pressure axis {axis["slope"]:.4f} / {axis["intercept"]:.4f}'
              f' (captures: {axis.get("capture_slope", axis["slope"]):.4f}'
              f' / {axis.get("capture_intercept", axis["intercept"]):.4f})')
    else:
        notes.append('this record pins no pressure axis: its baseline numbers are only '
                     'reproducible on the axis the captures were taken on, which the '
                     'record does not state. Freeze v6 is the first record that does.')

    covered = record.get('covered_estimator')
    if covered:
        covered_hash = hash_file(ROOT / covered['path'])
        if covered_hash is None:
            failures.append(f'covered estimator missing: {covered["path"]}')
        elif covered_hash != covered['sha256']:
            failures.append(f'covered estimator changed: frozen {covered["sha256"][:16]}'
                            f' != current {covered_hash[:16]}')
        else:
            print(f'   ok  covered estimator {covered_hash[:16]}')
            sys.path.insert(0, str(ROOT / 'tools'))
            try:
                module = importlib.import_module(Path(covered['path']).stem)
            except ImportError as exc:
                failures.append(f'cannot import covered estimator: {exc}')
            else:
                bad = 0
                for name, frozen in covered.get('constants', {}).items():
                    current = repr(getattr(module, name, '<missing>'))
                    if current != frozen:
                        bad += 1
                        failures.append(f'covered constant {name} changed: frozen {frozen}'
                                        f' != current {current}')
                if not bad:
                    print(f'   ok  {len(covered.get("constants", {}))} covered constants')

    check_recompute(record, failures)

    sys.path.insert(0, str(ROOT / 'tools'))
    module_name = Path(record['estimator']['path']).stem
    try:
        estimator_module = importlib.import_module(module_name)
    except ImportError as exc:
        failures.append(f'cannot import estimator {module_name}: {exc}')
    else:
        for name, frozen in record['estimator']['constants'].items():
            current = repr(getattr(estimator_module, name, '<missing>'))
            if current != frozen:
                failures.append(f'constant {name} changed: frozen {frozen} != current {current}')
        if not failures:
            print(f'   ok  {len(record["estimator"]["constants"])} estimator constants '
                  f'({module_name})')

    for note in notes:
        print(f'   --  {note}')
    for line in failures:
        print(f'   FAIL {line}')
    print()
    return failures


def main():
    available = records()
    if not available:
        raise SystemExit(f'no freeze records under {PROTOCOLS}')

    if '--list' in sys.argv:
        for path in available:
            record = json.loads(path.read_text(encoding='utf-8'))
            axis = record.get('pressure_axis')
            tail = ('axis %.4f / %.4f' % (axis['slope'], axis['intercept'])) if axis \
                else 'no pinned axis'
            print(f'{record["name"]:20s} {path.name:34s} {tail}')
        return 0

    if '--name' in sys.argv:
        wanted = sys.argv[sys.argv.index('--name') + 1]
        available = [p for p in available
                     if json.loads(p.read_text(encoding='utf-8'))['name'] == wanted]
        if not available:
            raise SystemExit(f'no freeze record named {wanted}')

    total = 0
    for path in available:
        total += len(check_record(path))

    if total:
        print(f'{total} failure(s). The holdout is only valid if every record verifies. '
              'Either revert the change or declare a new freeze and capture a new set.')
        return 1
    print(f'{len(available)} freeze record(s) intact; prospective scoring is valid.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
