# Bring up blood pressure monitor firmware

## Controlled peak-window deflation comparison (2026-11-05)

User OK covers increasing beat support after exact valve timing validation.
Keep normal mode as power-on default. Add explicit `profile normal|peak` plus
read-only `profile`; writes require fresh calibrated sealed zero with no active
capture/export/calculation. Peak profile only applies at inflation target>=200:
fixed 200..245mmHg window targets1.8mmHg/s, outside stays3.0; lower targets and
deflate diagnostic remain unchanged. Window covers the prior212.5..230 peaks
and is declared before observing the new comparison; no panel labels used.
Nominal275->15 takes86.7s at3.0; window adds10s =>96.7s/3867points versus4200
capacity. This is a planning estimate, not a worst-case guarantee. Keep overflow
abort,278host/280firmware ceilings,2s freshness and130s active deadline. One
baseline then one profile trial; preserve failures. Host records profile command,
readback, firmware ID and fixed window in raw metadata; restore normal/target50
at verified closeout. Schema4 waveform/edges and extraction gates are unchanged.
Run real-C selector and profile gate regressions, full suite, Keil/RAM/stack,
verified download and zero pulse before profile inflation. Independent dynamic
pressure accuracy and causal source of ringing remain unverified.


## Current increment: synchronous valve command timing (2026-11-05)

Record actual PC1 pulse open/close commands on the sample HAL tick clock,
including early cancellation, under the user's OK. Preserve 4200 lossless
points, safety and BP arithmetic. Export schema4 with strict 1/2/3 compatibility.
Invalid/truncated timing stays explicit. GPIO timestamps are not mechanical
motion or ADS conversion apertures. Validate host, Keil RAM/stack and safe
download first. Peak-region slower deflation follows as a controlled comparison.

## Current increment: peak instability localization (2026-11-05)

Under the user's OK, diagnose high-pressure envelope instability offline using
all 13 retained attempts (8 complete). Freeze shared extraction and gates;
quantify per-origin leading-bin margins, beat contributions and leave-one-beat-out
sensitivity, retaining failures. Do not select a favorable bin, drop a beat to
correct an answer, or interpret sensitivity as BP error. Record what valve
telemetry can and cannot establish. Deliver reproducible JSON/Markdown/plot and
regressions; no pressure round or firmware deployment in this increment.

## Current increment: shared envelope extraction and stability audit (2026-11-05)

Under the user's OK, repair the offline label-blind envelope candidate before
deciding whether it is ready for firmware. Share extraction with diagnostics;
reject irregular ticks and whole-beat pressure violations; use only the longest
contiguous eligible time window, rejecting it if insufficient. Require peak
stability across four predeclared 10 mmHg bin origins
(0, 2.5, 5, 7.5 mmHg); require every origin to pass the existing support/tail
checks and the combined height/area peak span to be <=15 mmHg. Retain all
abstentions, source hashes, prior results and raw files. Audit the six earlier
complete runs and Preset4 target250/275, retaining failed attempts separately.
No preset label is an inference input; no SBP/DBP estimation or accuracy claim.
Do not port or flash merely because one candidate matches a panel MAP. Record
an explicit deployment decision and the on-device fixed-window/offset debt.

## Current increment: lossless 4200-point capture (2026-11-05)

After the retained target275 overflow, user authorized capacity repair and one
repeat. Preserve float32 pressure/voltage, exact MCU ticks, 40 Hz sampling,
deflation rules, calibration and 280 mmHg hard protection. Require 4200 samples
(105 seconds nominal) with unchanged invalidation on overflow. Frozen legacy C
must match envelope bits and result/features, including FFT fallback. Require
cooperative fallback/cancellation, full host tests, Keil and RAM/stack gates,
verified authorized download, then one nonhuman Preset4 target275 capture with
130s active deadline / 115s terminal wait and existing 278mmHg host abort.
Retain failures; complete vent -> fresh zero -> seal, restore target50. A full
capture/replay is transport evidence and does not establish BP accuracy.

## Current increment: Preset 4 target275 coverage trial (2026-11-05)

User requests one nonhuman Standard BP / External Cuff / Preset 4 trial at
target275 after target250 lacked the upper envelope tail. Panel confirmation:
255/195,80 BPM,0.55cc; unchanged circuit and load12V connected. Preserve280
hard protection, current calibration and waveform/algorithm arithmetic. Permit
target275 with5mmHg margin; host abort278, freshness2s and active deadline105s.
Require build/host/RAM gates, verified download, fresh zero, complete closeout,
strict decode and actual production-C replay. Retain failures and compare upper
coverage without assigning preset labels as measured BP or claiming accuracy.

## Current increment: Standard BP range-adaptive envelope algorithm (2026-11-01)

Audit the prior research-only offline candidate for circular validation and
unjustified SBP/DBP output. Retain label-blind raw waveform inspection, envelope
peak diagnostics and explicit abstentions, and retain unvalidated ratio
crossings as research fields, but output null SBP/DBP until a
prospectively frozen model passes an independent batch. Record unsupported
low-pressure range honestly. Preserve raw data and current firmware/calibration.

## Current increment: multi-setting envelope model readiness (2026-11-01)

Use the retained non-human Standard BP development runs to inventory qualified
height/area features across 120/80, 150/100 and 200/150. Verify the manifest,
gate and capture hashes; report same-volume repeat support and all abstentions.
Do not fit BP coefficients from incomplete or rule-selection data. Define the
prospective evidence needed before a multi-setting formula or firmware change.
This increment has no device I/O or calibration edit.

## Current increment: development-only offline envelope abstention (2026-11-01)

Use the existing strict decoder and oscillogram study to give the retained
non-human Standard BP runs explicit analyzable-candidate or abstain decisions.
Require both height and area diagnostics and robustness to pass, preserve 5/10
mmHg results, keep the failed no-rise attempt, and reject the 200/150 run under
the 150/100-specific 170 mmHg bound. Output no SBP/DBP and make no independent
accuracy claim. This increment has no device I/O, firmware or calibration edit.

## Current increment: read-only multiwindow pulse study (2026-11-01)

Investigate why two completed non-human Standard120/80 captures report 56 BPM while the operator setting and label-free long-window cadence are 80 BPM. Use strictly decoded existing raw voltage and MCU ticks; compare the fixed first 256-point FFT with declared 128/256-point window strides wholly within 40..120mmHg. Retain every raw file, report abstentions and frequency-bin limits, test synthetic varied rates and valve-only/weak-signal rejection, and do not treat same-sensor agreement as reference accuracy. No serial writes, inflation, calibration or firmware change in this increment.

## Current increment: operator-confirmed load-off switch comparison (2026-10-31)

Operator replied OK to BP Stop and disconnecting only pump/valve load-side12V,
retaining MCU/ADS/UART/control power. Record this as operator confirmation, not
an independent voltage measurement. Use current firmware and EK bridge only:
static readtest, three bounded cycles each of valve1-only, valve2-only and
coupled pump/valve1 outputs. First ADS/UART/reset/freshness/pressure failure
terminates switching. Preserve counters, raw records and vent/fresh-zero/seal.
No return of load power without a subsequent operator state confirmation.

## Current increment: reading-path isolation test (2026-10-31)

User requests a test distinguishing external faults from software reading faults.
Compile the actual ADS driver and actual manual inflation/hold functions on host:
validate command bytes, conversion readiness, signed raw/scaling/calibration,
100 mmHg ramp/hold and every transaction's HAL_ERROR/BUSY/TIMEOUT handling.
Add `readtest`: sealed-zero non-human 10 seconds at production 25 ms cadence,
no actuator writes, first-failure termination, no retries masking a lost sample.
Download under existing explicit authorization after fresh safety preflight;
restore current calibration only if erased. Preserve board evidence. A passing
simulation and static reading do not prove absence of hardware-dependent software
or physical faults during pump/valve switching.

## Current increment: UART receive recovery and command integrity (2026-10-31)

Code review found that USART3 has no error callback after HAL aborts ORE RX,
and the shared command buffer can change before main parses its parameters.
Recover RX with bounded HAL calls, reject damaged/overflowed lines through a
clean delimiter, snapshot a completed command atomically, and retain stop/vent
priority when a command is pending. No actuator/I2C/logging work in RX callbacks.
Fix i2cscan's shifted HAL address and reject scanning during active acquisition
or unsafe actuator pins. Exercise the actual vendor RX/error path and production
parser in host C; full host, Keil, SRAM/stack gates precede any download. Retain
the distinction between these software defects and the unproven loaded-dropout
cause. No new pneumatic trial or return of 12V power in this increment.

## Current increment: ADS first-failure bus evidence (2026-10-31)

User requests resolution of the repeated post-switch pressure-read fault. The
15:06 run still fails with CONVERSION_START/HAL_BUSY/TIMEOUT/SR2.BUSY. Add
read-only CR1 and GPIOB input snapshots to distinguish line levels at failure,
and preserve the actual bus failure across calls rejected while already offline.
Do not retry in ReadSample, conceal a lost sample, restart the measurement or
claim the physical cause repaired by diagnostics. Existing emergency vent must
precede all recovery. Host C tests, full suite, Keil/RAM/stack checks precede a
load-off download and separately gated non-human isolation/reproduction check.

## Current increment: post-target hold fault protection (2026-10-31)

During the one-second wait before automatic deflation, monitor pressure at the
existing 25 ms safety cadence independently of diagnostic streaming. A failed or
offline pressure read must cancel the pending hold/PWM/pulse/calculation and
enter SENSOR_READ emergency vent before logging or recovery. Explicit pressure
queries obey the same active-hold protection; after seal cancels the hold, idle
diagnostic failure must not take actuator ownership. Retain the normal deadline,
target and calibration. Validate with actual-C host fault injection, the full
suite, Keil rebuild and RAM/stack gates before a separate non-human board check.

## Current increment: retrospective capture catalog and prospective protocol (2026-10-31)

Return to the open non-human oscillometric cuff dataset direction. Audit every
archived firmware-export NDJSON with the existing strict decoder, isolate invalid
transfers, deduplicate exact validated MCU records, and report sample timing,
pressure range and missing experimental metadata. Keep raw files untouched.
Freeze a per-run metadata template for the next prospective batch and distinguish
development from independent validation. Do not infer BP panel truth from
filenames or claim production-C replay was rerun by a decode-only catalog.

## Current increment: PB8 active-low inflation relay (2026-10-31)

User requested PB8 low-level control of the inflation valve. Migrate only valve1
from PC0 active HIGH to PB8 FT open-drain/NOPULL active LOW, with SET preloaded
before output initialization. Synchronize CubeMX, serial diagnostics, both safe
capture/pulse predicates, current wiring and specs. Preserve PC1/PC8 behavior.
Acceptance: actual production GPIO/macro and separate-port gate regressions,
host suite, Keil zero-error/zero-warning rebuild, source registration and RAM/stack
budget. This increment includes no device download or pneumatic operation.
Previous PC0 descriptions below record the pre-migration task history.

## Current increment: connected-line pulse-width comparison (2026-10-29)

After the connected 5 ms diagnostic showed repeatable 4-5 mmHg valve-phase
notches and about 18 mmHg loss over three seconds, compare fixed 1-4 ms
PC1 pulses in the same non-human Pressure Source fixture. Preserve the
existing 5 ms command, pressure and actuator safety gates, one-second sealed
baseline, three-second pulse interval, automatic vent, and `/3` raw capture.
Treat each width as a separate round and reject an export whose recorded
width differs from the request. Do not infer clinical accuracy or uniquely
identify a pneumatic part from the one-sensor comparison.

## Current increment: low-pressure loaded valve-pulse comparison (2026-10-29)

The sealed-zero 5ms/200ms PC1 pulse check showed only 0.043 mmHg equivalent
peak-to-peak voltage variation, while Standard BP captures had occasional
5-9 mmHg valve-phase notches. Compare under non-human pressure sourced by
the BP Pump 2 Pressure Source function, at a nominal 60 mmHg setpoint. The
Tester does not maintain pressure after reaching setpoint. The user most
recently observed about 11 mmHg/min leakage; measure a sealed baseline in
the same capture and reject an unstable starting pressure.

Acceptance: pump PC8 remains OFF and inflation valve PC0 closed throughout;
record one second of sealed baseline followed by at most three seconds of
5ms/200ms PC1 pulses, 25ms pressure and sensor-voltage samples, exact MCU
ticks and pulse diagnostics. Start only in a calibrated, fresh, sealed
40-80 mmHg window. Stop and vent on ADS failure, pressure outside 20-85
mmHg, overflow or timeout; normal completion must vent residual pressure
before strict `/3` export. In the actual static fixture PC1 is isolated from
the pressurized three-way line: close PC1 after the run, have the operator
release the BP Pressure Source at its panel, then verify fresh near-zero
pressure. Preserve BP algorithm and
calibration arithmetic. Host tests, zero-warning Keil rebuild, SRAM/stack
gate and non-human board preflight precede physical operation. This test
still uses one sensing chain and cannot prove a physical root cause alone.

## Current increment: sealed-zero pulse diagnostic (2026-10-29)

The 100/65 L2/L3/L4 waveforms contain a recurring valve-phase pressure notch,
but one pressure channel cannot distinguish pneumatic transients from electrical
or sensing coupling. On the non-human, zero-pressure setup, capture a bounded
five-second 5 ms/200 ms PC1 pulse series at nominal 40 Hz, retaining sensor
voltage and MCU sample ticks in the existing `/3` export. Require a fresh
calibrated sealed-zero preflight with pump off; close PC1 automatically on
completion, and vent on pressure, ADS or capture failure. Leave inflation and
BP feature arithmetic unchanged. A zero-pressure result is comparative evidence
from the same sensor chain, not a physical root-cause proof.

Acceptance: stop/vent/seal remain reachable during the diagnostic; conflicting
commands cannot take over the valve; host tests, zero-warning Keil rebuild,
Keil source registration and RAM/stack budget pass before any non-human board
operation. The exported raw voltage must be analyzed because displayed
negative pressure is clipped to 0 mmHg.

## Current increment: bounded pressure-step trace (2026-10-29)

The 100/65 L2 capture failed the frozen beat-height screen after six
>=5 mmHg pressure falls. Existing `/2` exports show their 200 ms valve
phase but only aggregate pulse-width ranges. Preserve the earliest 12
step-to-pulse associations with actual sample index, phase and commanded
valve-open duration in `/3`; report the total step count so truncation is
explicit. Preserve all pressure/voltage bits and ticks, old `/1` and `/2`
decoding, actuation timing, algorithm arithmetic and safety handling.

Acceptance: real-C export and strict decoder cover ordered/checksummed
step records, overflow cap and tampering; host suite and zero-warning Keil
build pass, static RAM headroom remains >=2048 B with stack gate, and a
non-human board check precedes any conclusion about the physical source.
This diagnostic cannot by itself establish whether BP Pump 2, the valve,
pneumatic path or sensing chain caused a pressure step.

## Current increment: bounded 3300-point capture storage (2026-10-28)

The retained 150/100 External Cuff captures start deflation below the labeled
SBP. Projecting a higher inflation target from observed 2.016-2.131 mmHg/s
deflation rates requires up to 3170 samples at target190, while the existing
2800-point capture is already near the 64 KiB SRAM limit. Expand the capture
budget without losing exact pressure/voltage float32 bits or MCU sample ticks.

Acceptance: a bounded 3300-point in-RAM capture with exact sequential and
random-access tick reconstruction (including uint32 wrap), explicit rejection
and existing emergency vent on nonrepresentable sample gaps or overflow,
unchanged `/2` export semantics and production-C replay, host tests through
3300 points, zero-warning Keil rebuild, and >=2048 B static RAM headroom plus
stack gate. Preserve calibration, BP feature arithmetic, actuation timing,
pressure limits, and existing 2800-point archived captures. Do not flash or
operate pneumatic hardware in this software increment; document the later
non-human wiring and validation gate.

## Current increment: valve-pulse correlation evidence (2026-10-25)

The new Standard BP capture shows large pressure steps phase-associated with the
200 ms valve schedule, but `bp.capture/1` contains no direct valve timing or pulse
width evidence. Add bounded aggregate diagnostics from the actual valve-open path
without adding per-sample arrays or changing measurement/algorithm behavior.

Acceptance: record actual pulse count, period/on-time ranges, >=5.0 mmHg pressure
step counts and 25 ms phase bins, plus maximum rise/fall evidence; export exactly
one checksummed valve record in `bp.capture/2`; retain strict `bp.capture/1`
decoder compatibility; add real-C lifecycle/roundtrip and missing/duplicate/
tampered-record regressions; pass the complete host suite, zero-warning Keil build,
and RAM/stack gate with at least 2048 bytes RAM headroom. Do not change pressure
thresholds, FFT/window selection, envelope arithmetic, compensation, calibration,
electrical settings, or actuator timing. Do not flash or operate hardware without
separate authorization.

## Current increment: complete capture export and same-source replay (2026-10-25)

User approved software implementation after the 19:40 failed Standard BP round.
Export the stored internal nominal40Hz samples, actual MCU ticks and both
envelopes after non-human vent/low-pressure/seal closeout. Do not change algorithm
arithmetic, calibration, electrical settings or safety thresholds. No automatic
flash/inflation. The old20Hz log cannot reconstruct that failed round.

Acceptance: bounded one-line-per-loop NDJSON export, capture-time calibration
and input-voltage provenance, complete count/order/checksum validation, explicit
envelope/calculation state, cancellation on mutation/commands, offline replay
compiled from production C, adversarial decoder and real-C roundtrip tests,
fresh zero-warning Keil build and RAM/stack gate. Target export timing and new
full-waveform acquisition remain separate physical acceptance gates.

## Current increment: Standard BP software hardening (2026-10-25)

User requested software fixes first, without changing hardware. MPXV5050GP is
the current sensor; MPXV7007DP descriptions below are historical. This increment
must remove the confirmed algorithm stack-budget defect, prevent silent sample
truncation, and make ADS errors/recovery observable without delaying emergency
venting. Preserve current calibration, algorithm tuning and electrical settings.
Code/build/tests may complete before physical validation; do not mark the entire
bring-up task complete or claim the ADS dropout root cause is established.

Acceptance: zero-error/warning Keil build, RAM/stack gate, old and new regression
tests, updated contracts and a non-human validation plan. No automatic flash or
actuator operation in this software-only increment.

## Goal

Turn the initialized STM32 blood pressure monitor project into a traceable firmware bring-up workflow. The immediate goal is to verify the existing modules against the wiring plan, identify the next concrete firmware gaps, and make the project ready for iterative Trellis-guided development.

## Requirements

- Treat `blood pressure monitor/` as the firmware project root.
- Preserve STM32CubeMX generated-code boundaries and keep custom edits inside `USER CODE` blocks or custom modules.
- Verify the current hardware assumptions:
  - ADS1115 on I2C1, address `0x48`, A0 connected to MPXV7007DP through the divider.
  - Pump PWM on TIM8_CH3 / PC8.
  - Valve controls on PC0 and PC1.
  - ESP8266 on USART1, debug output on USART3.
- Review the measurement state machine for safe pump and valve behavior.
- Decide the next firmware implementation target before changing code. Likely candidates:
  - button start/stop integration,
  - pressure calibration and ADS1115 conversion validation,
  - ESP8266 upload completion,
  - deflation rate control,
  - result display or serial reporting.

## Acceptance Criteria

- [ ] Trellis firmware specs exist and are referenced by the task context manifests.
- [ ] The active task explains the firmware bring-up scope, constraints, and next-step options.
- [ ] The current code has been reviewed against the wiring plan before implementation begins.
- [ ] Any code change made under this task keeps pump/valve safety behavior explicit.
- [ ] The project can still be opened and built from the Keil MDK project after changes.

## Notes

- This task intentionally starts with project organization and bring-up planning because Trellis was initialized with generic fullstack templates.
- The code already contains custom modules for ADS1115, BP control, BP algorithm, and ESP8266. Do not restart from a blank template.

## Staged Non-WiFi Completion Scope

The user requested that all remaining non-WiFi firmware work be completed one
hardware-verifiable stage at a time. WiFi integration remains explicitly out of scope.

Confirmed actuator contract:

- PC0 HIGH opens the inflation path; PC0 LOW closes it.
- PC1 HIGH opens the deflation valve; PC1 LOW closes it.
- PC8 LOW turns the active-low pump relay on; PC8 HIGH turns it off.

Ordered stages:

1. Unify pump/valve polarity, defaults, and safety interlocks.
2. Enable and validate standalone ADS1115 pressure acquisition.
3. Resolve the MPXV7007DP range mismatch, then calibrate pressure conversion against
   non-human reference pressure.
4. Implement measurable slow-deflation control.
5. Correct sample timing/buffering and validate the oscillometric algorithm.
6. Enable buttons, the full measurement state machine, and result reporting.
7. Run non-human end-to-end safety and repeatability validation.

### Stage 1 Acceptance

- Startup leaves PC0 LOW, PC1 LOW, and PC8 HIGH.
- Inflation closes PC1 before setting PC0 HIGH and PC8 LOW.
- Deflation/stopping sets PC8 HIGH and PC0 LOW before setting PC1 HIGH.
- Valve macros do not implicitly control the pump.
- USART3 actuator logs state all affected pin levels.
- The Keil target builds with zero errors.
- With the documented MPXV7007DP fitted, testing remains non-human and below 40 mmHg
  because its +/-7 kPa range cannot cover the firmware's 200/280 mmHg targets.

Stage 1 hardware validation passed on 2026-08-25 per user confirmation.

### Stage 2 Acceptance

- Relay-only actuator mode remains enabled and starts in sealed idle state.
- Startup probes ADS1115 address `0x48` and reports the config register or a clear failure.
- `pressure` / `p` performs one A0 conversion and reports raw code, ADS1115 A0
  voltage, reconstructed sensor voltage, and an explicitly uncalibrated pressure estimate.
- Failed initialization or sampling reports an error without changing PC0, PC1, or PC8.
- The diagnostic command can retry initialization after wiring is corrected.
- The Keil target builds with zero errors.

Stage 2 hardware validation passed on 2026-08-25 per user confirmation.

### Safety Hardening Acceptance While Calibration Is Pending

- [x] Keep relay-only mode enabled and physical PA0/PA1 polling disabled.
- [x] Preserve start/stop/open/close/vent/seal/pressure/p serial behavior.
- [x] Replace the blocking emergency stop with an immediate latched vent state.
- [x] Prevent BP_Control_Start() from running while calibration is invalid.
- [x] Treat full-state-machine ADS read failure, inflate timeout, and over-pressure
  as emergency-stop faults.
- [x] Add help/status/pins/fault and stream start/stream stop diagnostics.
- [x] Automatically stop and vent relay-only start/open after 5000 ms.
- [x] Enable an approximately 4-second IWDG with debugger freeze and main-loop refresh.
- [x] Synchronize new sources into CubeMX metadata and the Keil project.
- [x] Pass static safety contracts and Keil build with zero errors/warnings.
- [x] Complete non-human hardware validation of the new commands, 5-second timeout,
  serial stop behavior, and watchdog boot stability.

## Stage 3 Request: Automated Pressure Calibration

The user wants a one-stop calibration workflow rather than an Ansur report-only
workflow. The intended flow is:

1. Apply known non-human reference pressures with the BP Pump 2.
2. Collect stable ADS1115 / pressure-sensor samples over USART3.
3. Fit the sensor zero and gain from multiple reference points.
4. Write the candidate calibration to the STM32, read it back, and verify integrity.
5. Repeat the pressure points, calculate per-point error, and produce a calibration
   result that clearly passes or fails.

Confirmed constraints:

- The current MPXV7007DP is limited to approximately +/-52.5 mmHg and project bench
  testing must remain below 40 mmHg.
- BP Pump 2 automatic static-pressure output starts at 50 mmHg, so it cannot safely
  provide the calibration points for the currently fitted MPXV7007DP.
- The existing firmware reports raw ADC code, ADS voltage, reconstructed sensor
  voltage, and provisional mmHg, but its zero and sensitivity are compile-time
  constants and there is no persistent calibration write/read protocol yet.
- No human may be connected during calibration or verification.

Open product decision:

- Target the automation at the replacement >=40 kPa sensor for full-range BP Pump 2
  calibration, or build a separate low-pressure/manual-source mode for the existing
  MPXV7007DP.
