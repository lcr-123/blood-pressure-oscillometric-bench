# Offline pressure-step audit of the 100/65 series (2026-10-29)

This is a post hoc, read-only audit of the three complete strict-verified
captures in `prospective-low-waveform-results-20261029.md`. It does not
alter the frozen protocol or its decision: L1 and L3 passed, L2 returned
`insufficient_bins`, and the required 3/3 lower-condition criterion failed.
The conditional six-curve comparison was not performed.

## Reproduction

Run from the repository root:

```powershell
python 'blood pressure monitor/tools/bp_step_audit.py' tmp/capture_export_20261029-115718.verified.ndjson tmp/capture_export_20261029-120105.verified.ndjson tmp/capture_export_20261029-120520.verified.ndjson
```

The audit script SHA-256 is
`9DBFFA2395096711E19164983FC66E9D7B694E46CC36D910168A9120777C5220`.
The L1/L2/L3 verified-input SHA-256 values are respectively
`7B634AB0131734330288571FD750AB8CDE804BFF68E27DD4831E52377ED25E6D`,
`05053E1ECAB8B38D5EB6AC5C7FA7C6FAA135F7A09F728B52EF8865E5D580D750`,
and `C0BCDCB60D0BDE653A043D2134DEB10601A70603015A6B8F6F5C07DBE69F8C40`.
The script uses the strict decoder, then calls the existing study function
with upper pressure 130 mmHg and padding 0/20/40/60 samples. The 40-sample
result is the prespecified one; other paddings are sensitivity checks only.

## Observations

| Slot | >=5 mmHg adjacent falls | Samples within +/-40 of a fall in 50-130 mmHg | Padding 0/20/40/60: clean beats | Padding 0/20/40/60: occupied bins |
| --- | ---: | ---: | --- | --- |
| L1 | 0 | 0/1404 | 44/44/44/44 | 14/14/14/14 |
| L2 | 6 | 405/1403 (28.9%) | 36/28/24/20 | 13/6/6/6 |
| L3 | 3 | 49/1533 (3.2%) | 46/45/45/44 | 13/12/12/12 |

L2's six falls, indexed from the first deflation sample, are:

| Time (s) | Before -> at (mmHg) | Immediate fall | Net change 25 ms later | Net change 100 ms later |
| ---: | ---: | ---: | ---: | ---: |
| 14.4 | 106.88 -> 100.87 | -6.01 | -2.46 | -2.44 |
| 16.8 | 100.43 -> 94.94 | -5.50 | -2.51 | -2.54 |
| 20.4 | 92.59 -> 87.47 | -5.13 | -1.79 | -1.95 |
| 22.8 | 86.81 -> 80.89 | -5.92 | -2.24 | -2.68 |
| 33.4 | 60.53 -> 55.03 | -5.50 | -1.89 | -2.06 |
| 40.0 | 47.73 -> 42.01 | -5.72 | -1.62 | -1.76 |

The first four falls span approximately 107 to 81 mmHg. All six partly
rebound at the next 25 ms sample. The final fall starts below the study's
50 mmHg lower boundary. The export's valve aggregate places all six in
the first 25 ms bin of the recorded 200 ms valve schedule. L3 also has
three falls, two near the 130 mmHg upper boundary and one below 50 mmHg;
only 49 in-band samples are near them. L1 has none.

With zero step padding, L2 would have 13 occupied bins and a 77.39 mmHg
diagnostic fitted peak. At the frozen 40-sample padding, only six bins
remain, below the required eight. Thus the **software rejection path is
accounted for by step-adjacent beat exclusion** in this capture. Shrinking
the padding after seeing L2 cannot change the locked 2/3 verdict.

All three exports have `raw_kind=2`. Their pressure `p` is the calibrated
transform of exported voltage `v` using slope 82.326 mmHg/V and intercept
-19.887 mmHg, with at most 0.00001 mmHg numerical residual. These are
not independent measurements. The phase association and partial rebound
support targeted investigation of the pneumatic/control/sensing chain,
but there is no synchronized independent pressure trace or per-pulse valve
on-time history here to distinguish BP Pump 2, valve, tubing, sensor, ADC,
or timing effects. No pressure calibration, firmware algorithm, or hardware
setting was changed for this audit.

## Validation boundary

The command above only reads saved NDJSON files. It needs no MCU pins,
serial port, BP Pump 2 connection, power, or ground to run; it cannot
inflate or actuate either valve. The expected output is the table above
and a successful strict decode. No firmware C file changed, so there is
no Keil project sync, build, or download for this audit.

If obtaining new non-human captures later, retain the established ADS1115
on PB6/PB7, USART3 bridge on PB10/PB11, valves on PC0/PC1, pump relay on
PC8, External Cuff fixture, verified supplies and common ground. After any
reconnection, check shorts/polarity with power off, then measured supply
and logic levels before operation. Confirm fresh sealed near-zero serial
pressure, calibration/ADS/fault/pin status and the protocol's pressure
abort limits before inflation. After a run, use `vent` -> fresh near-zero
pressure -> `seal` and confirm new sealed-zero samples. These are the
existing non-human acquisition gates, not actions performed by this audit.
