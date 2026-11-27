"""Smoke-test the syringe analysis pipeline on synthetic data with a known answer.

The point is to prove the offline math recovers a volume that was put in by hand, before another
hardware run is spent. If this test cannot return 150.0 cc for a simulated 150 cc loop, the analysis
is wrong and no amount of careful operating will fix it.

Simulated loop: V = 150 cc, ATM = 760 mmHg, start 150 mmHg gauge, leak 0.108 mmHg/s.
Pull 0 -> 10 mL, then 10 -> 20 mL. The log is written in the exact format the bridge produces, so
the reader in syringe_analyze_20261109.py is exercised too, not bypassed.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OMNI = ROOT / 'tmp' / 'omniprobe'
NAME = 'synthetic_volume_check'
ATM = 760.0
SLOPE = 81.529
INTERCEPT = -20.03
TRUE_VOLUME = 150.0
LEAK = 0.108          # mmHg/s, positive means pressure falls
DT = 0.05

events = []
samples = []


def add(seconds, p_gauge):
    """Emit one pressure line the way the firmware prints it."""
    sensor_mv = (p_gauge - INTERCEPT) / SLOPE * 1000.0
    ads_mv = sensor_mv / 1.3799
    raw = int(round(ads_mv / 0.125))
    samples.append(dict(t=seconds, raw=raw, ads=int(round(ads_mv)),
                        sensor=int(round(sensor_mv)), p=p_gauge))


def plateau(t_start, t_end, p0, label):
    """Constant volume: pressure falls at the leak rate."""
    t = t_start
    while t <= t_end:
        add(t, p0 - LEAK * (t - t_start))
        t += DT
    return dict(label=label, t_first=t_start, t_last=t_end,
                median=p0 - LEAK * (t_end - t_start) / 2,
                rate=-LEAK, n=int((t_end - t_start) / DT))


base_epoch_ms = 1794200000000
t = 0.0
plateau_records = []

# settle, then plateau A at g = 0 mL
plateau_records.append(plateau(0.0, 60.0, 150.0, 'A'))
events.append(dict(label='plateau_A_done', t_ms=int(60 * 1000)))

p_a_end = 150.0 - LEAK * 60.0
p_b_start = (ATM + p_a_end) * (TRUE_VOLUME + 0.0) / (TRUE_VOLUME + 10.0) - ATM
events.append(dict(label='pull_1_done', p_before=round(p_a_end, 3), t_before_ms=int(60 * 1000)))
plateau_records.append(plateau(60.0 + DT, 105.0, p_b_start, 'B'))
events.append(dict(label='plateau_B_done', t_ms=int(105 * 1000)))

p_b_end = p_b_start - LEAK * (105 - 60)
p_c_start = (ATM + p_b_end) * (TRUE_VOLUME + 10.0) / (TRUE_VOLUME + 20.0) - ATM
events.append(dict(label='pull_2_done', p_before=round(p_b_end, 3), t_before_ms=int(105 * 1000)))
plateau_records.append(plateau(105.0 + DT, 150.0, p_c_start, 'C'))
events.append(dict(label='plateau_C_done', t_ms=int(150 * 1000)))

# The report records plateau windows in epoch seconds, which is what the acquisition script does.
for record in plateau_records:
    record['t_first'] += base_epoch_ms / 1000.0
    record['t_last'] += base_epoch_ms / 1000.0
for event in events:
    if 't_before_ms' in event:
        event['t_before_ms'] += base_epoch_ms

with open(OMNI / f'{NAME}.ndjson', 'w', encoding='utf-8') as handle:
    for sample in samples:
        text = (f'[Pressure] raw={sample["raw"]} ads={sample["ads"]}mV '
                f'sensor={sample["sensor"]}mV est=0.0mmHg VALID')
        handle.write(json.dumps({'type': 'text', 'lines': [
            dict(timestamp=int(base_epoch_ms + sample['t'] * 1000),
                 direction='rx', text=text, truncated=False)]}, ensure_ascii=False) + '\n')

report = dict(protocol='three_plateau_syringe_volume',
              graduations_ml=dict(g1=0.0, g2=10.0, g3=20.0),
              plateaus=plateau_records, events=events, synthetic=True,
              note=f'simulated V={TRUE_VOLUME} cc, leak {LEAK} mmHg/s, no noise')
(OMNI / f'{NAME}.events.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print(f'synthetic data: {len(samples)} samples over {samples[-1]["t"]:.0f} s, '
      f'true V = {TRUE_VOLUME} cc')
print(f'  A {150.0:7.2f} mmHg -> B {p_b_start:7.2f} -> C {p_c_start:7.2f} (gauge)')
print()

sys.stdout.flush()
result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'syringe_volume_analysis.py'),
                         NAME, '--g1', '0', '--g2', '10', '--g3', '20'],
                        capture_output=True, text=True, encoding='utf-8')
print(result.stdout)
if result.returncode != 0:
    print(result.stderr)
    raise SystemExit('analysis failed')

if str(int(TRUE_VOLUME)) not in result.stdout:
    print(f'CHECK: the printed volumes should contain {TRUE_VOLUME:.0f}; they do not')
else:
    print(f'CHECK PASS: the analysis recovered the {TRUE_VOLUME:.0f} cc that was simulated')
