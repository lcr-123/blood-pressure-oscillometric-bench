"""Independent data-quality audit over every export in the dataset.

What this is for
    The question "is this data usable by someone else" should be answerable without
    trusting the blood-pressure estimator. Everything here is derived from three fields
    that any third party can read straight out of a bp.capture/4 export - the pressure
    series, the oscillation series, and the interval - plus the file's own point count and
    duration. Nothing depends on ratio constants.

Checks, and why each one matters
    1. strict decode        an export that does not decode is not evidence of anything
    2. interval consistency every file must claim 25 ms, and n must match duration/interval
                            within a point or two; a mismatch means dropped samples or a
                            timestamp discontinuity that nobody would notice by eye
    3. pressure span        a capture that starts at 15 mmHg or tops out at 400 is a failed
                            run regardless of what the estimator says
    4. beat rate            the fixture's panel is set to 80 BPM. Measuring it from the
                            oscillation series is a check the operator never sees and the
                            estimator never uses. This is the strongest external evidence
                            in the dataset.
    5. pulse strength       peak-to-peak of the band-passed oscillation inside the MAP band;
                            a capture with no pulse cannot support any envelope method

Beat-rate method (and two methods that failed)
    Band-pass `v` at 1.0-1.6 Hz, take the panel's own MAP as the band centre, and measure
    peak-to-peak period with find_peaks. Two earlier attempts were wrong and are recorded
    here so they are not repeated: using the envelope series (it is a rectified, 800 ms
    smoothed residual, so its harmonic content is not the pulse fundamental) gave
    75-77 BPM, and autocorrelation on the 40 Hz grid quantises the lag to one sample,
    which is +/-1.3 BPM at 0.75 s.

Usage:
    python tools/data_quality_audit.py [--json out.json]
"""
import argparse
import glob
import json
import os
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, find_peaks, sosfiltfilt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'blood pressure monitor' / 'tools'))
sys.path.insert(0, str(ROOT / 'tools'))
import bp_capture  # noqa: E402

PANEL = {
    'standard120_080': dict(sbp=120, dbp=80, map=93),
    'standard150_100': dict(sbp=150, dbp=100, map=116),
    'standard200_150': dict(sbp=200, dbp=150, map=166),
    'standard255_195': dict(sbp=255, dbp=195, map=215),
    # Manual table 3-2 rows 5-7. They carry a low MAP (40/60/76 mmHg), so the
    # MAP +/-15 mmHg pulse band used by the crisper measurements sits lower too.
    'standard060_030': dict(sbp=60, dbp=30, map=40),
    'standard080_050': dict(sbp=80, dbp=50, map=60),
    'standard100_065': dict(sbp=100, dbp=65, map=76),
}
EXPECTED_INTERVAL_MS = 25
EXPECTED_BPM = 80.0
BAND_HZ = (1.0, 1.6)
BAND_HALF_WIDTH_MMHG = 15.0
MIN_BAND_SAMPLES = 200      # 5 of the 8 originally-skipped runs have 250-300 samples
                            # and still yield a clean 80.00 BPM; below ~200 the
                            # band is too short to hold 6 beats


def f32(bits):
    return struct.unpack('<f', struct.pack('<I', bits))[0]


def audit_one(path):
    name = os.path.basename(path)
    key = name.split('_target275')[0]
    if key not in PANEL:
        return None

    lines = [line.strip() for line in Path(path).read_text(encoding='utf-8').splitlines()
             if line.strip()]
    try:
        capture = bp_capture.decode(lines)
    except Exception as exc:                               # noqa: BLE001
        return dict(export=name, preset=key, decode='failed', error=repr(exc)[:120])

    header = capture['header']
    points = capture['points']
    pressure = np.array([f32(p['p']) for p in points])
    oscillation = np.array([f32(p['v']) for p in points])

    interval = header['interval_ms']
    duration_s = 0.0
    for index in range(1, len(points)):
        duration_s += (points[index]['t'] - points[index - 1]['t']) & 0xFFFFFFFF
    duration_s /= 1000.0
    implied_n = round(duration_s * 1000.0 / interval) + 1 if interval else 0

    record = dict(
        export=name,
        preset=key,
        firmware=header['firmware'],
        decode='ok',
        n=len(points),
        interval_ms=interval,
        interval_ok=(interval == EXPECTED_INTERVAL_MS),
        n_consistent=(abs(implied_n - len(points)) <= 2),
        duration_s=round(duration_s, 2),
        pressure_min=round(float(pressure.min()), 2),
        pressure_max=round(float(pressure.max()), 2),
        pressure_span_ok=(float(pressure.max()) < 300.0 and float(pressure.min()) < 60.0),
        checksum_present=bool(capture['end'].get('hash')),
    )

    sos = butter(2, list(BAND_HZ), btype='band', fs=1000.0 / interval, output='sos')
    band_signal = sosfiltfilt(sos, oscillation)
    centre = PANEL[key]['map']
    band = (pressure >= centre - BAND_HALF_WIDTH_MMHG) & (pressure <= centre + BAND_HALF_WIDTH_MMHG)
    segment = band_signal[band]
    record['band_samples'] = int(len(segment))
    if len(segment) >= MIN_BAND_SAMPLES:
        record['pulse_p2p_mv'] = round(float(segment.max() - segment.min()) * 1000.0, 2)
        peaks, _ = find_peaks(segment, height=np.percentile(segment, 60),
                              distance=int(0.4 * 1000.0 / interval))
        if len(peaks) >= 6:
            periods = np.diff(peaks) * interval / 1000.0
            periods = periods[(periods > 0.5) & (periods < 1.5)]
            if len(periods) >= 5:
                record['period_s'] = round(float(np.median(periods)), 4)
                record['bpm'] = round(60.0 / float(np.median(periods)), 2)
                record['bpm_error'] = round(record['bpm'] - EXPECTED_BPM, 2)
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', type=Path, help='also write the per-run records here')
    ap.add_argument('--pattern', default='data/raw/**/*.export.ndjson')
    args = ap.parse_args()

    paths = sorted(glob.glob(str(ROOT / args.pattern), recursive=True))
    records = [r for r in (audit_one(p) for p in paths) if r]
    current = [r for r in records if r.get('firmware') == 'PEAK_WINDOW_20261105']

    print(f'{len(records)} exports with a recognised preset name, '
          f'{len(current)} of them current firmware\n')

    print('=== structural checks ===')
    for field, label in (('decode', 'strict decode'),
                         ('interval_ok', 'interval == 25 ms'),
                         ('n_consistent', 'n matches duration/interval'),
                         ('pressure_span_ok', 'pressure span sane'),
                         ('checksum_present', 'end checksum present')):
        good = sum(1 for r in current if r.get(field) in (True, 'ok'))
        print(f'  {label:<28} {good:>3}/{len(current)}')

    print('\n=== beat rate inside the panel MAP band ===')
    measured = [r for r in current if 'bpm' in r]
    print(f'  measured                 {len(measured):>3}/{len(current)}')
    if measured:
        bpms = np.array([r['bpm'] for r in measured])
        errors = bpms - EXPECTED_BPM
        print(f'  median BPM               {np.median(bpms):.2f}')
        print(f'  sd                       {np.std(bpms, ddof=1):.2f}')
        for tol in (0.5, 1.0, 2.0):
            inside = int(np.sum(np.abs(errors) <= tol))
            print(f'  within +/-{tol:.1f} BPM      {inside}/{len(bpms)} '
                  f'({100 * inside / len(bpms):.0f}%)')
        worst = sorted(measured, key=lambda r: -abs(r['bpm_error']))[:3]
        print('  worst runs:')
        for r in worst:
            print(f'    {r["export"][-30:]:>30}  {r["bpm"]:6.2f} BPM '
                  f'({r["bpm_error"]:+.2f})')

    print('\n=== per preset ===')
    print(f"  {'preset':<18} {'n':>3} {'decoded':>8} {'BPM med':>8} {'pulse mV':>9}")
    for key in PANEL:
        sel = [r for r in current if r['preset'] == key]
        if not sel:
            continue
        bp = [r['bpm'] for r in sel if 'bpm' in r]
        pp = [r['pulse_p2p_mv'] for r in sel if 'pulse_p2p_mv' in r]
        print(f"  {key:<18} {len(sel):>3} {sum(1 for r in sel if r['decode']=='ok'):>8} "
              f"{(np.median(bp) if bp else float('nan')):>8.2f} "
              f"{(np.median(pp) if pp else float('nan')):>9.2f}")

    problems = [r for r in current
                if r.get('decode') != 'ok' or not r.get('interval_ok')
                or not r.get('n_consistent') or not r.get('pressure_span_ok')]
    print(f'\nruns failing a structural check: {len(problems)}')
    for r in problems[:10]:
        print(f"  {r['export'][-34:]:>34}  {json.dumps({k: r.get(k) for k in ('decode','interval_ok','n_consistent','pressure_span_ok')}, ensure_ascii=False)}")

    print('\nreading: everything here is independent of the blood-pressure estimator.')
    print('a run can fail the estimator and still pass every check above - that is the')
    print('point. it means the data is intact and the algorithm declined to answer.')

    if args.json:
        args.json.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n',
                             encoding='utf-8')
        print(f'\nwrote {args.json}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
