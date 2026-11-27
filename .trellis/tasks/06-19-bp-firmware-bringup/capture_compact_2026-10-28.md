# Compact capture: software evidence and non-human validation

## Software result

- New image marker: `CAPTURE_COMPACT_20261028`. The software increment was
  followed by a separately authorized Keil download and non-human baseline on
  2026-10-28; see the board result below.
- `BP_ALGO_MAX_SAMPLES=3300`. Pressure and input-voltage float32 values remain
  exact; the public sample getter reconstructs exact uint32 MCU ticks from a
  first-tick anchor and 1-byte intersample deltas. An interval outside 1..255 ms
  rejects the capture point and takes the existing SAMPLE_OVERFLOW caller path.
  The exporter refuses any capture with a nonzero dropped count.
- Real-C host regressions: 82/82 pass. They cover 3300 capacity, tick rollover,
  0/1/25/255/256 ms edges, production control emergency vent, complete `/2`
  exports at 2000/2800/3300 points, irregular tick replay, and old `/2` decode.
- Keil ARMCLANG V6.22 Rebuild: 0 errors, 0 warnings. Program size Code49308,
  RO6260, RW28, ZI63388. RAM budget 63416/65536, headroom2120 B;
  stack4096 B, known peak1304 B plus1024 B reserve. The new static budget passes
  by only 72 B above its 2048 B headroom floor. After the baseline and export,
  two runtime reads were used1536/free2560/reserved4096/saturated0.
- Build HEX SHA256:
  `537B9FFD10ABD21E39EC51CF04EC2E97EE56E0AEADE32B8DA0CF215CE0F6155D`.
  `bp_algorithm.c` and `bp_capture_export.c` are already registered in
  `MDK-ARM/blood pressure monitor.uvprojx`; no new compiled C/S source or include
  path was added. This is the artifact downloaded by the recorded Keil step;
  the board export independently reports the matching firmware marker.
- The four archived 150/100 runs projected 2992-3170 samples at target190,
  leaving 130 samples in the worst observed case under a 3300-point design.
  That projection assumes unchanged hold loss and average deflation rate; it
  does not establish physical capacity, waveform coverage or BP accuracy.

## Existing wiring and power boundary

Keep the already verified non-human setup and do not change supply rails:

- STM32 USART3 PB10 (TX)/PB11 (RX) to the existing CH340 debug serial path;
  keep the proven TX/RX crossing and common ground. I2C1 PB6/PB7 to ADS1115,
  with the MPXV5050GP pressure output through the existing verified input path.
- PC0 and PC1 remain the valve-control outputs; PC8 controls the existing
  low-trigger pump relay. SWD PA13/PA14 is the Keil programming connection.
- Keep BP Pump 2 External Cuff, the real cuff as a **non-human** volume, the
  existing pressure path to MPXV5050GP P1 and P2 open to atmosphere. Do not
  connect the cuff to a person during validation.
- With power removed, check wiring, polarity, ground continuity, shorts and
  tubing. Then power the existing setup and measure the already documented
  supply/logic nodes before running code. This increment adds no module and
  makes no new supply-voltage recommendation. Any changed module or supply
  requires its exact official datasheet and measured logic compatibility first.

## Board validation procedure

1. Rebuild the Keil `.uvprojx` with zero errors/warnings; run
   `python 'blood pressure monitor/tools/check_firmware_budget.py'` and confirm
   both source files remain visible in Keil. Download using the established
   Keil `UV4 -f` path only as a separate board step; full-chip erase may clear
   Flash calibration. Do not use pyocd for this Horco CMSIS-DAP v2 setup.
2. With no pressure applied, check `status`, `pins`, `fault`, `cal`, `stack` and
   fresh `[Pressure]` on USART3 at the existing serial settings. Require the
   new firmware marker, IDLE/manual OFF, ADS ONLINE, PC0/PC1 LOW, PC8 HIGH,
   pump OFF, valid calibration and near-zero pressure. If erased, restore only
   `cal write 82.326 -19.887` on unchanged hardware, then independently read
   back `VALID` and displayed `82.326/-19.89` before any inflation.
3. Run a non-human low-pressure 50 mmHg start/stop safety exercise. Verify
   commanded stop/emergency vent state and fresh pressure decay. Complete
   `vent` -> consecutive fresh est near 0 -> `seal`, confirming PC1 LOW.
4. Run one complete non-human 120/80, 80 bpm External Cuff baseline with the
   previously validated pressure setting and high-pressure hold. Inspect
   `[Capture] n=... capacity=3300 dropped=0`, `[Calc]`, `[BP]`/`DBGFAIL`, and
   `[Deflate] done; valve2 closed`. Any invalid BP remains invalid evidence.
   Finish `vent` -> fresh near-zero samples -> `seal`; the BP Pump 2 may stop
   automatically when external pressure disappears, so a panel Stop is only
   needed if pressure does not settle or the next run cannot start.
5. Export `/2` only after the safe low-pressure sealed preflight. Require full
   begin/point/valve/features/end checksum, exact MCU ticks, zero drops and
   production-C replay on the same firmware marker. Query `stack` twice after
   calculation/export; require reserved4096, saturated0, free>=1024, no ADS
   errors/recoveries, pump OFF and PC0/PC1 LOW, PC8 HIGH.
6. Higher-pressure 150/100 collection remains gated on the above result plus
   verification of the connected cuff/BP Pump 2 pressure ratings and a specific
   bounded sample-budget plan. Do not infer that the nominal 3300-point limit
   guarantees completion. On any overflow or sensor failure require emergency
   vent and no BP result; follow with `vent` -> fresh near-zero -> `seal` only
   after the pressure has safely fallen.

This is simulator and engineering evidence, not clinical or ISO 81060-2
accuracy validation.

## Board result, 2026-10-28

- Keil Full Chip Erase/Programming/Verify OK/Application running completed at
  16:26:50 (`tmp/compact_flash_20261028.log`). Restored the erased calibration
  to82.326/-19.887 with written+verified and independent VALID readback.
- Non-human target50 active-stop exercise passed: observed peak32.2mmHg,
  safe STOP pins and vent -> fresh near-zero -> seal. No inflation retry.
- User confirmed External Cuff120/80mmHg,80bpm and non-human cuff setup. One
  target150 run reached151.8mmHg, held, naturally completed2161/3300 points
  over54000ms, dropped0. Board BP106/80,84bpm valid1; calculation
  work1559ms/wall2264ms/max_step31ms. This checks the acquisition path, not
  numerical BP accuracy. Log: `tmp/linkpad_standard_20261028-163326.ndjson`.
- After the first vent/near-zero/seal, sealed pressure rebounded to3.1-3.5mmHg;
  the stricter export preflight correctly refused before `capture export` was
  sent. Cleanup repeated vent -> fresh zero -> seal; a new five-second snapshot
  was0.4-0.6mmHg. No calibration/threshold changes or new inflation followed.
  Rejected preflight log: `tmp/capture_export_20261028-163445.ndjson`.
- Retried export only: complete `/2` begin+2161points+valve+features+end,
  hash1601732005, markerCAPTURE_COMPACT_20261028. Strict decode and production-C
  replay passed; all ticks25ms, envelope/feature bits equal, validity equal,
  max envelope/smooth error0. Valve271 pulses,200ms period,1-5ms on-time,
  seven >=5mmHg steps, all in first25ms phase bin. Artifacts:
  `tmp/capture_export_20261028-163539.ndjson`, `.verified.ndjson`, `.csv`,
  `.replay.json`.
- Two independent post-export reads both used1536/free2560/reserved4096,
  saturated0; ADS errors0/recoveries0, calibration VALID, fresh near-zero,
  PC0/PC1 LOW,PC8 HIGH,pump OFF. Logs:
  `tmp/compact_postexport_stack1_20261028.ndjson` and
  `tmp/compact_postexport_stack2_20261028.ndjson`.
- The120/80 baseline uses2161/3300 points. A later user-authorized, bounded
  target190 non-human run completed3153/3300 points with147 points remaining.
  It validates one acquisition at190, not repeated capacity or a full3300-point
  transfer.
  The offline measured-rate diagnostic gives deflation134.99->14.8mmHg over54s
  (2.226mmHg/s) and projects2520/2700/2880 points at targets170/180/190,
  leaving780/600/420 points for this single baseline pattern. The actual
  target190 capture measured2.021mmHg/s and used3153 points, leaving147. Four
  historical150/100 patterns projected as few as130 remaining at190. The local
  Fluke BP Pump 2 official operator manual PN2196592 states its pressure
  measurement range is0..400mmHg, but the screenshot of the connected standard
  22-32cm electronic cuff does not show a pressure rating, and tubing/fitting
  ratings are not documented. The user authorized this single non-human190 run;
  it does not establish a rating or provide margin for reliable repeats.
- High-target harness `tmp/linkpad_lowpressure_check.py --target190` applied a
  205mmHg host ceiling, 105s acquisition timeout, firmware-fault/freshness
  aborts, single start/no retry, vent -> fresh low pressure -> seal, and target
  restore50. Offline fake-bridge suite:8/8 passed, including over-ceiling
  cleanup and retaining a complete invalid-BP waveform. No production firmware
  or calibration was changed.
- For the190 run, first post-seal telemetry rebounded to3.6-3.9mmHg. Repeated
  vent -> fresh samples0.0 -> seal, then observed another five seconds at0.0
  before export. No additional inflation occurred.
- The 150/100,80bpm External Cuff run reached190.4mmHg, naturally deflated, and
  captured3153/3300 points over78800ms with dropped0 and25ms ticks. Board result
 154/90,75bpm valid1; calculation work2267ms/wall3292ms/max_step33ms. Complete
  `/2` export hash3067838985 had395 valve pulses at200ms, on-time1-6ms and12
  >=5mmHg steps, all in phase0-24ms. Strict decode and production-C replay
  matched envelope/feature bits and validity exactly (max error0). Artifacts:
  `tmp/linkpad_target190_20261028-170050.ndjson`,
  `tmp/capture_export_20261028-170426.ndjson`, `.verified.ndjson`, `.csv`,
  `.replay.json`.
- Two post-export stack checks both read used1536/free2560/reserved4096,
  saturated0. ADS errors0/recoveries0, calibration VALID, fresh near-zero,
  PC0/PC1 LOW,PC8 HIGH,pump OFF. The offline beat diagnostic returned
  `cadence_unreliable` (28 peaks, median2300ms, cadence fraction0.148), so this
  round is acquisition/replay evidence, not BP accuracy or a reliable80bpm
  waveform. At the tested rate, 3153/3300 leaves147 samples; do not repeat190
  or raise the target without a larger proven storage budget and verified
  pressure ratings for all connected pneumatic parts. Stack logs:
  `tmp/compact_target190_stack1_20261028.ndjson` and
  `tmp/compact_target190_stack2_20261028.ndjson`.
- A separate user-confirmed100/65,80bpm External Cuff run at target150 reached
 151.4mmHg and captured2097/3300 points, dropped0, duration52400ms, exact25ms
  ticks. BP calculation failed because DBP feature86.6mmHg exceeded MAP86.3;
  no result was accepted. The complete `/2` export hash2790072925 decoded and
  replayed with exact envelope/feature bits and validity0. The sealed pressure
  rebounded to3.7mmHg once; after a second vent -> fresh0.0 -> seal, a new
  post-seal snapshot was stable0.0. Both post-export stacks were
  used1536/free2560, ADS errors0/recoveries0. The host beat check was
  `cadence_unreliable` at80bpm; preserve this as an invalid research waveform.
  Evidence: `tmp/linkpad_standard_20261028-171421.ndjson`,
  `tmp/capture_export_20261028-172032.ndjson`, and
  `tmp/compact_100_65_stack1_20261028.ndjson` /
  `tmp/compact_100_65_stack2_20261028.ndjson`.
- A separate same-setting start then remained at0.0mmHg until firmware
  `Manual pump timeout; emergency vent`. The harness issued one start only,
  completed stop -> vent -> fresh zero -> seal, restored target50 and did not
  retry. Follow-up telemetry confirmed101 fresh0.0 samples and safe pins,
  calibration VALID, ADS errors0/recoveries0; no new capture exists. Before
  another round, confirm BP Pump2 is on the intended Standard100/65,80bpm,
  External Cuff simulation page with its pulse/ready indication. Evidence:
  `tmp/linkpad_standard_20261028-172502.ndjson` and
  `tmp/compact_100_65_timeout_postcheck_20261028.ndjson`.
- After the user reconfirmed External Cuff/ready, a target50 non-human pump
  diagnostic peaked26.3mmHg and passed the active-stop/vent/seal gate. A new
  firmware target150mmHg run with the BP Pump set to100/65,80bpm then reached
 150.8mmHg and completed2177/3300 points, dropped0, exact25ms ticks; result
 118/68,56bpm valid1. Its full `/2`
  export hash2604842734 decoded and production-C replayed with identical
  envelope/feature bits and validity. After a post-seal3.3-3.4mmHg rebound,
  repeated vent -> fresh0.0 -> seal and confirmed another five seconds at0.0
  before export. Two stacks were used1536/free2560, ADS errors0/recoveries0.
  Beat cadence remains unreliable at80bpm. Evidence:
  `tmp/linkpad_lowpressure_20261028-173104.ndjson`,
  `tmp/linkpad_standard_20261028-173235.ndjson`,
  `tmp/capture_export_20261028-173648.ndjson`, and
  `tmp/compact_100_65_stack1b_20261028.ndjson` /
  `tmp/compact_100_65_stack2b_20261028.ndjson`.
