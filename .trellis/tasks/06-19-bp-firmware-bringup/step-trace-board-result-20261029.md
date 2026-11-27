# Instrumented 100/65 non-human trace (2026-10-29)

This exploratory run followed the locked L1/L2/L3 series. It is not a
replacement for L2, and the prospective 100/65 decision remains 2/3 failed.
The operator had previously confirmed User Defined 100/65 mmHg, 80 BPM,
0.7 cc, External Cuff and unchanged non-human fixture; this panel setting
was not electronically read back for the instrumented run.

## Software and safety gates

- Image `CAPTURE_STEP_TRACE_20261029` rebuilt with 0 errors/warnings.
  HEX SHA-256:
  `C5698327B557882934BE19102CC9BD420D2AA825885D49346ADED0D231F7A1DB`.
  Static RAM 63472/65536 B (2064 B headroom); known stack peak 1312 B,
  reserved stack 4096 B. The 2048 B RAM headroom floor passes by only 16 B.
- Before Keil SWD download, the serial preflight found sealed PC0/PC1 LOW,
  PC8 HIGH, pump OFF, ADS ONLINE, cal VALID 82.326/-19.887, errors and
  recoveries 0/0 and 93 fresh 0.0 mmHg samples. Download erased the Flash
  calibration. Inflation stayed blocked while `UNCAL`; the documented
  coefficients were restored and read back as VALID before the run.
- The non-human host used target 150 mmHg, observed-pressure abort at
  >=165 mmHg, 75 s acquisition deadline and fresh-pressure/fault checks.
  Observed peak was 152.0 mmHg. The natural capture held 2201/3300 points,
  dropped 0, duration 55000 ms with exact 25 ms MCU intervals. Firmware
  reported 120/68 mmHg, 33 BPM, valid1; label-free cadence was 80 BPM.
  Neither output is an independent BP accuracy check.
- First vent/low/seal closeout rebounded to 3.7-3.8 mmHg, so export was
  rejected by preflight. A second `vent` produced 100 fresh 0.0 mmHg
  samples; after `seal`, 92 fresh 0.0 mmHg samples and safe pins passed.
  Export completed. A later read-only preflight again found 93 fresh
  0.0 mmHg samples, safe pins, cal VALID and ADS errors/recoveries 0/0.
  This is the last observed state, not a claim about future live pressure.

## Complete `/3` evidence

Acquisition log: `tmp/linkpad_user_defined_20261029-123355.ndjson`, SHA-256
`BEECCE30EC4F86ED544ADE45FA4CB59B77290091688F1FF909B42F7543649EB3`.
Raw bridge export: `tmp/capture_export_20261029-123637.ndjson`, SHA-256
`D982E852509A1F613E7137D313F726F4E39B38A0782132C15633127CC5191100`.
Strict verified export: `tmp/capture_export_20261029-123637.verified.ndjson`,
SHA-256 `74BED86B1E967C877E69F58C0F1F1F6E55F2B11B14095A3F01BBF3484DA517A0`.
The matching `.csv` and `.replay.json` have the same export ID. The export
reported 276 actual PC1-open commands at 200 ms intervals, commanded
on-time 1-6 ms, seven >=5 mmHg adjacent pressure steps, and `trace_n=7`.
The strict decoder accepted all rows and FNV checksum. Production-C replay
matched envelope bits, feature bits and validity; maximum numerical
envelope/smooth error was 0.0 V.

| Sample | Elapsed (s) | Pressure before -> at (mmHg) | Step (mmHg) | Phase after PC1-open command (ms) | Commanded on-time (ms) |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 152 | 3.800 | 129.87 -> 120.64 | -9.23 | 23 | 6 |
| 153 | 3.825 | 120.64 -> 126.84 | +6.21 | 48 | 6 |
| 168 | 4.200 | 124.57 -> 118.00 | -6.57 | 23 | 5 |
| 1000 | 25.000 | 79.44 -> 73.48 | -5.96 | 23 | 5 |
| 1232 | 30.800 | 66.59 -> 61.22 | -5.37 | 23 | 5 |
| 1504 | 37.600 | 53.85 -> 47.41 | -6.45 | 23 | 5 |
| 1744 | 43.600 | 43.01 -> 37.20 | -5.81 | 23 | 5 |

Six falls share the 23 ms sample phase; the one >5 mmHg rise is the next
25 ms sample after the largest fall. Other falls also partly recover by
the next sample. The recorded time is MCU time after the GPIO-open command,
not a measurement of the valve's mechanical opening instant. The seven
events fit within the 12-event trace; no step trace was truncated.

The fixed 40-sample step-padding study retained 32 clean beats and 11
occupied bins, with a diagnostic fitted peak at 79.50 mmHg. Its robustness
screen still **rejected** the run (`weak_peak_support`: only two beats in
the strongest bin). The firmware's 33 BPM also differs from the independent
label-free 80 BPM estimate and remains a separate algorithm issue.

The exact phase alignment across this run and the earlier L2 supports a
valve-synchronous disturbance. It does not isolate pneumatic pressure
transients from valve-driver electrical coupling or sensing/timing effects;
the exported `p` and `v` are the same sensor chain, and no simultaneous
independent pressure reference or electrical trace was measured. The
commanded 5-6 ms widths cannot be treated as measured mechanical open
durations. No valve timing, pressure calibration or BP algorithm tuning
was changed based on this run.

## Phase-conditioned check of all cycles

Reproduce with:

```powershell
python 'blood pressure monitor/tools/bp_valve_phase_audit.py' tmp/capture_export_20261029-123637.verified.ndjson
```

Script SHA-256:
`2AD4E23948A669BCA4FF2E98529391FD224FB68225B1BFF22872F6F3ADE6CAF4`.
For `/3` it uses the first exact step event as the phase anchor; for older
`/2` exports it uses the aggregate maximum fall. It requires exact 25 ms
samples and a recorded 200 ms valve period, then verifies all available
event phases and the complete reconstructed >=5 mmHg phase-bin counts.
The `/2` analysis has no per-event on-time evidence. The reconstruction
assumes the recorded 200 ms period held throughout each capture.

Within 50-130 mmHg, 172 cycles have a sample 23 ms after a PC1-open
command. The adjacent pressure change at that phase has median
-0.937 mmHg, including five falls of at least 5 mmHg. The other seven
sample phases have medians from -0.085 to +0.227 mmHg and no fall of
at least 5 mmHg. The following sample has median change +0.248 mmHg.
Across those two samples, median net change is -0.760 mmHg and no cycle
has a net fall of at least 5 mmHg. One of the six large falls in the
full seven-event table starts below 50 mmHg; the seventh event is a rise.

This supports a recurring phase-locked notch with occasional large
outliers. It does not separate an actual pneumatic transient from
electrical coupling into the one sensing chain. The existing locked
100/65 outcome and this run's rejected robustness screen are unchanged.

The same read-only command on the strict-verified L2 (`120105`) and L3
(`120520`) exports gives the following comparison. All three aggregate
phase-bin counts agree with the reconstruction:

| Capture | Anchor evidence | In-band first-phase cycles | Median first change (mmHg) | First-phase falls >=5 mmHg | Median following change (mmHg) | Median two-sample net (mmHg) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| L2 | `/2` maximum fall, phase 23 ms | 176 | -0.845 | 5 | +0.234 | -0.582 |
| L3 | `/2` maximum fall, phase 17 ms | 192 | -1.079 | 1 | +0.426 | -0.575 |
| Exploratory L4 | `/3` seven timed steps, phase 23 ms | 172 | -0.937 | 5 | +0.248 | -0.760 |

L1's `/2` aggregate has no >=5 mmHg event, so it supplies no absolute
valve-phase anchor for this reconstruction. This cross-run comparison
strengthens the evidence for a repeated valve-synchronous notch; it does
not identify whether the notch is a real cuff-pressure transient or an
electrical/sensing artifact.
