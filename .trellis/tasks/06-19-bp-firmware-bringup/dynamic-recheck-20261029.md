# Dynamic 100/65 recheck after isolated PC1 test

## Setup and safety

On 2026-10-29 the operator confirmed User Defined 100/65 mmHg, 80 BPM,
0.7 cc, External Cuff, unchanged non-human fixation, and PC1 reconnected
to the established cuff pressure path. The CH340 serial stream disappeared
before acquisition; no pump command was sent. After reconnection, 100 fresh
samples displayed 0.0 mmHg. `tmp/linkpad_capture_io.py preflight`
reported cal VALID 82.326/-19.89, ADS ONLINE/errors0/recoveries0, fault
NONE, PC0/PC1 LOW, PC8 HIGH, pump OFF, and 101 fresh near-zero samples.
The raw zero sensor voltage was about 0.223 V, which the stored linear
calibration maps to approximately -1.5 mmHg before firmware clipping.
Thus displayed 0.0 did not prove an exact zero baseline; no calibration
coefficient was changed.

One `tmp/linkpad_lowpressure_check.py --user-defined` run set target
150 mmHg with a 165 mmHg sampled host abort limit. It reached 151.8
mmHg, naturally completed 2009 samples over 50.200 s with dropped0,
and reported firmware 118/57 mmHg, 56 BPM, valid1. These are firmware
outputs, not reference BP accuracy. The host issued `stop`, then `vent`,
confirmed fresh pressure <=2 mmHg, immediately `seal`ed PC1, and restored
target50. A post-seal preflight detected rebound to 2.5 mmHg, so export
was deferred. A second `vent` produced 100 fresh 0.0 samples; `seal`
followed immediately. Export preflight passed with PC0/PC1 LOW, PC8 HIGH,
pump OFF, cal VALID, ADS ONLINE, and 101 fresh 0.0 readings. A later
five-second snapshot also had 101 fresh 0.0 readings.

## Capture and analysis

- Acquisition bridge log: `tmp/linkpad_user_defined_20261029-210438.ndjson`.
- Raw export: `tmp/capture_export_20261029-211027.ndjson`, SHA-256
  `101156A9FE45D749C11C8FCE36A59BEC16CD7D31C2492FE82BD99D1B0E5E0D63`.
- Strict verified `/3` export:
  `tmp/capture_export_20261029-211027.verified.ndjson`, SHA-256
  `8446ADBA00AC521E3586168314B4C0DA3BFF37D39256F67B9689218F037FF5AA`.
  Exact 25 ms MCU intervals, n2009/dropped0, count/order/FNV valid.
  Production-C replay matched exported envelopes, features, and validity
  bit for bit; see matching CSV and `.replay.json` files.
- Valve diagnostics: 252 actual PC1 commands, period200 ms, on-time1-7 ms.
  Three >=5 mmHg falls were retained in `/3` step rows, all 17 ms after
  the most recent pulse command. At sample indices184/752/968, the falls
  were -5.92/-5.14/-5.10 mmHg from 125.54/88.30/70.65 mmHg, with
  partial recovery at the next 25 ms sample. The corresponding commanded
  on-times were 7/5/5 ms.
- The earlier 100/65 L2 capture had six similar falls of approximately
  5-6 mmHg, all in the first 25 ms valve phase bin. The new `/3` trace
  resolves association to 17 ms and individual commanded on-times.
- The label-free offline pulse estimate was 80 BPM, while firmware emitted
  56 BPM. The height fit gave a diagnostic center of 79.0 mmHg, but its
  robustness screen **rejected** a 20 mmHg gap between occupied pressure
  bins. This is not a valid MAP or a replacement BP result.

The sealed Pressure Source test with PC1 isolated from the pressurized
line had at most about 0.043 mmHg adjacent phase change. Reappearance of
5-6 mmHg partial-rebound notches when PC1 is again in the dynamic cuff
path makes a pressure-dependent pneumatic interaction plausible. The
capture still has only one pressure sensing chain; voltage and reported
pressure are the same calibrated signal, not independent measurements.
Do not assign the physical cause uniquely to PC1, tubing, or BP Pump 2,
or change the BP algorithm on this evidence. No new wiring, supply,
firmware, or clinical-use claim is authorized by this run.
