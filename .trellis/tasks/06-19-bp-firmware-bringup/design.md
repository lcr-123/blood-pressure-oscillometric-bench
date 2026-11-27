# Design

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


## Synchronous valve command timing (2026-11-05)

Budget 1200 bytes for 600 pairs of uint8 open-to-open delta / actual open width,
plus first absolute uint32 tick and metadata. Deltas 1..255, widths 0..255;
uint32 wrap is exact. Capacity, unrepresentable intervals/widths or unmatched
edges set sticky error bits and stop appending; retained prefix is not complete.
Open and SysTick close are bounded O(1), no logging. Start/cancel share an IRQ
critical section. Cancel closes an outstanding pulse before the caller's final
GPIO state; no delayed ISR may reseal an emergency vent. Export rejects pending
pulses; schema4 adds timing metadata then ordered pulse rows after step rows.
Full validity requires no errors and count == aggregate pulses. Keep >=2048B
linker RAM headroom and 4096B reserved stack. No pressure-control change yet.

## 2026-11-05 peak instability diagnostic design

Reuse extract/bin_beats/summarize_bins/assess_stability without modifying their
features or thresholds. For each fixed origin, retain bin membership and the
three-bin smoothing contributors, top-two normalized margin and all gate reasons.
Remove each accepted beat in turn, rebin at all four origins, and retain every
outcome; this is deterministic perturbation of fixed extracted beats, not
re-extraction, independent repeats, uncertainty estimation or a correction.
Audit source/metadata/verified SHA256 before strict decode, preserve failed
attempts, and report local beat amplitude dips descriptively. Full pulse timing
is absent from retained valve aggregates; do not fabricate phase from tick%200
or claim that zero >=5mmHg steps excludes smaller artifacts. Separate the
demonstrated binning mechanism from unresolved pneumatic/electrical causes.

## 2026-11-05 shared envelope and stability design

Extract the existing raw-voltage bandpass, cadence, trough-bracketed beat and
height/area bin processing into one offline module. Both inference and diagnostic
commands consume the same result; diagnostics retain raw bin medians, unrounded
internal calculations, rejection counts and extraction failure reasons. Do not
concatenate disjoint eligible time intervals for Welch. Select the longest
contiguous interval and require >=600 samples and >=50mmHg pressure span within
that interval. A beat must lie wholly inside it. Preserve decoder and firmware.

Use the existing 10 mmHg median bins and 1/4,1/2,1/4 smoothing for baseline.
For stability, repeat only binning (not extraction) at origins 2.5,5,7.5 mmHg.
Every origin needs the baseline minimum support, gap, tails and height/area
agreement. The largest minus smallest height/area peak across all four origins
must not exceed15 mmHg. This is a development sensitivity screen, not a measured
error bound or confidence interval. Return null primary peaks on instability
while retaining baseline candidates and per-origin reasons in diagnostics.

Keep current C firmware unmodified until an offline candidate has repeatable
multi-setting evidence. Its80..100 MAP window, -10/-5 offsets and first-window
pulse estimate are known deployment blockers; unchanged host-C replay verifies
transport only. This increment neither starts pressure nor sends serial commands.

## 2026-11-05 lossless capacity design

Reuse one N-float array: EXTRACT stores unsmoothed values, SMOOTH preserves the
last32 raw envelope values in a ring before overwriting each array position.
Sum the same window in the original order; no running-sum rounding change.
Export recomputes each raw envelope from retained float32 inputs. Storage is
13*N+128 bytes rather than17*N; set N4200 and a new firmware identity. Keep
feature/FFT arithmetic unchanged. If FFT fails, use a separate <=8-point/5ms
cooperative phase to recompute/count raw envelope peaks, then finalize the
original result rules. Cancellation/reset must cover this phase. Decoder and
capacity diagnostics recognize4200; old captures remain valid. Freeze the
pre-change result function in host-only fixtures for independent comparison.

## 2026-11-01 range-adaptive Standard BP candidate

The offline tool strictly decodes bp.capture transfers, checks 25 ms MCU ticks,
extracts periodic beats from raw voltage across the observed pressure span, and
forms 10 mmHg median height/area bins. It reports only an envelope peak when
both tails, beat count, continuity and cadence are sufficient. It never infers
SBP/DBP using unvalidated 50%/60% crossings, and never uses panel values during
inference. Known presets are report metadata. The 60/30 synthetic profile
abstains with the current low-pressure coverage gate. No device I/O or firmware
image change occurs in this increment.

## 2026-11-01 multi-setting model readiness

The read-only study joins the existing development manifest and envelope gate
by run ID and hash, then strictly decodes candidate captures to reuse the
existing 10 mmHg oscillogram feature extraction. It groups candidates by
panel setting and recorded pulse volume. Each setting reports feature peaks,
comparable repeat support and blockers. The result carries null BP coefficients
because these seen runs selected the quality rule, the highest setting has no
qualified envelope and no synchronized dynamic reference exists.

## 2026-11-01 development envelope abstention

The read-only gate consumes the local development manifest, checks each verified
file hash, strictly decodes complete exports, and calls the existing
`bp_oscillogram_study.analyze` at both 5 and 10 mmHg widths. A small pure
decision function requires height and area `diagnostic_only` plus passing
robustness; it emits explicit abstention reasons and never emits BP values.
The 200/150 run remains out of scope for a validated pressure bound. Preserve
the four seen rule-selection runs as development candidates and the failed
no-rise attempt as an abstention. No firmware or actuator data flow changes.

## 2026-11-01 read-only pulse window comparison

Reuse bp_capture.decode and the existing label-free estimate_pulse as a same-source comparator. A host-only tool reads exact 25ms MCU ticks and float32 raw voltage, applies the production 256-point detrend/Hann/band-bin shape at two fixed strides, and restricts complete windows to 40..120mmHg after the first80 and before the final15 points. Preserve per-window bins, abstentions, exact source hashes and an explicit output artifact. The exploratory 70% modal-bin rule is not a firmware replacement or independent label validation.

## 2026-10-31 load-off switch comparison

Reuse Bridge/HoldBridge, ADS counter decoder and existing stable-zero closeout.
Current commands: holdopen/close isolates PB8, vent/seal isolates PC1, start/close
couples PB8+PC8 and exercises 25ms manual reads. Three cycles each,2s on/2s off,
host pressure ceiling5mmHg and freshness2s. Firmware identity uses the prior
verified download/boot record (not a fresh identity query); current help must
advertise readtest. Require calibration and safe idle pins; static readtest before/after. No target/calibration
or firmware changes. This cannot reproduce natural target-stop ordering or
one-second automatic hold at pressure: close stops pump before closing valve1,
whereas natural target stop does the reverse. A passing result narrows conditions
but does not prove a hardware fault or eliminate hardware-dependent software.

## 2026-10-31 reading-path isolation test

Keep production ADS/HAL code and calibration unchanged. A register-level host
fake checks every I2C address, register and byte and models conversion completion
after 8 ms. Extract actual main/control function bodies, without copied algorithm
implementations, for ramp/hold and fault injection regressions.

`readtest` owns no actuator GPIO; accepts only inactive acquisition, no pending
calculation, calibrated initialized ADS, <=250 ms cached pressure in 0..1 mmHg,
PB8 HIGH/PC1 LOW/PC8 HIGH. Reuse cached pressure and sample clock; add 8 B SRAM.
Require >=380 reads in 10000 ms to pass; sample failure, changed pins or pressure
outside 0..5 mmHg terminates without a success marker. Preserve ADS baseline and
first error. Stop/vent/seal and acquisition cancellation stop the diagnostic;
other acquisition/export/calibration/scan paths recognize it as active.
Streaming prints cached samples while active, avoiding duplicate conversions.
Report PASS_READ_ONLY as sealed static evidence only, never loaded-switch repair.

## 2026-10-31 UART receive recovery and command integrity

Do not rearm or accept a byte in RxCplt when ErrorCode is nonzero: the vendor
handler calls RxCplt before its ORE abort/error callback, and rearming would
erase the error. ErrorCallback clears the F1 SR/DR error condition, invalidates
the partial line and unsafe pending command, and rearms only a READY RX once.
A short PRIMASK-preserving main-loop task retries a READY receiver; BUSY RX
is left alone. Count errors with one saturating uint16 and report on status.

Keep the existing 48-byte buffer as a frozen single-command mailbox. While it
is pending, compare incoming tokens against stop/vent using a two-bit match
mask, preserving emergency priority without another static buffer. Main copies
the mailbox into a 48-byte local under a short interrupt mask, releases it and
rejects any partial busy input until the next clean delimiter. Invalid characters
and overlength lines reject the entire line. Parameter parsing uses only the
snapshot. This adds four small bytes of state rather than another 48-byte buffer;
the linker and stack budget remain acceptance gates.

Move the scan into a small helper: active acquisition/calculation or any unsealed
actuator pin rejects it before I2C. Idle scan uses addr<<1 and bounded existing
trials/timeouts. No vendor driver, ADS conversion/recovery, calibration, target,
PWM or GPIO mapping change. Identify the rebuilt image as UART_RX_GUARD_20261031.

## 2026-10-31 ADS first-failure bus evidence

Append uint16 CR1 and GPIOB.IDR to the existing failure snapshot (4 bytes in
the struct, 8 bytes total SRAM growth in the Keil link); no per-sample storage. Read CR1 and
IDR without writes after the existing SR1/SR2 capture and before marking offline.
Keep the original ADSdiag line intact and emit a second bounded ADSbus line
only with explicit diagnostics. Report PB6=SCL/PB7=SDA from the saved inputs,
not current GPIO readings after recovery. Sequential snapshots do not measure
transient edges and two HIGH lines cannot by themselves prove a silicon erratum.
An ARGUMENT rejection with recovery pending retains the previous snapshot and
counter; actual probe/recovery/transaction failures still replace it. Firmware
ID ADS_BUS_DIAG_20261031 distinguishes the diagnostic image. No new recovery,
bus pulses, calibration, PWM or actuator commands in this software increment.

## 2026-10-31 post-target hold fault protection

Extend ManualPump_TimeoutTask to sample while inflation OR the pending hold owns
the pressure path. Reuse the 25 ms clock and cache without new static buffers;
after over-pressure protection, return for hold-only state so the target branch
cannot extend the deadline. PressureStream_Task prints that cache during hold.
Safety-read failure clears sample validity and calls ManualPump_EmergencyStop
before UART diagnostics; record the attempt time to defer offline retry. A
pressure query cancels/vents a pending hold before recovery if already offline,
or immediately on a failed read. Idle diagnostic reads retain fault-only behavior.
Move target-stop GPIO actions before the target-reached log. No ADS driver,
electrical, PWM parameter, algorithm or calibration change is part of this fix.

## 2026-10-31 capture catalog and next-batch metadata

Use `bp_capture.decode` as the only transfer validator. Hash the exact decoded
MCU lines for identity, while retaining each source file SHA-256 and decoder
failure separately. Report MCU tick intervals, sensor-estimated pressure and
header provenance, with unknown panel/fixture fields null. Historical files
remain method-development data; catalog generation is read-only and does not
build or run production C. Record a prospective run's panel settings, fixture,
HEX hash, calibration readback, zero checks and source hash before assigning a
validation role. Keep the catalog deterministic and outside `data/raw/`.

## 2026-10-31 PB8 active-low inflation relay

`VALVE1_CTRL_Port/Pin` now select GPIOB/PIN_8. `VALVE1_OPEN()` sinks LOW;
`VALVE1_CLOSE()` writes SET, releasing the externally pulled-up input. Initialize
OD/NOPULL only after SET, separately from GPIOC PC1/PC3/PC8 push-pull outputs.
CaptureExport_IsSafe and LoadedPulse_IsSafe require PB8 HIGH, PC1 LOW, PC8 HIGH
using named ports/pins; a combined GPIOC mask cannot represent this state.
The powered relay supplies HIGH; no module attached means readback can float.
Manufacturer FT limits and the unpowered-MCU restriction are captured in
hardware-map.md and the current wiring plan. No pressure/algorithm changes.
Earlier PC0 sections below are the historical design before this migration.

## 2026-10-29 connected pulse-width comparison

Keep `loaded pulse` as the original 5 ms command; add exact USART3 commands
`loaded pulse 1` through `loaded pulse 4`. Map each to a run-local fixed
PC1 open time, leaving the 200 ms period, 1 s sealed baseline, 4 s total
duration, pump-off start gate, 20-85 mmHg abort and automatic vent intact.
The capture valve aggregate reports actual on-time. The connected bridge
selects one width per run and checks the strict `/3` aggregate before
accepting export. The audit accepts a fixed 1-5 ms width and reports it.
Compare each run's own sealed-baseline drift with its phase-conditioned
pressure/voltage steps; do not pool samples across separate BP starts.

## 2026-10-29 loaded valve-pulse comparison

BP Pump 2 manual chapter 3, pages 3-11 to 3-12, states Pressure Source
supports 50-400 mmHg and does not maintain pressure after reaching the
setpoint. Use its 60 mmHg setpoint as a repeatable starting condition, then
measure passive drift within the capture rather than assuming a constant
pressure. The host requires fresh, stable pressure before requesting the
run. The current user-observed leak is about 11 mmHg/min, equivalent to
0.73 mmHg over four seconds if unchanged.

The USART3 `loaded pulse` command uses the existing 40 Hz capture and
SysTick-ended PC1 pulse machinery without adding sample arrays or static
state. Start only with calibrated ADS, fresh 40-80 mmHg pressure, PC0/PC1
LOW, PC8 HIGH, and no other acquisition. Sample continuously for four
seconds; leave PC1 sealed for the first 1000 ms, then command 5 ms PC1
opens at 200 ms intervals for the remaining 3000 ms. The internal pump
never starts. Any pressure below 20 or above 85 mmHg, ADS failure or
capture overflow uses the emergency vent. Normal completion stops pulses,
keeps PC0 closed and PC8 off, and opens PC1 for residual-pressure venting.
The original host plan waited for PC1 vent to reduce pressure before seal.
Board observation showed PC1 is isolated from the static BP/sensor/cuff line,
so the corrected host seals PC1 immediately after completion and waits for
the operator to stop the BP Pressure Source at its panel. After fresh near-zero
pressure, it exports the uncalculated `/3` waveform. Stop/vent/seal remain reachable; other
actuator commands are rejected while active.

The offline audit separates the baseline and pulse intervals, reports
absolute pressure decay and phase-conditioned adjacent pressure/voltage
changes, and compares the result with prior zero and Standard BP captures.
Pulse command tick is not the mechanical opening instant. In this fixture,
PC1 actuation cannot directly cause a pneumatic pressure transient in the
BP static line, so this run checks sensing/electrical coupling only. A
separate pneumatic fixture would be needed to test valve mechanics.

## 2026-10-29 sealed-zero pulse diagnostic

The USART3 `zero pulse` command starts only from a fresh sealed pressure
sample <=1 mmHg, valid calibration and ADS, PC0/PC1 LOW and PC8 HIGH. The
existing main-loop 25 ms acquisition writes pressure and unclipped sensor
voltage to the capture buffer. SysTick closes each 5 ms PC1 pulse; the main
loop schedules one every 200 ms for at most 5 seconds. Completion cancels
the pulse and closes PC1. ADS failure, pressure >1 mmHg or capture overflow
uses the existing emergency vent. During the run, only read-only status/help,
stream control, and stop/vent/seal commands are accepted.

The final `bp.capture/3` has `calc=0`, so no BP result or computed envelope is
implied. The completion line reports the final pulse tick to anchor a later
phase analysis. At 40 Hz the capture observes response after the valve-open
command, not the mechanical 5 ms opening itself. Voltage and pressure share
the same sensor chain; even a zero-pressure notch cannot independently
separate pneumatic from electrical causes.

## Bounded step-to-valve trace (2026-10-29)

The existing 200 ms valve aggregate remains unchanged. In AddSample, retain
the first 12 >=5 mmHg consecutive pressure changes after an actual valve
pulse. Each compact four-byte entry contains sample index, elapsed time
from the latest actual pulse (uint8, 255 means phase exceeded 254 ms), and
that pulse's commanded on-time. The aggregate `steps` count remains the
full count; `trace_n=min(steps,12)` exposes truncation. Reset clears both.
No new GPIO, UART, watchdog or control-loop work runs in the record path.

`bp.capture/3` emits begin, original ordered points, one valve aggregate
with `trace_n`, exactly `trace_n` ordered step records, features and FNV end.
Strict decoding checks count, order, pressure-step magnitude, on-time range,
phase bin and checksum. `/1` and `/2` remain readable. A step's closest
recorded valve-open MCU tick is point tick minus phase (modulo uint32) when
phase <255. The trace is diagnostic evidence, not an independent pressure
reference or proof of physical causation. If `steps>12`, later events are
unavailable and the export must be labeled truncated for step timing.

## Candidate MAP algorithm gate after full 180 mmHg capture (2026-10-28)

Keep this as an offline design until independent non-human reference data and
held-out captures exist. The candidate consumes exact exported 25 ms voltage,
pressure and valve diagnostics. First require stable pulse cadence; extract
beat heights and areas from original voltage; reject beats supported by
reported-pressure steps near recorded valve pulses; bin remaining beats by
pressure. A candidate needs measured rise and fall tails, enough beats near
its peak, no large internal pressure gap, agreement between the binned
maximum and fitted center, and small leave-one-bin-out movement. Quality
failure returns no BP estimate and retains the raw waveform.

The complete User Defined150/100 target180 capture has a promising height
fit at123-125 mmHg but only two beats in its strongest pressure bin. The
earlier Standard150/100 target190 capture is an important counterexample:
its strongest bin is142.5 mmHg, fit117-124 mmHg, and step exclusion leaves
a40 mmHg internal gap. Their simulator modes and pulse volumes differ, so
they cannot be treated as matched repeats. Do not select a parameter by
making either run agree with the nominal150/100 label. Validate thresholds
on separate captures, then measure target MCU memory, work time and safety
latency before any firmware integration. SBP/DBP ratios and compensation
require separate reference evidence; MAP quality alone does not validate
them.

## Bounded full-waveform storage (2026-10-28, software only)

Keep public `BP_Sample_t` and `bp.capture/2` point fields unchanged. Store only
the two float32 inputs per point in a private 8-byte structure; store each
sample's unsigned millisecond delta from the previous sample in a separate
uint8 array. Keep one uint32 first tick and one uint32 last tick. The first
delta is zero. Reject a later delta of zero or >255 before writing the point;
the caller treats rejection like capture overflow and emergency vents. AddSample
continues to reject full/frozen buffers and increments the dropped count on
rejection. Reset clears count, tick anchors, diagnostics, and capture state.

`BP_Algorithm_GetCapturePoint()` fills the public snapshot with float bits and
reconstructs its uint32 tick from first tick plus deltas 1..index. This is
read-only, supports arbitrary access and wrap, and changes no exporter wire
fields. At nominal 25ms, 3300 points span 82.475s. Storage becomes
`3300*(8+1+4+4)=56100` bytes versus the old `2800*20=56000`; budget the two
tick anchors and any compiler changes against the Keil 2048-byte RAM gate.
One random access costs at most 3299 byte additions; the one-line-per-loop
export remains bounded, with target timing to be checked after download.

Raise the strict host decoder maximum and producer fixtures to 3300 while
retaining `/1` and `/2` compatibility for archived <=2800-point transfers.
Keep the firmware marker distinct so old captures cannot be passed off as
same-image replay. `bp_beat_analysis.py` must use the actual firmware's capacity
when projecting future captures; old board evidence remains 2800 until a new
image is flashed. No threshold, compensation, calibration, valve or pump change.

## Valve-pulse correlation increment (2026-10-25, software only)

Keep valve evidence in one small `BP_ValveDiagnostics_t`, not a fourth 2800-point
buffer. `DeflatePulse_Start()` records a pulse only when the real PC1 open path is
executed, using its actual MCU tick and bounded 1..90 ms on-time. `AddSample()`
compares consecutive cuff-pressure samples after the first recorded pulse. Absolute
steps >=5.0 mmHg are counted into eight 25 ms phase bins covering 0..199 ms and one
>=200 ms bin relative to the latest pulse; maximum positive and negative steps retain
sample index, signed delta, phase and pulse on-time. Reset clears the aggregate;
calculation begin does not. Recording remains diagnostic-only and has no GPIO,
serial, watchdog or result-selection side effect.

Upgrade the writer to `bp.capture/2`: begin, ordered point rows, exactly one `valve`
aggregate row, features, end. FNV1a covers the valve row with the other pre-end raw
JSON bytes. The strict decoder accepts both versions: `/1` forbids a valve row and
returns no valve diagnostics; `/2` requires exactly one valve row after all points
and before features. Validate exact keys, scalar ranges, nine phase bins, aggregate
count consistency, signed finite float bits and maximum-event metadata. Production-C
replay continues to consume only original point bits/ticks, while its report carries
the validated valve aggregate unchanged. No algorithm input or arithmetic changes.

## Capture export / replay increment (2026-10-25)

Keep the existing2800-point buffers; expose read-only sample/envelope access and
a revision that changes on mutation. Context is set immediately after Reset by
both callers: relay input is reconstructed sensor_voltage_v, full control input
is ads_voltage_v. Preserve this existing difference; never label either mmHg
oscillation or silently change the algorithm input. Snapshot calibration then.

New capture exporter owns only a cursor/hash/revision. `capture export` is
accepted only with no actuator/calculation job, fresh calibrated<=5mmHg and
PC0/PC1 LOW, PC8 HIGH. It writes at most one bounded NDJSON line per loop;
normal safety/stream/IWDG continue. Other commands cancel the pending export
before execution (including stop), and revision mismatch aborts it. No end on
abort or transport failure. Never hold a lock that could block emergency stop.

Protocol bp.capture/1: begin metadata, ordered point rows with uint32 float bits
(pressure/raw voltage/extracted envelope/smoothed envelope) and MCU ticks, then
an independent features diagnostics row and an end checksum row. FNV1a covers
exact begin+point+features UTF8 bytes excluding CRLF and end. Envelope values
are null unless a terminal calculation completed; failed
BP still has complete envelopes. Decoder rejects loss/duplication/tampering,
nonfinite floats, overflow and incomplete sessions. Bridge text RX wrappers and
direct serial NDJSON supported; transport timestamps never replace MCU ticks.

Offline runner compiles actual production bp_algorithm.c against host HAL,
feeds original float32 values at original ticks and reports result/feature
diagnostics/envelopes. Compare host envelopes numerically and report differences;
do not promise ARM/MSVC bit identity. Python tool has no device/actuator I/O.

## Cooperative calculation increment (2026-10-25, software only)

The complete LINKPAD round showed a 1858ms host-delivery gap after deflation.
Measure MCU work separately from wall time; transport causation is not proven.
Keep existing arithmetic order, window sizes, thresholds and compensation.
Split envelope extraction and smoothing into bounded batches (at most8 samples,
yield after5ms of tick-observed work); run final feature/FFT processing as its
own measured step. The final step is not claimed to have a hard5ms bound.
Both acquisition callers start/step calculation from the main loop rather than
using the synchronous compatibility wrapper. Stop/reset/actuator overrides
cancel pending jobs; no stale BP result may be published afterward. Streaming
continues with new ADS samples, not repeated cached deflation data. Keep the
2s host freshness gate and IWDG policy unchanged. No flash or pressure operation
in this increment; target timing, responsiveness and repeatability remain gates.

## Standard BP reliability increment (2026-10-25)

See `.trellis/spec/firmware/core/capture-reliability.md` for executable contracts.
Use percentile threshold counting rather than sorting a large local buffer;
reserve 4 KiB stack and budget 2800 samples in 64 KiB RAM. A failed AddSample
invalidates the capture and immediately vents in every caller. ADS read failure
returns its HAL status and snapshot without recovery; later offline Init rebuilds
HAL/I2C1 state. Keep the last failure for diagnosis, rate-limit offline stream
attempts, and never restart a pump or close the emergency vent on recovery.
Do not change existing MAP/SBP/DBP tuning in this increment. Hardware dropout
causation must be assessed by subsequent non-human tests, not inferred from the
presence of a software defect.

## Existing Firmware Shape

The project is organized as a CubeMX / Keil MDK STM32F103ZET6 firmware project.

The current application modules are:

- `ads1115.[ch]` for pressure ADC access.
- `bp_control.[ch]` for the measurement state machine.
- `bp_algorithm.[ch]` for oscillometric result calculation.
- `esp8266.[ch]` for AT-command WiFi support.

## Bring-Up Strategy

1. Confirm project conventions and hardware map in `.trellis/spec/firmware/`.
2. Review code against `血压仪完整接线方案.md`.
3. Pick one small firmware objective at a time.
4. After each session, record what was verified, what failed, and what the next physical test should be.

## Current Risks To Resolve

- Button start/stop wiring exists in `main.h`, but `main.c` does not currently call `BP_Control_Start()` from button logic.
- ADS1115 conversion constants must be checked against the actual MPXV7007DP output divider and calibration data.
- `ESP8266_UploadResult()` currently logs a placeholder request and still needs real server connection handling.
- Pressure calibration remains unavailable until the replacement sensor and reference equipment arrive.
- Algorithm output is not clinically validated and needs calibration/reference-device testing.

## Staged Completion Design

Each stage must end with a non-human hardware test before the next stage begins.
Actuator control is the foundation: PC0 and PC1 macros own only their respective
valves, while the pump API exclusively owns PC8. Combined operating states are
assembled explicitly at command/state-machine call sites so safety ordering remains
visible.

Stage 1 operating states:

| State | PC0 | PC1 | PC8 |
| --- | --- | --- | --- |
| Safe sealed idle | LOW | LOW | HIGH |
| Inflate | HIGH | LOW | LOW |
| Vent / emergency stop | LOW | HIGH | HIGH |

Transitions must stop the pump before opening the deflation valve, and must close the
deflation valve before starting the pump.

### Stage 2 Pressure Diagnostic

Keep relay-only actuator behavior active while initializing ADS1115 independently.
The pressure diagnostic performs a single AIN0 conversion and derives all reported
fields from that same raw sample:

`AIN0 raw -> ADS voltage -> divider-reconstructed sensor voltage -> provisional mmHg`

The raw and ADS-voltage fields validate acquisition. Sensor voltage and mmHg remain
provisional until the physical divider values and pressure reference are calibrated in
Stage 3. ADS failures must not start or otherwise alter any actuator.

### Calibration-Wait Safety Foundation

Relay-only command handling remains in main.c so existing bench commands continue to
work. BP_Control owns the shared latched fault and emergency-stop model. This keeps
diagnostic sampling independent while ensuring any future full-measurement failure
has one ordered path: pump off, inflation valve closed, deflation valve open.

The command boundary is:

USART3 line -> command enum -> main-loop dispatcher -> actuator or diagnostic helper

Physical PA0/PA1 polling stays disabled at the user's request. USART3 start and stop
substitute for the two buttons during bring-up. start/open arm a 5000 ms main-loop
deadline; stop and timeout both enter an immediate vent state.

The IWDG starts only after startup diagnostics and is refreshed at the end of the
main-loop safety work. Debug freeze allows normal Keil halt/step use. The watchdog is
not a pressure limit; it is a final recovery mechanism for a stalled main loop.

## Stage 3 Automated Calibration Design

The first automation slice is deliberately hardware-safe and sensor-agnostic. It
does not open a COM port, operate Ansur, or command the BP Pump 2. It validates the
calibration data path with deterministic synthetic samples so the fitting and report
contracts are ready before a replacement sensor is connected.

Data flow:

`reference pressure + sensor samples -> per-point summary -> linear fit -> independent verification -> JSON/CSV report`

The calibration model is:

`pressure_mmhg = slope_mmhg_per_unit * sensor_value + intercept_mmhg`

When `sensor_value` is reconstructed sensor voltage in volts, the report also derives:

- `zero_voltage_v = -intercept / slope`
- `sensitivity_v_per_kpa = 7.50062 / slope`

The tool keeps calibration samples and verification samples separate. The fit uses
only calibration samples; PASS/FAIL uses only verification error against a configurable
tolerance. This prevents a tautological report that verifies a fit with the same data.

The later live adapter will normalize EK-OmniProbe `ek.telemetry/v1` samples into the
same input records. BP Pump 2 control remains behind the supported Ansur plug-in until
its initialization protocol is understood; raw commands are prohibited because they
reproducibly trigger instrument error 1300 on this unit.
## Target275 coverage increment (2026-11-05)

Share target upper bound as BP_MAX_TARGET_MMHG=BP_MAX_PRESSURE_MMHG-5U,
while hard protection remains280 and executes before target-stop handling.
Identify this image as TARGET275_CAPTURE_20261105. Change neither calibration
nor oscillometric feature/deflation rules. A bounded host runner records one
275 trial with278 abort and105s total active deadline,25s reach deadline and
90s terminal wait; preserve3300-point overflow protection. Lock image SHA256
before authorized Keil download, restore calibration only after UNCAL, verify
version/pins/counters and idle target275 acceptance/target280 rejection.
Complete vent -> continuous fresh zero -> seal before export; restore target50.
Compare height and area tail diagnostics against250 as development evidence.

