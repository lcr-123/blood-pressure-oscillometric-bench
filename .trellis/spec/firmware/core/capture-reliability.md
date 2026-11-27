# Capture reliability (2026-10-25)

## Lossless 4200-point storage contract (2026-11-05)

### 1. Scope / Trigger

`CAPTURE4200_20261105` resolves the retained3300-point target275 overflow.
This changes capacity/scheduling, not calibration or BP accuracy evidence.

### 2. Signatures

`BP_ALGO_MAX_SAMPLES=4200U`; existing AddSample, BeginCalculate,
CalculateStep, CancelCalculate and GetCapturePoint signatures remain unchanged.
Strict decoder accepts n1..4200 and old protocols/identities; ordinary replay
still requires an exact firmware identity match.

### 3. Contracts

Keep float32 pressure/voltage and exact uint8 tick deltas without quantization.
One N-float work array stores raw envelope in EXTRACT, then SMOOTH overwrites
in place using32 saved raw values. Each window sums in the legacy order.
Completed/failed calculations recompute raw envelope per export point; uncomputed
or cancelled exports retain null envelope fields. Storage13*N+128 bytes.
After feature/FFT FINISH, FFT0 schedules PULSE_FALLBACK: recompute raw envelope
and count strict local peaks using the original0.2*max threshold and duration
arithmetic. This phase also yields after <=8 samples or >=5ms tick delta.
Its timing contributes to calc_finish_ms. Only a terminal step publishes a
result; cancel/reset/new acquisition must suppress pending fallback results.
Keep hard280, target<=275, overflow invalidation/emergency vent/export rejection,
sampling25ms and original deflation/calibration rules.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| 4200 accepted points | Complete retained data; never circular overwrite |
| Point4201 or unrepresentable tick gap | dropped++, cancel, existing emergency vent |
| FFT rejected after valid features | Cooperative peak fallback; legacy numerical result |
| Stop/null/reset while fallback busy | Cancel, no delayed BP output |
| Decoder n4201 | Reject |
| Historical identity differs | Strict replay rejects; explicit separate numerical comparison may report both IDs |

### 5. Good / Base / Bad Cases

Good: raw/smooth envelope bits and feature bits match the frozen legacy result
at4200. Base: no-signal remains invalid with full retained arrays. Bad: faster
venting, truncation, quantization, cleared dropped counter or altered identity
to make a full capture/replay appear successful.

### 6. Tests Required

Frozen host-only legacy_result_3300.h plus independent extraction/smoothing
loops compare constant/ramp/pulse/noise/FFT-flat-head cases at20/31/32/33/64/65/
256/2521/2800/3300/4200. Assert exact raw pressure/voltage/ticks and envelope,
feature/result bits, fallback entry, batch/tick yielding and cancellation.
Real-C export/replay through4200, decoder4201 rejection and overflow vent gates
must pass. Rebuild Keil, confirm source registration, RAM>=2048B and known stack
+1024<=4096. Host checks are not runtime timing/stack or accuracy validation.

### 7. Wrong vs Correct

Wrong: retain two N-float arrays and shrink stack to fit4200. Correct: reuse
the envelope workspace with a32-float ring; record actual map/stack budget.

## High-target capacity evidence (2026-11-05)

`BP_MAX_TARGET_MMHG` is275 (280 hard threshold minus5); accepting a target
does not prove a complete capture fits SRAM. Nonhuman Preset4 target275
reached275.3 then overflowed at3300 points,82475ms,dropped1 before reaching
the15mmHg endpoint (last pressure stream23.6). Preserve emergency vent and
export rejection; do not clear dropped, bypass the export gate or call this
a complete envelope/accuracy pass. The subsequent host STOP can replace the
latched fault name with USER_STOP, so retain the original overflow transcript.
Resolve capacity/duration budget before another full275 trial. Report:
`data/reports/standard255_195_target275_20261105.md`.

## Load-off comparison interpretation (2026-10-31)

Before switch tests, record operator-confirmed load-side supply state separately
from independent voltage measurement. Retain MCU/ADS/UART/control power and
GUI bridge permissions. Query calibration/status/pins and ADS baseline; stop on
first read/UART/reset/freshness failure and preserve original evidence. Compare
error/recovery increments and finish vent -> fresh near-zero -> seal -> no rebound.

`holdopen/close` tests PB8, `vent/seal` PC1, `start/close` couples PB8/PC8.
Current help advertises capability but does not print firmware ID; image identity
requires a boot record, or label prior verified boot evidence as historical.
Pump ON is a GPIO state, not proof of motor movement or load current.
Manual close stops pump before closing valve1; natural target stop reverses that
order. A zero-pressure load-off pass cannot establish natural hold-path equivalence,
exclude hardware-dependent software, or identify a damaged pump. No falsified
sensor samples to force a target stop; subsequent supply return requires current
operator state confirmation. Offline checks cover first on-window failure and
lost diagnostic response cleanup as well as the healthy command sequence.

## Sealed static readtest contract (2026-10-31)

### 1. Scope / Trigger

Compare static production ADS reads at the 25 ms inflate/hold cadence against
loaded I2C failures. Diagnostic only; no actuator ownership.

### 2. Signatures

Request `readtest`; terminal line:
`[ReadTest] <reason> n=<count> elapsed=<ms>ms last_raw=<signed-code>`.
Reasons: PASS_READ_ONLY, FAIL_ADS, FAIL_PINS, FAIL_PRESSURE, FAIL_CADENCE.
Rejection starts `[ReadTest] REJECTED`.

### 3. Contracts

- Require inactive acquisition/calculation, calibrated initialized ADS, valid
  <=250 ms cache at0..1 mmHg, PB8 HIGH/PC1 LOW/PC8 HIGH.
- Duration10000 ms,25 ms cadence,minimum380 successful conversions. No GPIO
  writes, per-sample allocation or inline retries. Streaming uses the cache.
- First failed read invalidates cache, marks ADS offline, records SENSOR_READ,
  ends diagnostic and prints evidence. Deferred recovery cannot resume the test.
- Block competing acquisition/calibration/scan/export. Stop/vent/seal cancel
  without a success marker. Preserve preexisting ADS counters and raw voltage.

### 4. Validation & Error Matrix

| Condition | Expected |
| --- | --- |
| Stale cache, invalid cal/ADS, active job, unsafe pins, pressure outside0..1 | REJECTED before conversion |
| Healthy10000 ms and >=380 reads | PASS_READ_ONLY |
| First ADS failure | FAIL_ADS, retained evidence, no GPIO/retry |
| Pin change / pressure outside0..5 including NaN | FAIL_PINS / FAIL_PRESSURE |
| Duration reached with <380 reads | FAIL_CADENCE |
| Explicit cancellation | Inactive, no PASS |

### 5. Good / Base / Bad Cases

Good: board400 reads/10000ms,ADS0/0,preserved transcript. Base: report increments
against retained counters. Bad: call static PASS a repaired loaded-switch fault
or count recovered reads as an uninterrupted test.

### 6. Tests Required

Compile actual ADS driver and actual main/control functions. Assert address,
configuration bytes,8ms ready fake,signed raw/scaling,100mmHg ramp/hold and
five transaction sites times three HAL failure statuses. Assert unchanged
failed destination,no inline recovery,loaded failure vent-before-log.
Cover400 static reads,uint32 rollover,slow loop,first failure,pin/pressure/start
gates and cancellation. Keil/source registration/RAM>=2048B/stack gates apply.

### 7. Wrong vs Correct

Wrong: fake HAL passes,so physical STM32 I2C/HAL and electrical path are healthy.
Correct: distinguish deterministic software,static board and loaded-switch
evidence; clipped zero pressure cannot prove zero input drift or a repaired cause.

## Loaded-pressure pulse diagnostic (2026-10-29)

The connected-line 5 ms run on 2026-10-29 recorded 15 phase-associated
pressure/voltage falls: 0-24 ms median adjacent change -4.23 mmHg, followed
by 25-49 ms median +3.12 mmHg; its 3 s pulse interval lost 17.98 mmHg.
The prior PC1-isolated run lost 0.43 mmHg over the same interval. This
connection-dependent effect supports a pneumatic transient, but one sensor
cannot isolate the valve body, tubing, BP source or sensing dynamics.
For the subsequent non-human comparison, `loaded pulse 1` through
`loaded pulse 4` change only fixed PC1 open time in milliseconds. The
original `loaded pulse` remains 5 ms. The host must confirm the strict
`/3` valve aggregate reports the requested fixed width and retain the
existing pressure, ADS, pump-off, overflow and vent/zero/seal gates.

`loaded pulse` is a non-human Pressure Source comparison at approximately
60 mmHg. In the current static three-way fixture, PC1 is isolated from the
BP Pressure Source/sensor/cuff pressure line. Its actuation therefore tests
pressure-dependent sensing/electrical coupling, not a pneumatic opening of
that line. Require fresh calibrated 40-80 mmHg readings, ADS online, PB8 HIGH (released), PC1
LOW, PC8 HIGH, and no active capture before starting. Record a one-second
sealed baseline followed by three seconds of 5 ms PC1 opens every 200 ms.
The internal pump stays off. Pressure outside 20-85 mmHg, ADS failure, or
capture overflow must emergency vent the firmware valve. Normal completion
also opens PC1, but this cannot release pressure in the static source line.
Close PC1 with `seal`; if the BP Source still holds pressure, stop it at the
panel. Then confirm consecutive fresh near-zero samples before exporting
the uncalculated `/3` capture. The BP Pump 2
Pressure Source does not maintain its setpoint: compare measured baseline
drift with pulse-phase changes, and do not attribute either to hardware
without an independent simultaneous measurement. The observed leak of about
11 mmHg/min is a planning estimate, not a subtraction applied to data.

For the separate fixture where PC1 is connected to the BP Pressure Source,
sensor and cuff line, use `loaded-pulse-connected`. A previous USER_STOP
may leave BP_Control in EMERGENCY even with sealed safe pins. The diagnostic
may clear that state only when the fault is exactly USER_STOP and all fresh
pressure, calibration, ADS, pump-off and sealed-pin gates pass; all other
faults remain rejected. Normal completion vents the connected line. Require
fresh near-zero samples, then `seal` immediately, verify fresh post-seal
near-zero samples and retry vent/zero/seal once on rebound before export.
Do not interpret a rejected or incomplete capture. The BP panel Measured
value and STM32 serial pressure must be recorded separately.

## Sealed-zero pulse diagnostic (2026-10-29)

`zero pulse` is a non-human, no-inflation diagnostic. Its start gate requires
fresh sealed pressure <=1 mmHg, calibrated ADS, PB8 HIGH (released), PC1 LOW and PC8 HIGH.
For five seconds it records nominal 25 ms pressure plus unclipped sensor
voltage while commanding 5 ms PC1 opens every 200 ms. SysTick ends each
pulse; normal completion cancels any pending pulse and closes PC1. Sensor
failure, pressure >1 mmHg or capture overflow must emergency vent. During
capture, stop/vent/seal and read-only status remain available; start/PWM and
other actuator commands are rejected. The uncalculated `/3` export (`calc=0`)
is diagnostic data only. Pressure clipping at zero means phase analysis must
use voltage; one shared sensing chain cannot establish the physical cause.


Current software increment: [Capture Export](./capture-export.md) defines the
`CAPTURE_VALVE_20261025` read-only evidence API, `/2` valve aggregate, NDJSON
checksum and offline production-C replay. Seventy-three tests and a fresh
zero-warning Keil build passed. The image was flashed/verified on 2026-10-26 and
the erased82.326/-19.887 calibration was restored only after safe pins, ADS and
zero-pressure telemetry passed. A non-human50mmHg `/2` target export then passed:
n377/dropped0, all tick intervals25ms, one48-pulse valve aggregate, complete hash
and bit-equal production-C replay. A Standard120/80,80BPM `/2` waveform then
passed transport/replay: n2225/dropped0, result113/91/75 valid1,279 pulses, and
no >=5mmHg step. Offline differences found six >=2mmHg changes all at the200ms
schedule boundary, so smaller phase association remains but valve causation is not
established. Runtime watermark implementation and idle target baseline passed on
2026-10-28, while dynamic calculation/export-path high-water remains pending
because the serial bridge disconnected before the retained capture could be
exported. Older20Hz logs cannot supply the failed19:40 internal waveform.

## Scenario: Cooperative post-capture calculation (2026-10-25)

### 1. Scope / Trigger

The LINKPAD round's 1858ms post-deflation delivery gap coincides with synchronous
calculation. Blocking code is confirmed; exact MCU duration/transport contribution
is not. Both main.c and bp_control.c must use cooperative calculation. Preserve
all existing arithmetic order, windows, ratios, compensation and freshness gates.

### 2. Signatures

```c
uint8_t BP_Algorithm_BeginCalculate(void);
BP_CalcStatus_t BP_Algorithm_CalculateStep(BP_Result_t *result);
void BP_Algorithm_CancelCalculate(void);
/* BP_CALC_IDLE, BP_CALC_BUSY, BP_CALC_DONE, BP_CALC_FAILED */
```

### 3. Contracts

- Begin rejects <20 samples, dropped captures and an already-busy job. Busy
  rejection leaves that job intact. An accepted job freezes capture storage.
- EXTRACT -> SMOOTH -> FINISH. Each extraction/smoothing step handles <=8
  samples and checks unsigned tick delta after each sample, yielding at >=5ms.
  One sample can overshoot; this is not a hard real-time 5ms bound. FINISH runs
  features/FFT separately, measured but not bounded by the envelope yield rule.
- Step clears every non-null result. Only DONE publishes a valid result; BUSY,
  FAILED and IDLE never do. After a terminal step, another Step returns IDLE.
  Cancel stops without clearing captured evidence; Reset also clears buffers.
- AddSample during a job returns0, latches dropped++ and cancels the job without
  writing capture storage. Callers retain the existing overflow fail-safe.
- Main-loop command, safety and fresh ADS streaming run between batches. Stop,
  reset, new capture and actuator overrides cancel pending output. Calibration
  changes and diagnostic ADS failure cancel calculation without new GPIO writes.
  A cancel must clear caller pending/result state, not just the algorithm phase.
- Natural completion keeps valve2 closed. Cancellation must not add a valve
  operation to a diagnostic/calibration command. Synchronous Calculate remains
  compatibility-only; no production acquisition caller may invoke it.
- Main emits `[Calc] work=...ms wall=...ms max_step=...ms extract=...ms
  smooth=...ms finish=...ms steps=...`. Work sums algorithm steps; wall includes
  main-loop intervals, but neither includes subsequent result/log transmission.
  Timing is uint32 tick subtraction (wrap-safe for these short jobs).
  Algorithm code must not print or refresh IWDG.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Busy Begin | Return0, preserve active phase/index |
| Null Step | FAILED and cancel; no result pointer access |
| Invalid capture Begin | Return0, no job or valid BP |
| Stop/reset/override mid-job | Cancel and clear result/pending; no late BP |
| ADS stream fails mid-job | Cancel result, retain existing diagnostic actuator ownership |
| Terminal Step then repeated task | No duplicate BP/Calc output |
| Envelope tick limit | Yield after a sample; never promise exact 5ms maximum |

### 5. Good / Base / Bad Cases

- Good: n2521, streamed new ADS conversions between steps, DONE once, timings
  recorded, no changed BP feature arithmetic.
- Base: invalid/no-signal waveform finishes FAILED with invalid result.
- Bad: reset halfway then print old BP; operate valve2 from calculation cancel;
  treat work time as total host-delivery gap or call host mocks board validation.

### 6. Tests Required

- Frozen legacy extraction/smoothing loops: bit-equivalent arrays at n20/31/32/
  33/64/65/256/2521/2800/3300 with constant/ramp/pulse/noisy inputs; compare final
  results and feature diagnostics, including successful FFT cases.
- Assert <=8 samples/step, tick-based early yield and wrap-safe timings, busy
  Begin preservation, null/frozen capture rejection, cancel/restart in all phases.
- Compile actual main calculation/cancel helpers: success/failure publish once,
  reset/cancel publish nothing. Real control path must begin asynchronously and
  clear pending/result on stop/reset/init. Static tests prohibit sync callers
  and guard command/safety/stream/step/IWDG order and GPIO-free cancellation.
- Require fresh Keil build, RAM/stack gate and existing safety tests. Board-only
  acceptance targets: steps <=50ms and fresh Pressure delivery gaps <=200ms,
  including final feature step and logs; retain the independent 2s host abort.
  Acceptance is scoped to the tested firmware image and input, not all jobs.
  CAPTURE_SAFE_COOP_20261025 first complete bench round: n2057/dropped0,
  max_step30ms (finish30ms), work1500ms/wall2160ms, max host gap80ms. One round
  meets these targets. A second natural capture at19:40 (n2177/dropped0,
  max_step31ms, work1581ms/wall2276ms, max host gap84ms) also met timing targets
  but FAILED BP validity: DBGFAIL MAP92.9/DBP93.7 triggers dbp>map_pressure.
  Never count clean capture/timing as a valid BP repeatability pass, relax that
  rejection to pass a bench round, or mix a cancellation run into BP statistics.
  The conditional next round was not started. Feature-selection root cause needs
  full internal waveform evidence; repeatability/runtime stack watermark remain open.
- Board cancellation validation uses `python tmp/linkpad_lowpressure_check.py
  --calc-stop`: require fresh natural done, a nonzero clean capture, wait >=300ms,
  then request stop. Reject if BP/Calc already appeared or appears during the
  following5s; require >=60 fresh Pressure records and host STOP response<=200ms.
  One n2353 case passed with160.4ms request-to-response and no BP/Calc, max host
  gap60ms. This includes host/bridge overhead, not isolated MCU stop latency;
  the active phase is inferred from the control flow, not a runtime phase probe.
  See task software_hardening_2026-10-25.md and its19:24/19:33 raw-log references.
- Host cleanup must exclude queued pre-vent Pressure records even when they are
  <2s old. Timestamp eligibility starts after the vent command completes, then
  require fresh low pressure before seal. Clearing a Python list does not flush
  the socket queue. Offline bridge regressions cover normal cancellation, late/
  early output, missing stop response, pressure timeout and queued pre-vent data;
  no test may open real device connections or send actuator commands.
  Revised cleanup was exercised in the19:40 failed-BP run: last10 before seal
  were1.0..0.9 after firmware VENT; pins sealed/pump OFF, ADS errors/recoveries0,
  target50 restored. A later5s snapshot read3.7 throughout, so closeout samples
  do not establish sustained zero or authorize a new inflation. See task record.

### 7. Wrong vs Correct

Wrong: `Calculate(&result)` in the acquisition terminal branch; refresh IWDG
inside the algorithm; enlarge the host timeout to make the gap pass.

Correct: Begin once, Step once per loop after command/safety/stream work, cancel
all pending output on overrides, measure both phase timing and host delivery.

## 1. Scope / Trigger

Applies to ADS1115 -> acquisition caller -> algorithm -> serial diagnostics.
The former algorithm needed 8352 bytes of local stack, while startup reserved only
1024 bytes (old Keil known maximum 8820). This is a confirmed memory-budget defect,
not proof that it caused the observed ADS offline event. The former 2048-sample
buffer silently truncated 53–57-second Standard BP captures.

## 2. Signatures

```c
uint8_t BP_Algorithm_AddSample(float cuff_pressure_mmhg, float raw_voltage);
uint8_t BP_Algorithm_Calculate(BP_Result_t *result);
const ADS1115_Diagnostics_t *ADS1115_GetDiagnostics(void);
HAL_StatusTypeDef ADS1115_Init(I2C_HandleTypeDef *hi2c);
HAL_StatusTypeDef ADS1115_ReadSample(ADS1115_Sample_t *sample);
```

## 3. Contracts

- `BP_SAMPLE_INTERVAL_MS=25`, `BP_ALGO_MAX_SAMPLES=3300`: nominal 82.5 seconds.
  Private float inputs, byte tick deltas and two envelopes cost 56100 bytes;
  FFT arrays additionally cost 2048 bytes.
  Never enlarge capacity independently of the startup stack and linker RAM.
- AddSample returns 1 only after storage, 0 when full/frozen or when a later
  unsigned tick delta is zero or >255 ms. Rejection latches
  `g_bp_debug.dropped_samples`; no overwrite/wrap of stored samples. All callers,
  including the relay-only main loop and both bp_control paths, must check return.
- Calculate clears a non-null result before processing. Null, insufficient data,
  or any dropped sample returns 0; partial captures must never produce valid BP.
  Reset clears the count, both envelope arrays, samples, and all debug fields.
- `[Capture] n=... capacity=3300 dropped=... duration=...ms interval=25ms` reports
  actual first-to-last timestamp span (unsigned subtraction handles tick wrap).
  Interval is nominal, not a guarantee of jitter-free 40 Hz. A 20 Hz pressure
  stream is NOT an export of the internal 40 Hz algorithm waveform.
- Stack reservation is 4096 bytes. The read-only budget checker requires >=2048
  bytes linker RAM headroom and known callgraph peak +1024 <= reserved stack.
  Callgraph unknown cycles/indirect calls and interrupt nesting still require
  target testing; this is not a measured high-water mark.
- The old sorted percentile was used only for `sorted[floor(n*0.95f)] >= 0.0001f`.
  `envelope_has_signal` counts values below threshold instead, preserving that
  gate for finite samples without an O(n²) sort or large temporary stack array.
  Existing MAP window, SBP/DBP ratios, and fixed compensation are unchanged and
  remain simulator-specific, not a general/clinical accuracy guarantee.
- ADS failure preserves raw HAL status and records stage, register, HAL error,
  HAL state, SR1/SR2, CR1, GPIOB.IDR and boot-lifetime error/recovery counts.
  Success does not erase the last failure snapshot. `stage=0` means no recorded
  error; subsequent actual transaction/probe/recovery failures replace the
  snapshot, so save the first emitted diagnostic. An ARGUMENT rejection while
  recovery is pending does not touch the snapshot/counter: no bus transaction
  occurred and it must not erase the root failure.
- The driver prints nothing and controls no actuators. A failed read returns
  immediately after snapshot, marking offline; no reset/retry occurs there.
  A later offline Init performs HAL DeInit -> I2C1 RCC reset -> HAL Init -> probe.
  This restores HAL/peripheral state, not a physically stuck external device.
  No GPIO bus pulsing or electrical changes. ReadSample commits output only when
  all stages succeed; failure must leave the caller's sample unchanged.
- I2C transactions use HAL timeout argument 10 ms, readiness probe 1 trial;
  conversion-ready deadline is 25 ms. HAL internal BUSY handling has its own
  bounds: do not claim every failed sample returns within exactly 10 ms.
- Offline diagnostic stream re-init is limited to once per >=1000 ms, independent
  of safety sampling. Idle `pressure` retries immediately; a pending post-target
  hold must cancel/vent on offline state before any explicit retry. Hold safety
  sampling continues with streaming disabled; see the
  [hold fault contract](./safety-rules.md#post-target-hold-fault-contract).
  Recovery does not
  restart the pump, clear a safety fault or close an emergency vent.

## 4. Validation & Error Matrix

| Condition | Return / response | Actuator policy |
| --- | --- | --- |
| Room in buffer | AddSample=1, update count/span | Normal caller control |
| First sample beyond capacity | AddSample=0, dropped++ | Stop pump, release PB8 (close inflation), open PC1; SAMPLE_OVERFLOW (9) |
| Later tick delta 0 or >255 ms | AddSample=0, dropped++; no partial point | Same SAMPLE_OVERFLOW emergency vent |
| Calculate with overflow/null/insufficient data | 0, non-null result invalid | No valid BP result |
| ADS transmit/receive failure | Original HAL status, stage 3/4/5 | Active caller emergency vents before diagnostics/recovery |
| Conversion not ready at deadline | HAL_TIMEOUT, stage 6 | Same active caller fail-safe |
| Probe/recovery failure | Original status, stage 2/7, offline | No automatic actuator restart |
| Offline recovery succeeds | Initialized=1, old failure retained | Emergency state remains latched |

Stage 1 is invalid argument; HAL status values are defined by STM32 HAL, not a new
wire error enum. For an emergency, cancel any SysTick pulse before setting PC1
HIGH and exit the iteration before further PWM writes.

## 5. Good / Base / Bad Cases

- Good: n~2200, dropped=0, complete low-pressure tail and coherent timestamps;
  still inspect signal quality and reference labels before dataset acceptance.
- Base: a full 3300-point buffer with no attempted extra sample is not overflow.
- Bad: n=3300, dropped>=1; reject whole capture, vent, never report valid BP.
- Bad: ADS recovery succeeds but cuff pressure is unknown; do not auto-seal.
  Use independent pressure confirmation if sensor remains offline.

## 6. Tests Required

```powershell
python -m unittest discover -s 'blood pressure monitor/test' -v
# Rebuild in Keil first; stale map/callgraph evidence is rejected.
python 'blood pressure monitor/tools/check_firmware_budget.py'
```

- Host HAL tests compile real algorithm/ADS/control C with MSVC (no device I/O).
  Assert capacity edge, overflow rejection, reset, result clearing, tick wrap,
  sorted percentile equivalence for n=1..3300, timeout/busy propagation,
  unchanged output on failure, deferred recovery, retained diagnostics, and
  production control inflate/deflate failure/overflow vent state.
- Static contracts cover every AddSample caller, relay-only terminal continue,
  shared interval, offline retry bound and diagnostics-after-stop order.
- Keil must include all production sources/startup; test/host headers and C must
  NOT enter its include paths or source groups. Require zero errors/warnings.
- Target: non-human only, verify idle pins, calibration readback, low-pressure
  stop/vent first, then Standard BP repeated capture. Follow the task validation
  document; neither host mocks nor linker checks establish pneumatic safety.

## 7. Wrong vs Correct

Wrong: `void AddSample(...) { if (full) return; }`, then calculating truncated BP;
`float tmp[BP_ALGO_MAX_SAMPLES]` on a 1 KiB embedded stack; resetting I2C inside
the read-failure path while the pump is still running.

Correct: check `AddSample(...) == 0U`, emergency-stop and exit; use constant-size
threshold counting; return the ADS failure immediately, vent first, then perform
offline Init recovery on a later safe diagnostic attempt.

## Scenario: ADS first-failure bus snapshot (2026-10-31)

### 1. Scope / Trigger

The post-target failure stage5/HAL_BUSY/TIMEOUT/SR2.BUSY is insufficient to
separate sampled bus line levels from peripheral status. Capture evidence
before any recovery. This increment does not repair the physical fault.

### 2. Signatures

`ADS1115_Diagnostics_t` appends `uint16_t cr1` and `uint16_t gpio_b_idr`.
`Debug_PrintADS1115Diagnostics` preserves ADSdiag and then emits
`[ADSbus] cr1=0x%04X pb=0x%04X scl=%u sda=%u` from the saved fields.

### 3. Contracts

Fail performs only reads for CR1/IDR, no pin reconfiguration or recovery.
PB6/PB7 decode SCL/SDA; the full saved port includes PB8. These are sequential
digital reads, not voltages or simultaneous switching-edge measurements.
Two HIGH lines with BUSY may motivate peripheral investigation but do not prove
an erratum or exclude a prior electrical transient. Idle multimeter readings
around3.2V cannot exclude such a transient either. No high-rate extra logging.

### 4. Validation & Error Matrix

- Read fails -> sample unchanged, original status returned, offline; caller vents.
- Call rejected while recovery pending -> HAL_ERROR, evidence/counter unchanged.
- Real retry fails -> update evidence and counter with that new failure.
- Recovery succeeds -> retain saved CR1/IDR even if current register inputs differ.

### 5. Good / Base / Bad Cases

Good: save ADSdiag plus ADSbus before re-init and relate to the same failed run.
Base: stage0/zero snapshots mean no failure recorded, not physically LOW lines.
Bad: read present-day GPIO after recovery and label it the fault-time state.

### 6. Tests Required

Compile actual ADS driver and inject failure; assert CR1/IDR, unchanged caller
sample, no inline reset, retained evidence/counters on offline API calls, and
retention across successful re-init with changed mock registers. Full host suite,
Keil/RAM/stack gates and fresh image-ID verification before board conclusions.

### 7. Wrong vs Correct

Wrong: call an offline ADC, overwrite stage5 with stage1, then infer argument
failure was the trigger. Correct: preserve actual transaction evidence until a
real retry yields new evidence; lost pressure data still invalidate the round.

## Scenario: Runtime main-stack watermark

### 1. Scope / Trigger

Use when the existing 4096-byte Cortex-M3 main stack needs on-target high-water
evidence. This is a diagnostic complement to the Keil callgraph budget, not a
stack overflow guard or proof for unexercised paths.

### 2. Signatures

```c
uint8_t StackWatermark_Init(void);
uint8_t StackWatermark_Get(StackWatermark_Result_t *result);
uint8_t StackWatermark_ScanRange(const uint32_t *base,
                                 const uint32_t *top,
                                 StackWatermark_Result_t *result);
```

The read-only serial command is `stack` and reports `used`, `free`, `reserved`,
`saturated`, and the pattern. The current firmware identity is
`STACK_WATERMARK_20261027`.

### 3. Contracts

- The linker exports `__stack_base` and `__initial_sp`; the reserved range must
  be exactly 4096 bytes. CubeMX `ProjectManager.StackSize`, startup assembly,
  Keil project sources, and linker map must stay consistent.
- Call `StackWatermark_Init()` as the first statement in `main`, after C runtime
  ZI initialization and before HAL/interrupt initialization. On ARMCC/ARMCLANG,
  read the live MSP and pattern only `[stack_base, align_down(MSP-128,4))`;
  conservatively count the unpainted active-frame guard as used.
- Reset-time assembly painting is invalid here: the Keil stack region is Zero RW
  and runtime ZI initialization clears the fill before `main`.
- `StackWatermark_Get` is read-only, requires successful initialization, and
  rejects a range other than the reserved 4096 bytes. `ScanRange` clears a valid
  output before validation and scans upward from stack base until the first
  non-pattern word. The `stack` command must not control GPIO or pressure.
- Measurement covers paths executed after entry to `main`; it does not capture
  transient C-runtime stack use before `main`. Fill-pattern coincidence and
  reserved-but-unwritten stack frames may underestimate historical MSP depth.
  Combine target observation with static callgraph analysis and the 1024-byte
  reserve; never claim all-path proof from one measurement.
- After a full-chip erase, restore and independently read back the current
  hardware calibration before any pressure test. Dynamic validation stays
  non-human and finishes `vent` -> fresh near-zero pressure -> `seal`.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Null output or invalid range | Return failure without an out-of-range write/read |
| MSP too near base or above stack top | Initialization fails; do not claim a valid watermark |
| Successful initialization, ordinary command | Return reserved=4096 and used+free=4096 |
| Free reaches zero | saturated=1; fail the target reserve gate |
| Only boot/diagnostic path exercised | Report baseline only, not measurement maximum |
| Serial bridge disconnected | Do not infer command execution or target state from host ACK attempt |

### 5. Good / Base / Bad Cases

- Good: exercised non-human acquisition/calculation/export path reports
  saturated=0 and >=1024 bytes free, and the static RAM/callgraph budget passes.
- Base: idle `stack` reports 1384 used / 2712 free; this establishes initialization
  only, not the dynamic path peak.
- Bad: paint the stack before C runtime ZI clearing, overwrite the live MSP frame,
  read stack during export and invalidate its state, or call the result exact
  historical maximum.

### 6. Tests Required

- Host tests compile production C and cover range bounds, null outputs, scan
  boundaries, initialization ordering and the read-only command response.
- Require CubeMX/Keil/startup synchronization, zero-warning Keil build, and the
  current static RAM/stack budget check.
- On target, require calibration/status/pin/ADS/fresh-pressure preflight, a
  non-human low-pressure safety run, a complete Standard BP run, safe vent/seal,
  strict full `/2` export and production-C replay before claiming dynamic stack
  validation. Query after computation/export without capture mutation and retain
  raw evidence. On 2026-10-28 one full 120/80, 80 BPM capture passed (n=2305,
  dropped=0, ticks=25ms, replay=117/86/75 valid); two post-export readings were
  used=1536/free=2560/reserved=4096/saturated=0. The earlier disconnected-bridge
  attempt was refused and not counted. This verifies only the exercised path;
  retain the pre-main and unexercised-path caveats above.

### 7. Wrong vs Correct

Wrong: fill the stack in `Reset_Handler` before C runtime initialization, or treat
an idle baseline as the full BP stack maximum.

Correct: initialize in the first `main` statement using the live MSP and protected
guard, then measure only after the complete target path and state the coverage
limits alongside the static reserve.

## Scenario: Pressure text length compatibility (2026-10-25)

### 1. Scope / Trigger

Two interrupted bench attempts had 2089/2129 ms host timestamp gaps near
94 mmHg, followed by 41/42 lines sharing one host timestamp. Both crossed
from 65-byte records (ads=1004mV) to 64-byte records (ads=999mV), CRLF included.
This is a reproducible formatting boundary and a transport hypothesis, NOT
proof of a CH340/USB driver defect. OmniProbe 3.2.2 alone is not proof of a fix.

### 2. Signatures

`static void Debug_PrintPressureRecord(const ADS1115_Sample_t *sample)` in main.c.
Wire fields remain `[Pressure] raw=... ads=...mV sensor=...mV est=...mmHg VALID`;
`UNCAL` is the alternative status. CRLF remains the record delimiter.

### 3. Contracts

- Format once into the existing 144-byte buffer, then measure its actual length.
- Only if length >=2, length %64 ==0 and length+1 <sizeof(buffer), insert one
  ASCII space immediately before CRLF. All numerical fields remain unchanged.
- Do not pad every line unconditionally: a different field width could then
  create another 64-byte multiple. Text length does not guarantee USB framing.
- Keep pressure telemetry at nominal 20 Hz and algorithm acquisition at nominal
  40 Hz. Do not extend the host 2-second freshness stop threshold.
- Host timestamps are delivery observations, not MCU sampling ticks.
  `sampleRateHz=0` means unknown. Internal Capture dropped=0 is insufficient
  evidence of a lossless external export or jitter-free acquisition.
- Evaluate delivery gaps separately during deflation and after acquisition.
  The first complete LINKPAD bench round had 2521 internal points / dropped=0,
  1261 deflation pressure records with a maximum host gap of 55 ms, but a
  1858 ms gap between the final deflation pressure and the next pressure after
  BP calculation/output. This leaves only 142 ms to the unchanged freshness
  gate. Synchronous Calculate is a hypothesis until MCU timing is measured;
  one complete round is not three-run repeatability or proof of driver cause.

### 4. Validation & Error Matrix

| Original record | Required output | Meaning |
| --- | --- | --- |
| 64-byte multiple, room available | One space before CRLF | Compatibility workaround |
| Other length | Byte-identical record | No unnecessary wire changes |
| Buffer has no room for suffix | No out-of-bounds write | Never sacrifice memory safety |
| Host freshness exceeds 2 seconds | Existing stop/vent remains | Reject incomplete capture |

### 5. Good / Base / Bad Cases

- Good: 7992/999/1379/93.6 VALID changes from 64 to 65 bytes; parser values match.
- Base: 8031/1004/1385/94.2 VALID remains 65 bytes without added whitespace.
- Bad: declaring USB causation from equal timestamps, or declaring bench success
  from host-only formatting tests or an idle zero-pressure observation.

### 6. Tests Required

- Host test extracts and compiles the real main.c formatter; assert field/status
  preservation, CRLF, buffer bounds and conditional padding across field widths.
- Analyzer regex must parse both unpadded and padded VALID/UNCAL records.
- Keil zero errors/warnings and budget check; main.c stays in uvprojx, host C
  remains excluded. Bench download requires fresh physical safety confirmation.
- Non-human low-pressure check precedes Standard BP. Inspect delivery around
  ads=1000 ->999 and finish with vent -> confirmed target -> seal. Compare on
  the same OmniProbe version; upgrading it concurrently confounds causal claims.
- Record maximum host pressure-delivery gaps both within the acquisition and
  across done -> Calculate -> BP -> next Pressure. Independently measure MCU
  Calculate duration before attributing the post-capture gap. Do not exclude
  that interval to claim uninterrupted telemetry or enlarge the 2-second gate.

### 7. Wrong vs Correct

Wrong: always append a space, disable freshness abort, or label idle tests as
proof of a complete Standard BP round.

Correct: conditionally pad based on actual line length, retain safety stops,
and require a naturally completed capture plus explicit safe closeout.

## Scenario: Compact 3300-point capture storage (2026-10-28)

### 1. Scope / Trigger

`CAPTURE_COMPACT_20261028` expands the in-RAM full-waveform budget without
changing float32 pressure/input values, BP feature arithmetic, actuator timing,
calibration, safety thresholds or the `bp.capture/2` wire fields. The preceding
`STACK_WATERMARK_20261027` target image remains a 2800-point image until a
new build is explicitly downloaded.

### 2. Signatures

```c
#define BP_ALGO_MAX_SAMPLES 3300U
uint8_t BP_Algorithm_AddSample(float cuff_pressure_mmhg, float raw_voltage);
uint8_t BP_Algorithm_GetCapturePoint(uint16_t index, BP_Sample_t *sample,
                                    float *envelope, float *smooth);
```

Public `BP_Sample_t` still contains two floats and a uint32 MCU tick. The
private buffers use two floats plus a uint8 tick delta per sample, two float
envelopes, and first/last uint32 tick anchors: 56100 bytes plus 8 anchors.

### 3. Contracts

- The first accepted point stores an absolute `HAL_GetTick()` anchor and delta0.
  Every later point stores `(new_tick-last_tick)` only when in `1..255` ms.
  Both values are unsigned uint32, so rollover is valid. Rejection changes no
  point or anchor, increments `dropped_samples` and invalidates the capture.
- Random-access `GetCapturePoint` reconstructs the exact uint32 tick by adding
  deltas 1..index to the first anchor. Float32 inputs are copied unchanged;
  envelope arrays and `/2` JSON fields are unchanged. Getter cost is bounded
  by 3299 additions and exporter still writes at most one line per loop.
- At capacity, an extra sample and any invalid tick delta return0. Existing
  main and BP control callers convert that rejection to SAMPLE_OVERFLOW
  emergency vent; they do not publish a partial BP or silently truncate.
  `BP_CaptureExport_Begin()` also rejects any nonzero dropped count.
- The strict decoder accepts up to 3300 points. Old `/1` and `/2` exports up
  to 2800 remain decodable. Same-source replay rejects a different firmware
  marker; archived replays retain their original reports/source fingerprints.

### 4. Validation & Error Matrix

| Input | Storage / externally visible behavior |
| --- | --- |
| First sample | Absolute tick anchor, delta0, count1 |
| Later delta 1..255 ms, including uint32 wrap | Store point; getter restores exact tick |
| Later delta 0 or >=256 ms | Return0, dropped++, no partial write; caller vents |
| Point 3300 | Accepted; no overflow yet |
| Point 3301 | Return0, dropped++; caller vents |
| Reset | Clear count, anchors, deltas, envelopes and diagnostics |
| Old 2800-point transfer | Strict decode succeeds; new same-source replay requires new marker |

### 5. Good / Base / Bad Cases

- Good: 3300 accepted 25 ms samples, exact wrap-safe ticks and float32 bits,
  zero drops and full `/2` export/replay.
- Base: a fully occupied 3300-point buffer is valid until another sample is
  attempted; preserved old 2800-point exports still decode.
- Bad: truncate an unrepresentable time delta to uint8, wrap the buffer, or
  increase three old arrays to 3300 and violate the 2048-byte RAM gate.

### 6. Tests Required

Real-C host tests cover 3300 capacity, point3301 rejection, 0/1/25/255/256 ms
cases, uint32 wrap, caller emergency vent, and 2000/2800/3300 `/2` roundtrips
with exact intervals and envelopes. The full host suite, zero-warning Keil
Rebuild, >=2048-byte SRAM headroom and callgraph stack gate must pass before
physical validation. Target dynamic stack/export timing remains a separate
non-human gate after download.

### 7. Wrong vs Correct

Wrong: cast a 256 ms interval to uint8 and export it as a 0 ms interval.

Correct: reject that capture point, count a drop, and let the active caller
stop the pump and open the emergency vent.

## Bounded target190 bench acquisition (2026-10-28)

- `tmp/linkpad_lowpressure_check.py --target190` is a one-shot non-human
  harness mode for the `CAPTURE_COMPACT_20261028` image. It requires valid
  calibration/ADS, 40 fresh near-zero pressure samples, sealed-safe pins and
  enabled serial write permission before setting190 and starting once.
- During the run, pressure must remain fresh within2s and below the205mmHg
  host abort ceiling. Firmware safety failure, overflow/timeout, missing fresh
  pressure or the105s acquisition deadline raises an error; the armed cleanup
  sends stop then vent, waits for fresh low pressure, seals only after the low
  gate, and restores target50. The harness never retries inflation.
- A terminal `/2` capture is acceptable harness evidence only when `[Deflate]
  done`, `[Capture] n>0`, `n<=capacity`, `dropped=0`, and `[Calc]` are all
  present. A `valid=0` BP remains invalid but does not discard a complete
  research waveform; export and replay still require the normal strict gates.
- The 2026-10-28 user-authorized non-human run peaked190.4mmHg and completed
 3153/3300 points (147 remaining), followed by strict export, bit-equal
  production-C replay and two post-export stack checks. This is one successful
  case, not a repeat-capacity guarantee. Do not repeat190 or raise the target
  from this single run without verified ratings for the connected cuff/tubing/
  fittings and a worst-case sample budget with meaningful margin.
- Fake-bridge tests must cover both complete capture with invalid BP and an
  over-ceiling abort that sends stop/vent/seal, issues no second start and
  restores target50.

## High-target bounded capture (2026-11-01)

- The `HIGH_PRESSURE_CAPTURE_20261101` image uses a closed-loop deflation target
  of 3.0 mmHg/s for inflation targets >=200 mmHg; lower targets retain 2.0
  mmHg/s. Active capture rejects target changes. This is a buffer-capacity
  strategy, not evidence that the BP algorithm is accurate.
- A non-human Standard BP Preset 3 / External Cuff 200/150, 80 BPM, 0.60 cc
  development round reached 220.1 mmHg and exported 2289/3300 points over
  57.2 s with exact 25 ms MCU ticks and zero drops. One complete round does not
  establish capacity for other pneumatic settings or hardware.
- Preserve the bounded host pressure, freshness, time and closeout gates before
  another physical round. A failed initial target-220 attempt did not rise in
  12 s; the later operator confirmation of load-side 12 V does not establish
  power state before that first attempt. Raw zero stability must be assessed
  from fresh raw samples because displayed negative pressure clips to zero.
