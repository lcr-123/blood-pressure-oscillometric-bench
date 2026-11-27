# Prospective 100/65 non-human waveform results (2026-10-29)

Protocol: `prospective-low-waveform-protocol-20261029.md`, SHA-256
`4ACBF5BFFB7466CC9AEAEF977FC2910C246F649BAE9AB684939543D8AFFDD05F`
before L1. The operator's "OK" immediately before L1 was taken as confirmation
of User Defined 100/65 mmHg, 80 BPM, 0.7 cc, External Cuff, unchanged
non-human fixation and connections. The panel settings were not electronically
recorded by the capture protocol. All six frozen tool hashes were checked
before L1 and the analysis functions were unchanged through L3.

## Planned slots

| Slot | Acquisition log | Complete export | Peak observed | n/3300 | Firmware result | Raw MAP/DBP | MAP-to-DBP | Clean beats | Occupied bins | Fitted peak | Locked screen |
| --- | --- | --- | ---: | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |
| L1 | `tmp/linkpad_user_defined_20261029-115441.ndjson` | `tmp/capture_export_20261029-115718.ndjson` | 151.5 mmHg | 2249 | 119/60, 70 BPM, valid | 81.09/65.71 mmHg | 7.800 s | 44 | 14 | 79.49 mmHg | `diagnostic_only`, pass |
| L2 | `tmp/linkpad_user_defined_20261029-115906.ndjson` | `tmp/capture_export_20261029-120105.ndjson` | 151.1 mmHg | 2193 | invalid | 86.13/86.64 mmHg | 0.575 s | 24 | 6 | none | `insufficient_bins` |
| L3 | `tmp/linkpad_user_defined_20261029-120229.ndjson` | `tmp/capture_export_20261029-120520.ndjson` | 151.4 mmHg | 2345 | 121/70, 56 BPM, valid | 84.21/75.38 mmHg | 5.250 s | 45 | 12 | 79.97 mmHg | `diagnostic_only`, pass |

Every acquisition was natural and retained in its planned slot. All have
dropped=0 and exact 25 ms MCU tick intervals. Each `/2` export passed strict
count/order/FNV decoding and production-C replay: envelope, feature and
validity bits matched exactly, and maximum envelope/smooth error was 0.0 V.
The independent label-free pulse estimator returned 80 BPM in all three;
the firmware's 70/56 BPM values in L1/L3 therefore need separate scrutiny.
The fitted peaks are beat-height diagnostics, not reference MAP or BP.

Raw/verified export SHA-256:

| Slot | Raw bridge export | Strict verified NDJSON |
| --- | --- | --- |
| L1 | `BC67808C1C4A31100924E899450C32D6B6353182675C85CFEC446D04F2AB507B` | `7B634AB0131734330288571FD750AB8CDE804BFF68E27DD4831E52377ED25E6D` |
| L2 | `1DBE8A9FDC5400B6D3FAE98B4AD66116069869D07DFCC75B23264169C7F80AC4` | `05053E1ECAB8B38D5EB6AC5C7FA7C6FAA135F7A09F728B52EF8865E5D580D750` |
| L3 | `52FC1D6507FD3ABD43FFF0D3BC0FC117CD088160C650D5D0D329B94388CDFD0E` | `C0BCDCB60D0BDE653A043D2134DEB10601A70603015A6B8F6F5C07DBE69F8C40` |

Companion `.verified.ndjson`, `.csv` and `.replay.json` artifacts use each
export's ID. L2 has `calc=3`; its invalidity is consistent with the raw
DBP feature exceeding MAP by 0.51 mmHg, 0.575 s after the MAP feature.
The strict transport and replay succeeded despite the invalid BP result.

## Prespecified decision

The lower-condition screen succeeded in **2/3** slots, so the locked 3/3
within-condition repeatability criterion was **not met**. L1/L3 fitted
centers differ by 0.48 mmHg, but excluding L2 to compute a three-run range
would violate the protocol. Because the lower cohort failed its gate, the
prespecified six-curve nonoverlap comparison against the 150/100 cohort
was **not performed**. Do not report fixture discrimination or use these
captures to tune firmware MAP bounds, ratios, offsets or pulse calculation.

The L2 study detected 53 voltage peaks but retained only 24 clean beats
after its existing beat/pressure-step gates, versus 44 and 45 in L1/L3.
Only six 5 mmHg bins held at least two beats (52.5, 67.5, 72.5, 77.5,
112.5 and 117.5 mmHg), below the required eight. The valve diagnostic
reported six >=5 mmHg pressure steps in L2, versus zero in L1 and three
in L3. This explains the `insufficient_bins` status under the frozen
filter; these data do not isolate whether the physical source was BP Pump 2,
the pneumatic path, valve action or pressure sensing. The next useful work
is read-only sensitivity analysis of L2's step locations and beat
exclusions, explicitly exploratory and separate from this locked verdict.

Post hoc, **outside the locked decision**, step padding 0/20/40/60 samples
gave L2 36/28/24/20 clean beats and 13/6/6/6 occupied bins. Only padding0
yielded `diagnostic_only` plus robustness pass, with a 77.39 mmHg fitted
peak. This sensitivity does not replace the locked padding40 result.
L1 had no >=5 mmHg step and was unchanged at all four padding settings;
L3 retained 12-13 bins and passed at all four. L2's six steps occur at
14.4, 16.8, 20.4, 22.8, 33.4 and 40.0 s after deflation capture start,
with pressure changes -6.01, -5.50, -5.13, -5.92, -5.50 and -5.72 mmHg.
All six occupy phase bin0 of the recorded 200 ms valve schedule. The
phase association is evidence for targeted pneumatic/control diagnosis,
but the export has no independent simultaneous pressure or per-pulse
valve-on history to assign a unique cause.

## Safety and closeout

Each run used the host's target150, observed >=165 mmHg abort,
75-second deadline, fresh pressure and firmware fault checks. Each ended
with stop -> vent -> fresh low -> seal; the first sealed five-second
snapshots rebounded to 3.8, 3.0-3.5 and 3.9 mmHg for L1/L2/L3.
No export was attempted at those readings. A second vent yielded 100
fresh 0.0 mmHg samples, followed by 100/101/100 fresh 0.0 mmHg samples
after sealing, before the respective exports. Final read-only preflight
`tmp/capture_preflight_20261029-120704.ndjson` confirmed sealed PC0/PC1
LOW, PC8 HIGH, pump OFF, cal VALID 82.326/-19.887, ADS ONLINE,
errors/recoveries 0/0 and 92 fresh 0.0 mmHg readings. No human contact,
wiring, supply, calibration, firmware C or Keil image change occurred.
Any future non-human run retains the documented PB6/PB7 ADS1115,
PB10/PB11 USART3, PC0/PC1 valves, PC8 pump relay, established power/common
ground, unpowered polarity/short check after reconnection, fresh sealed
zero/ADS/cal/pins gate, and vent -> fresh zero -> seal closeout.
