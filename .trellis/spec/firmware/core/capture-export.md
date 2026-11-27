# Capture export, valve evidence and production-C replay (2026-10-25)

## Range-adaptive Standard BP offline candidate (2026-11-01)

### 1. Scope / Trigger

Use `tools/bp_standard_adaptive.py` for complete non-human `bp.capture` exports.
The BP Pump 2 manual lists seven fixed Standard BP presets; User Defined is a
separate configurable eighth profile, not another fixed preset. The tool is
development-only and never changes the firmware BP result or calibration.

### 2. Signatures

`infer(capture) -> dict` reads strict-decoder output without panel labels.
`analyze_path(Path) -> dict` strictly decodes one verified transfer.
`audit(manifest_path: Path, user_defined: dict | None) -> dict` checks manifest
hashes and adds panel comparison only after inference. CLI: run
`python tools/bp_standard_adaptive.py [--manifest PATH] [--output PATH]
[--user-defined SBP/DBP/MAP/BPM]`, or
`python tools/bp_standard_adaptive.py --capture INPUT --output OUTPUT`.

### 3. Contracts

Input is full `bp.capture/1..4` with 25 ms MCU tick spacing. Analyze only
20..300 mmHg after 80 head and 15 tail samples. Band-pass raw voltage and
form per-beat height/area in 10 mmHg pressure bins and report their envelope
peak only when both original tails pass. Exploratory 50%/60% crossings may be
retained as explicitly unvalidated diagnostics. Do not use panel SBP/DBP/MAP
during inference, apply the old -10/-5 offsets, or substitute preset values.
Output status is `envelope_candidate` or `abstain`; SBP/DBP stay null and
bp_output_allowed stays false. User Defined audit labels are limited to
60..140 BPM in this version. No device or actuator I/O.

### 4. Validation & Error Matrix

| Condition | Result |
| --- | --- |
| Complete stable waveform with both tails | Envelope peak, cadence and exploratory crossings; SBP/DBP null |
| Missing export, irregular MCU ticks, weak cadence or incomplete pressure span | Abstain with null BP values |
| Missing peak support, tail coverage or height/area peak agreement | Abstain with explicit reason |
| Manifest verified-file hash mismatch or corrupt transfer | Error; never silently accept |
| Capture output path equals input or enters raw directory | CLI error before write |

### 5. Good / Base / Bad Cases

Good: a complete 120/80 run gives a development candidate without reading
the 120/80 label during inference. Base: 200/150 with incomplete upper tail
abstains. Bad: clamp MAP to 80..100 or return the preset SBP/DBP on failure.

### 6. Tests Required

`test_standard_adaptive.py` covers six supported synthetic peak ranges, the
lowest 60/30 range abstention, User Defined, 60/120/140 BPM, missing high
tail, absent pulse, irregular ticks, single-file parity, and retained
development abstentions. Run the complete Python suite and regenerate the
audit. Before any firmware port, add actual-C replay tests, Keil zero-warning
build, SRAM/stack budget and non-human pneumatic validation.
The synthetic waveforms must not encode the same SBP/DBP ratio crossing used
by the algorithm as their answer. Seen development runs cannot validate a
ratio rule selected or inspected on those same runs.

### 7. Wrong vs Correct

Wrong: treat simulator labels as inputs and report 255/195 as measured BP
without a qualified capture. Correct: infer from raw waveform first, compare
with the panel only afterward, and leave unobserved presets unvalidated.

## Offline dataset catalog contract (2026-10-31)

### 1. Scope / Trigger

`bp_capture_catalog.py` inventories archived `data/raw/firmware_capture_exports/*.ndjson`
for the non-human dataset. It is read-only with respect to raw samples and does
not operate the serial port, BP Pump 2, valves or production-C replay.

### 2. Signatures

`catalog(directory: Path, root: Path = ROOT) -> dict` returns a deterministic
`bp.dataset_catalog/1` document. CLI: `python 'blood pressure monitor/tools/bp_capture_catalog.py' --json NEW.json --markdown NEW.md [--input DIR]`.

### 3. Contracts

Each file is passed to the existing `bp_capture.decode`. A valid transfer has
`file_sha256` of original bytes and `capture_sha256` of newline-joined exact
validated MCU records. `duplicate_of` points to the first sorted file with that
capture hash. The summary counts files, valid/failed files, unique captures and
duplicates separately. MCU tick deltas use unsigned 32-bit wrap, pressures and
calibration are decoded from float32 bits, and unknown panel/fixture metadata is
null. Every historical row has `dataset_role=historical_development`,
`release_ready=false`, and `replay_status=not_run`.

### 4. Validation & Error Matrix

| Input | Result |
| --- | --- |
| Complete direct or EK bridge RX capture | `decode_valid`, timing/pressure summary |
| Same MCU records in another envelope | Same capture hash, `duplicate_of` set |
| Missing end, malformed records or bad checksum | `decode_failed` with error, continue other files |
| No NDJSON input | Error; no empty-success catalog |
| Existing/equal output paths or output inside raw input | CLI rejects before writing |

### 5. Good / Base / Bad Cases

Good: a complete verified export and its bridge log count as one unique capture.
Base: a complete `calc=0` diagnostic is transport-valid but not a BP truth record.
Bad: a truncated export stays in the inventory with its failure reason and is
never accepted as a complete waveform.

### 6. Tests Required

`test_capture_catalog.py` asserts bridge/direct deduplication, different file
hashes, truncated-file isolation, null labels, false release flag and explicit
`not_run` replay. Full `test_*.py` host suite must pass. Regenerate the catalog
and compare JSON/Markdown byte-for-byte for deterministic output.

### 7. Wrong vs Correct

Wrong: count each `.ndjson` as a separate experiment or infer BP panel labels
from the filename or firmware BP result. Correct: strict-decode, hash original
MCU records, preserve missing metadata as null and record labels prospectively.

## Bounded `/3` step trace (2026-10-29)

The `CAPTURE_STEP_TRACE_20261029` image retains the first 12 adjacent
>=5 mmHg pressure changes after a real valve pulse. Each event records
the sample index, phase in milliseconds since that pulse (255 means the
exact phase exceeded 254 ms), and the commanded valve-on time. The existing
aggregate `steps` remains the full count; `trace_n=min(steps,12)` makes
later-event truncation visible. The C recording path has no GPIO, serial
or algorithm-result side effects. Do not interpret phase association as
proof that a valve caused the pressure change.

`bp.capture/3` places exactly `trace_n` ordered `step` rows after the single
`valve` row and before `features`; all rows are included in the FNV checksum.
The strict decoder validates order, count, actual adjacent pressure-step
magnitude, phase bin and valve-on range. `/1` and `/2` archived captures
remain decodable. After a firmware download, retain the sealed fresh-zero,
calibration and ADS preflight, and use non-human tests before considering
physical source attribution. A full-chip erase requires restoring the
documented current calibration and verifying its readback.

## 1. Scope / Trigger

`CAPTURE_VALVE_20261025` extends the cross-layer evidence contract from stored MCU
samples to offline replay with aggregate timing from the actual valve-open path.
It does not change algorithm arithmetic, tuning or actuator timing.
The failed 19:40 acquisition has only a 20Hz diagnostic log; its internal nominal
40Hz waveform cannot be reconstructed retroactively. Software checks and the
non-human low-pressure target export/abort gates passed. A new Standard BP
`/1` waveform was acquired. The `/2` image was flashed and its safe idle startup,
ADS state and calibration restoration passed on 2026-10-26 without actuator
operation. Its subsequent non-human50mmHg natural capture and complete `/2`
export passed with377 points,48 actual valve pulses,200ms period,1..4ms on-time,
checksum and bit-equal production-C replay. A Standard120/80,80BPM `/2` waveform
also passed transport/replay: n2225/dropped0,113/91/75 valid1,279 pulses at200ms,
on-time1..4ms and no >=5mmHg aggregate step. Six offline >=2mmHg differences all
fell on the200ms schedule boundary, so small phase association remains while the
prior +/-14mmHg shocks did not reproduce. Three consecutive complete same-image
Standard120/80 runs on 2026-10-27 now provide verified `/2` replay evidence; do not
infer valve causation or tune from this small batch. Runtime stack watermark remains
pending.

## 2. Signatures

```c
typedef struct {
    float slope, intercept;
    uint8_t cal_valid, raw_kind;
} BP_CaptureContext_t;
void BP_Algorithm_SetCaptureContext(uint8_t raw_kind, uint8_t cal_valid,
                                    float slope, float intercept);
const BP_CaptureContext_t *BP_Algorithm_GetCaptureContext(void);
void BP_Algorithm_RecordValvePulse(uint32_t timestamp_ms, uint8_t on_ms);
const BP_ValveDiagnostics_t *BP_Algorithm_GetValveDiagnostics(void);
uint32_t BP_Algorithm_CaptureRevision(void);
uint8_t BP_Algorithm_CaptureState(void);
uint8_t BP_Algorithm_GetCapturePoint(uint16_t index, BP_Sample_t *sample,
                                    float *envelope, float *smooth);
typedef uint8_t (*BP_CaptureWriter_t)(const char *line);
uint8_t BP_CaptureExport_Begin(void);
void BP_CaptureExport_Cancel(void);
void BP_CaptureExport_Task(BP_CaptureWriter_t writer);
uint8_t BP_CaptureExport_IsActive(void);
```

Command: `capture export`. Offline command from repository root:

```powershell
python 'blood pressure monitor/tools/bp_capture.py' capture.ndjson --csv capture.csv --ndjson verified.ndjson --report replay.json
```

The offline tool has no serial/TCP/actuator I/O. Replay requires MSVC C tools;
`--decode-only` validates/converts without compiling. Output paths must be distinct
new files and must not overwrite the input.

## 3. Contracts

### Capture lifecycle

- Immediately after Reset, both acquisition callers snapshot calibration and
  voltage provenance. `raw_kind=1` is ADS pin V (full control); `2` is reconstructed
  sensor V (relay mode). Preserve this existing difference. `oscillation` stores
  algorithm input V, not oscillation amplitude in mmHg.
- Context can be set only with an empty buffer and idle calculation. Reset
  clears it. Acquisition rejects `cal clear/write` so a capture cannot mix
  calibrations; later idle changes do not rewrite the stored snapshot.
- State: 0 uncalculated, 1 busy, 2 completed valid BP, 3 completed invalid BP,
  4 cancelled. States 2/3 have complete envelope arrays; 0/4 export null arrays.
  A completed invalid BP still retains evidence. Cancelling an idle calculation
  preserves its terminal state, allowing stop/vent/seal before export.
- Reset, accepted AddSample, BeginCalculate, active CancelCalculate, overflow,
  and accepted context changes invalidate an exporter via revision changes.
  AddSample also returns the capture to state0. Read access never changes GPIO.
- Reset clears valve diagnostics. BeginCalculate preserves them. The record API
  is called immediately after the real `VALVE2_OPEN()` in `DeflatePulse_Start()`;
  it records the actual MCU tick and 1..90 ms commanded on-time and has no GPIO,
  serial, watchdog or calculation-result side effect. Each accepted pulse changes
  capture revision, so a concurrent export cannot silently mix evidence.
- Consecutive pressure changes with absolute magnitude >=5.0 mmHg are diagnostic
  steps. After the first real pulse, AddSample counts them into eight 25 ms bins
  for phase 0..199 ms relative to the latest pulse and one >=200 ms bin. It retains
  the maximum positive/negative step index, signed delta, phase and pulse on-time.
  This is aggregate evidence, not another per-sample array.

### Scheduling and safe-state gate

- Begin rejects active export, empty capture, calculation busy or unknown context.
  Repeated Begin preserves an existing transfer. Export owns only cursor/hash/
  revision and uses one 512-byte stack line; it does not copy sample arrays.
- Each Task writes at most one line. Writer returns1 only after full successful
  UART transmission. Failure, revision mismatch or cancellation terminates without
  a successful end record. A failed end transmission is incomplete too.
- Main requires stream enabled, ADS ready, valid calibration, successful pressure
  sample age <=250ms, pressure in [-5,+5]mmHg, PB8 HIGH (released), PC1 LOW and PC8 HIGH. Manual
  pump/hold/deflate/hold-pending/calculation and full inflate/deflate are forbidden.
  Recheck each loop. These calibrated readings do not replace reference pressure.
- Any other recognized command cancels export before normal command handling;
  repeated `capture export` reports rejection while retaining the current transfer
  when otherwise safe. Safety, sampling, calculation and measurement tasks precede
  export; main-loop IWDG refresh follows it. UART timeout remains bounded at100ms
  per export line; actual stop latency remains a hardware acceptance item.
- A failed ADS sample during export clears `s_last_pressure_sample_valid` and
  causes the next main-loop `CaptureExport_IsSafe()` check to cancel export.
  Cancellation emits no terminal `end` or explicit abort row. The offline
  decoder must reject the partial transfer. A host may recognize the logged
  `[Pressure] sample failed`/`[Stream] read failed` and stop waiting early,
  but may retry only after fresh post-seal low pressure, valid calibration,
  ADS recovery and safe GPIO are confirmed. The retained capture must be
  exported as a new complete transfer, never stitched to the partial one.
- The host export helper retains those failure diagnostics and checks only
  events with bridge timestamps at or after its `capture export` request;
  old queued diagnostics must not interrupt a new transfer. A complete `end`
  still goes through the strict decoder before success is reported. A fresh
  read failure without `end` raises immediately and enters the existing
  stop -> vent -> fresh-low -> seal closeout, rather than waiting for the
  100-second export deadline. This is host-side failure reporting, not an
  additional firmware terminal record or permission to reuse partial data.
- This does not repair the pre-existing single pending-command ISR slot: commands
  sent rapidly can overwrite each other. Never promise a prioritized stop queue.
- After a non-human External Standard BP run, the BP Pump 2 may stop automatically
  once external pressure is released. Treat at least 40 consecutive fresh stream
  samples in the export preflight range `[-2,+1]mmHg` as the operational stopped/
  low-pressure gate. Do not repeatedly ask for a panel Stop when this gate passes;
  request a panel-state check only if pressure fails to settle, keeps oscillating,
  or the next run cannot start. This does not change the mandatory firmware
  `vent -> fresh low pressure -> seal` closeout or prove reference zero accuracy.
- Repeat the fresh-sample preflight **after seal**; do not reuse low samples
  observed with the vent open. On2026-10-28, the2161-point compact-image
  baseline initially met the closeout low-pressure condition but sealed pressure
  then rebounded to3.1-3.5mmHg. The host correctly rejected before sending
  `capture export`. Repeat vent -> fresh near-zero -> seal, then collect at least
  40 new post-seal samples in `[-2,+1]mmHg` before retrying export only. Do not
  relax that gate, change calibration, reinflate or infer a cause from rebound
  alone. The second vent/seal produced a stable0.4-0.6mmHg five-second snapshot
  and the same retained capture exported successfully. Evidence:
  `tmp/capture_export_20261028-163445.ndjson` (refused preflight) and
  `tmp/capture_export_20261028-163539.ndjson` (complete export).
- For a prospective non-human round, retain the raw ADS count and reconstructed
  sensor voltage before inflation and for at least 10 seconds after seal. A
  displayed near-zero estimate can conceal a baseline shift. If post-seal raw
  counts drift materially from the same round's unloaded preflight, preserve
  the capture as development evidence, pause repeat inflation, and check
  residual pressure with `vent -> fresh near-zero -> seal` and an independent
  reference before claiming a stable zero. The 2026-11-01 120/80 round had
  preflight raw 1316..1322, first post-seal raw rising to 1420..1425 despite
  est=0.3, then raw 1324..1332 after a second vent/seal. This observation
  alone does not identify pneumatic rebound versus sensor drift.
- In a bounded zero-pressure PC1-only comparison, preserve exact `vent`/`seal`
  echoes, safe pin states, raw ADS counts, sensor voltage, fresh pressure samples
  and a final sealed-zero check. On 2026-11-01 two cycles had open raw means
  1367.83/1365.75 and sealed means 1317.25/1313.22 while displayed `est`
  stayed 0.0. This establishes a repeatable state association on one sensing
  chain; independent simultaneous pressure evidence is needed to distinguish
  pneumatic from electrical effects. Do not tune calibration from this test.
- `tmp/linkpad_capture_io.py export --firmware <marker>` currently looks for
  `sw=<marker>` in the diagnostic status response, but the compact image's
  `[Status]` line has no `sw=` field. That optional preflight therefore
  rejects before sending `capture export` and enters its stop/vent/seal
  exception closeout. For this image, run `export` without that option after
  the complete post-seal gate, then require the strict export `begin.firmware`
  and production-C replay marker to match `CAPTURE_COMPACT_20261028`. Do not
  count a rejected preflight or repeated export of one RAM buffer as a new
  pressure run.

### Wire format

New firmware emits one JSON line per record with CRLF and
`schema="bp.capture/2"`:

| type | Required additional fields |
| --- | --- |
| begin | firmware, n, dropped, interval_ms, raw_kind, cal_valid, slope, intercept, calc |
| point | i, t, p, v, e, s |
| valve | pulses, period_min, period_max, on_min, on_max, threshold, steps, phase, rise_found, rise_i, rise_d, rise_phase, rise_on, fall_found, fall_i, fall_d, fall_phase, fall_on |
| features | map_i, map_p, sbp_found, sbp_p, dbp_found, dbp_p |
| end | n, hash |

- `/2` contains exactly one begin, n ordered points (i=0..n-1), one valve,
  one features and one end, in that order. `/1` remains decode-compatible with
  begin + points + features + end and must not contain a valve row.
  n=1..3300 (old `STACK_WATERMARK_20261027` captures were limited to 2800),
  dropped=0, interval_ms=25, raw_kind=1/2, cal_valid=0/1,
  calc=0/2/3/4. Main safe gate additionally requires current valid calibration.
- `t` is uint32 MCU tick in ms. `p` is pressure mmHg; `v` is input V;
  `e`/`s` are extracted/smoothed envelope V. All floating values (including
  calibration and feature pressures) are decimal uint32 IEEE754 float32 bits,
  not decimal float approximations. e/s are null in states0/4. Only completed
  states give the feature row its completed-calculation interpretation.
- `map_i` is an in-range sample index; found flags are0/1. Feature pressures
  are algorithm diagnostic points before final reported-BP compensation.
- `threshold`, `rise_d` and `fall_d` are float32 bit patterns; threshold is exactly
  5.0 mmHg. `phase` is an array of exactly nine unsigned counts whose sum equals
  `steps`. Zero pulses require zero ranges/events. One pulse has no period; two or
  more require `1 <= period_min <= period_max < 2^31`. Present rise/fall evidence
  requires index1..n-1, the correct delta sign/magnitude and nonzero on-time;
  absent evidence uses all-zero detail fields.
- FNV1a starts2166136261, XOR each UTF8 byte then multiply16777619 modulo2^32.
  `/2` hash covers exact begin + all point + valve + features JSON bytes, excluding
  every CR/LF and excluding end. `/1` retains its original coverage. Do not
  parse/reserialize before verifying the hash.
- Decoder accepts direct serial text and OmniProbe `type=text` RX lines;
  ignores diagnostic logs, sample projections and TX echoes. A truncated capture
  line, duplicate keys, mixed versions, missing/repeated/out-of-order records,
  inconsistent valve aggregates, nonfinite float,
  busy calc, overflow, invalid null envelope, checksum mismatch or missing end
  fails validation. MCU ticks must advance modulo2^32, each delta and total span
  <2^31ms. Nominal25ms is not proof of actual40Hz timing.
- CSV preserves float bits and MCU elapsed time. Replay compiles production C,
  feeds original float bits/ticks, compares completed arrays/features/validity,
  reports min/max intervals and source SHA256. ARM/MSVC bit equality is measured,
  not guaranteed. Synthetic fixtures are not board or clinical evidence.

## 4. Validation & Error Matrix

| Condition | Required outcome |
| --- | --- |
| Unsafe pins, stale/invalid/NaN pressure, ADS offline or stream off | Reject/cancel; no GPIO writes |
| Reset/new sample/calc/mutation during export | Revision abort; no accepted complete transfer |
| Other recognized command, including stop | Cancel before normal command handling |
| Acquisition active and cal clear/write | Reject calibration mutation |
| Writer fails or input ends early | Missing/invalid end; offline rejection |
| `/2` valve missing, repeated, reordered, semantically invalid or tampered | Offline rejection |
| Valid legacy `/1` without valve row | Decode succeeds with valve diagnostics absent |
| Invalid BP with completed calculation | Export complete e/s and feature evidence, calc3 |
| Any dropped sample, including an unrepresentable MCU tick gap | Export begin rejects incomplete capture |
| Cancelled/uncomputed calculation | Export null e/s; no stale-array claim |
| Different firmware ID in replay | Reject comparison against local production C |
| Existing/overlapping output paths | CLI error; preserve original files |
| Post-seal samples outside host `[-2,+1]mmHg` gate | Do not send export; repeat vent/fresh low/seal and collect new post-seal samples |

## 5. Good / Base / Bad Cases

- Good: natural failed BP, vent -> fresh reference-confirmed low -> seal, capture
  retained, complete `/2` transfer and checksum pass; valve aggregate directly
  identifies actual pulse timing before replay exposes feature mismatch.
- Base: uncomputed capture exports null envelopes; offline replay can compute them
  but does not claim they were computed on target. A `/1` file decodes with no
  valve evidence and cannot support direct valve-causation claims.
- Bad: reconstruct40Hz from20Hz logs, accept a transfer without end, silently use
  current calibration as capture metadata, or relabel relay sensor V as ADS V.

## 6. Tests Required

- `test_capture_export.py`: real production C exporter/algorithm `/2` roundtrip at
  2000/2800/3300 samples, aggregate pulse/step evidence, `/1` compatibility, failed/
  cancelled/uncomputed states, one line per Task, lifecycle, transport failure and
  strict decoder/CLI missing/duplicate/reordered/tampered valve protection.
- `test_host_firmware.py` + `capture_gate_regression.c`: real main.c predicates,
  pin combinations, active jobs, freshness boundaries/wrap, pressure bounds,
  NaN/Inf, stream/cal/ADS gates. Preserve legacy envelope bit-equivalence tests.
- `test_capture_contract.py`: main cancellation and safety scheduling, cal mutation
  rejection and Keil source/header registration.
- Host export helper regression: feed a retained ADS failure diagnostic through
  the real host export loop with a fake bridge. Assert prompt failure before
  the 100-second deadline, no success result, and stop -> vent -> fresh low ->
  seal; reject the saved partial transfer with the strict decoder. A separate
  non-human, zero-pressure normal export checks the complete `end` path without
  deliberately provoking an ADS/I2C fault on hardware.
- Valve increment full suite:73 tests passed. Keil V6.22:0 errors/0 warnings;
  Code48432, RO6136, RW28, ZI63276. Budget used63304/65536B, headroom2232B,
  stack4096B, known peak1304B plus1024B reserve. The aggregate added64B total RAM;
  the bounded exporter line grew384 ->512B and remains inside the stack gate.
  Target stack watermark is not measured. Rebuild/budget-check after firmware edits.
- Non-human 50mmHg target validation on the flashed image: natural capture n321,
  dropped0, MCU span8000ms and every exported tick delta25ms. A calc3 no-pulse
  result exported begin +321 points+features+end with checksum211184480; strict
  decode and production-C replay passed with zero envelope/smooth error and equal
  feature bits/validity. This is a transport/replay fixture, not BP validity.
- Complete begin-to-end delivery took5596ms. Pressure telemetry continued for107
  records with maximum54ms host delivery gap. Stop after27 capture records cancelled
  without end; observed request-to-safety-response was23.2ms including host/bridge/
  serial overhead. Vent ->10 fresh low-pressure records ->seal restored PC0/PC1 LOW (historical wiring before the 2026-10-31 PB8 migration),
  PC8 HIGH. Stream-off/stale export rejected; stream recovery and a subsequent
  identical complete export passed. Keep the2s host freshness abort unchanged.
- `cal` diagnostics print intercept to two decimals (`-19.89`) after writing
  `-19.887`. Validation scripts must parse numeric fields and compare within the
  displayed precision; exact source-string comparison is not a calibration check.
- New Standard120/80,80BPM waveform: n2089/dropped0/span52200ms, every MCU delta
  25ms, calc2 and target result93/90,56BPM. Complete export hash3282054663 took
  37163ms while697 pressure records continued with maximum60ms host gap. Production
  C replay was bit-equal for envelopes/features/validity. Firmware valid means only
  internal range/order checks passed; it is not reference-accuracy acceptance.
- The waveform explains the poor selection without justifying a tuning change.
  MAP smooth maximum53.67mV occurs at index606/P97.0 during large pressure shocks;
  SBP/DBP raw points are index225/P103.2 and index625/P95.3 before fixed compensation.
  There are42 adjacent pressure changes >=4mmHg;20 fall exactly on elapsed_ms%200=0,
  matching the valve pulse schedule, but that historical `/1` transfer has no valve
  GPIO/on-time trace, so call it strong phase association rather than direct causation.
  The new `/2` software applies only to future captures. One sealed export
  correctly aborted when a live pressure transient reached8.3mmHg (>5 gate).
- Pulse FFT currently uses only points0..255. In that window the0.9375Hz/56.2BPM
  magnitude0.3031 barely exceeds the1.40625Hz/84.4BPM magnitude0.3022; later256-point
  windows predominantly select75/84.4BPM. The exact max-bin rule therefore explains
  this56BPM result, while later data contains the expected-frequency neighborhood.
- Three consecutive complete same-image Standard120/80,80BPM runs on 2026-10-27
  produced `103/82@84`, `118/88@75`, and `114/90@75`. Their verified `/2` captures
  contain 2129/1921/1737 points with zero drops, exact 25ms tick intervals and
  bit-equal production-C replay. Batch mean/sample-SD/range are SBP
  111.67/7.77/15mmHg, DBP 86.67/4.16/8mmHg and pulse 78.0/5.20/9BPM. The first
  run has four >=5mmHg valve-phase steps; the next two have none. This completes
  the small same-image repeatability acquisition gate, not clinical accuracy,
  ISO81060-2 compliance or valve causation. Runtime stack water level remains open.

## 7. Wrong vs Correct

```text
Wrong: receive n point rows -> publish a complete dataset; replace MCU time with host time.
Correct: validate begin/order/count/features/end/hash and MCU ticks -> retain raw records.

Wrong: change DBP threshold to make 19:40 pass without its full waveform.
Correct: obtain a new full capture, inspect pressure reversals/envelopes/features,
         distinguish direct dbp>map rejection from the still-unknown root cause.

Wrong: infer valve timing from `elapsed_ms % 200` or store a fourth 2800-point array.
Correct: record each real open call, export bounded aggregate phase evidence, and
         require the checksummed `/2` valve row before making a direct-correlation claim.
```

## 8. Host-only beat diagnostics and capture budget (2026-10-28)

### 8.1 Scope / Trigger

`tools/bp_beat_analysis.py` is a research diagnostic for completed exports. It
does not alter the production algorithm, board state, calibration or safety
thresholds. `smooth_v` peaks are only *candidate* beats; cadence must be checked
before any MAP/SBP/DBP candidate is shown.

The later `raw_cadence` field separately checks periodicity in captured `v`
(`algorithm_input_v`). The production `smooth_v` is a trailing 32-point/800 ms
average of absolute detrended voltage, so its local maxima are not reliable
one-to-one beat markers at 80 bpm (750 ms period). Keep the older `beats` field
for comparison, but do not interpret its `cadence_unreliable` status as evidence
that the original voltage lacks the simulator's pulse cadence.

### 8.2 Signature

```powershell
python 'blood pressure monitor/tools/bp_beat_analysis.py' capture.verified.ndjson
python 'blood pressure monitor/tools/bp_beat_analysis.py' capture.verified.ndjson --bpm 80 --current-target 150 --future-targets 170 180 190
```

The host needs NumPy and SciPy. `captures` accepts one or more complete `/1` or
`/2` files. `--bpm` is optional and affects only the older reference-based
`raw_cadence` and `beats` diagnostics. `--current-target` and
`--future-targets` must be supplied together for capacity projection. The CLI
has no device I/O. `pulse_estimate` never consumes the declared BPM.
The JSON report adds `raw_cadence` with `status`, `eligible_count`,
`pressure_range_mmhg`, `peak_count`, `median_interpeak_ms`,
`cadence_fraction`, `dominant_hz`, `dominant_bpm`, and `prominence_v` when a
long enough regular segment exists. No raw-cadence status contains BP candidates.
The default `pulse_estimate` reports `pulse_bpm` only when its status is
`estimated`; all other statuses omit that key. It also reports eligible count,
pressure window, peak count, cadence fraction, spectral ratio, bandpass RMS,
full/split dominant frequencies and median interpeak time when available.

### 8.3 Contracts

- Reuse `bp_capture.decode()` for schema, count, order, float32 and checksum
  validation. Analyze only `calc=2/3` completed envelopes. Exclude the initial
  80 points and final 15 samples, and search local `smooth_v` peaks only above
  15 mmHg. The declared BPM sets the expected sample spacing.
- `cadence_fraction` is the fraction of peak gaps within 20% of expected spacing.
  Below 0.7, emit `cadence_unreliable` with counts/spacing only: suppress all
  BP candidates. Regular synthetic beats may emit `diagnostic_only` candidates,
  never a valid BP result or compensated clinical value.
- `raw_cadence()` requires exact 25 ms MCU ticks before treating voltage as
  uniformly sampled. It filters the complete `v` trace with a third-order
  zero-phase Butterworth 0.9-4.0 Hz bandpass, then analyzes the span between
  the first and last eligible sample at 40-120 mmHg, excluding the first 80 and
  last 15 samples. At least 256 eligible samples and five peaks are required.
  Peak prominence is `max(0.0005 V, 0.35*(P95-P5))` and minimum spacing is
  65% of the declared BPM period. `cadence_detected` requires >=70% of gaps
  within 20% of that period *and* Welch's strongest 0.9-4.0 Hz bin within 20%
  of declared BPM. This is a periodic voltage-component check, not proof of
  true physiology, simulator fidelity, or BP accuracy. BPM below the 0.9 Hz
  passband reports `expected_outside_band` rather than a positive match.
- `estimate_pulse()` uses the same strictly decoded `v` and exact 25 ms ticks,
  but selects the strongest Welch bin from 0.9-4 Hz with no label input. It
  requires at least 512 eligible 40-120 mmHg samples, bandpass RMS >=0.001 V,
  strongest-bin power >=8 times the band median, at least eight peaks, >=70%
  peak gaps within 20% of the selected period, and both half-segment dominant
  bins within 20% of the full-segment bin. It reports rounded bin BPM only
  after all gates pass. Welch's 512-sample, 40 Hz bin spacing is 0.078125 Hz
  (4.6875 BPM), so do not interpret the output as sub-BPM precision. These
  thresholds are host diagnostic gates, not a firmware or clinical acceptance
  specification. A 60 BPM physical-reference capture was later obtained, but
  it was stopped early and has `calc=0`; only its raw-voltage pulse estimate
  was evaluated, not a complete BP result.
- Capacity uses the observed mean rate `(first_pressure-last_pressure)/duration_s`.
  For each future target, project added samples as
  `round((future-current)/mean_rate * 40)` and compare with the source image's
  capacity (2800 for `STACK_WATERMARK_20261027`, 3300 for
  `CAPTURE_COMPACT_20261028`; unknown markers require explicit `--capacity`). This assumes
  unchanged hold loss and deflation rate, so `remaining_samples >= 0` is not
  permission or a capacity guarantee. Current 150/100 captures at target150
  project 2805-2972 samples at target180. Each extra firmware point costs
  20 RAM bytes across sample and envelope arrays; target190's worst observed
  projection needs 370 extra points (7400 B), beyond the last measured 2224 B
  static headroom. An acquisition/storage redesign must precede that target.

### 8.4 Validation & Error Matrix

| Input | Behavior |
| --- | --- |
| Incomplete/tampered export | Strict decoder raises; no diagnostics |
| Uncalculated/cancelled envelope | Reject beat analysis |
| BPM outside 30..240 or nonfinite/negative target | Reject |
| Fewer than five candidate peaks | `insufficient_peaks`, no BP candidates |
| Cadence fraction below 0.7 | `cadence_unreliable`, no BP candidates |
| Raw `v` ticks not all 25 ms | `raw_cadence.status=irregular_sampling`; no positive cadence claim |
| Fewer than 256 eligible 40-120 mmHg samples | `raw_cadence.status=insufficient_samples` |
| Raw cadence or Welch bin differs from declared BPM | `raw_cadence.status=cadence_unreliable`; no BP candidates |
| Pulse estimate has insufficient pressure span or irregular MCU ticks | `insufficient_samples` or `irregular_sampling`; no `pulse_bpm` |
| Pulse estimate fails RMS, spectral, peak count, spacing or split consistency | `signal_unreliable`; no `pulse_bpm` |
| Nonpositive observed pressure drop or duration | Reject capacity projection |

### 8.5 Good / Base / Bad Cases

- Good: regular synthetic beats produce an uncalibrated diagnostic curve and
  candidate crossing pressures; all output remains labeled research-only.
- Base: the seven retained 100/65 and 150/100 exports fail cadence and retain
  only peak-spacing and capacity evidence.
- Bad: infer that every smoothed-envelope peak is a heartbeat, publish its
  crossing as BP, or plan target180 from the firmware's nominal 3 mmHg/s rate.
- Raw-voltage base: retained 80 bpm exports at 100/65, 120/80 and 150/100
  contain a 1.328 Hz component even when `smooth_v` peak cadence fails. This
  supports a signal-processing diagnosis only; the BP feature bands/offsets
  remain unvalidated.

### 8.6 Tests Required

`test_beat_analysis.py` checks regular synthetic beats, wrong-cadence candidate
suppression and measured-rate overflow projection. Separately run all retained
exports through the CLI and inspect cadence status and target170/180/190 budgets.
No Keil build or pneumatic test is required for this host-only tool.
The raw-voltage tests additionally require regular 80 bpm with injected 5 Hz
valve frequency to pass, wrong cadence and valve-only signals to avoid positive
classification, an empty 40-120 mmHg span to report insufficient samples, and
irregular MCU ticks to refuse cadence inference. Re-run complete strict exports
from all labeled reference conditions; this regression never writes the board.
For label-free pulse estimation, assert correct results on synthetic 60/80/100
BPM with 5 Hz contamination, no `pulse_bpm` for valve-only, low-noise,
changing-rate, irregular-tick and out-of-range-pressure inputs, plus CLI use
without `--bpm`. Compare all16 retained strict exports with their separately
recorded 80 BPM labels only after estimation; do not feed the labels to the
estimator. The later truncated 60 BPM physical-reference capture is an
exploratory cross-rate check; complete, controlled reference runs are still
needed before firmware adoption.

### 8.7 Wrong vs Correct

```text
Wrong: target 180 is within the pressure limit, so the 2800-point capture fits.
Correct: project from observed rate and sample count; all four 150/100 rounds exceed 2800 at 180.

Wrong: smooth_v peaks are 1.5-2 s apart, so an 80 bpm simulator pulse was absent.
Correct: inspect the original v waveform in a declared pressure window; 800 ms
         smoothing can merge 750 ms beats, and first-window FFT can choose a
         different frequency from later windows.
```

## 9. User Defined reference settings and bounded rate probe

### 9.1 Scope / Trigger

Use this contract when a BP Pump 2 User Defined setting is compared with a
Standard BP preset or a prior physical capture. The BP Pump 2 Operators Manual
sections 2-5 and 3-15 list User Defined editing and Standard BP Table 3-2.

### 9.2 Signatures

`python tmp/linkpad_lowpressure_check.py --rate-probe` is a single non-human
target150 host probe. The existing `--standard` mode still waits for a full
natural capture. The probe emits `test.rate_probe_result` only on its planned
110 mmHg endpoint.
`python tmp/linkpad_lowpressure_check.py --low-band-probe` is a separate
single-run lower-pressure probe; it records the same result type with
`targetMmHg=120` and `endpointMmHg=45`.
`python tmp/linkpad_lowpressure_check.py --high-band-probe` is a separate
single-run non-human upper-pressure probe; its result has `targetMmHg=180`
and `endpointMmHg=125` but no calculated BP result.
`python tmp/linkpad_lowpressure_check.py --user-defined` uses the existing
bounded target150 full-capture path while labeling the log as User Defined.
It reports `test.result.userDefinedCaptureComplete` separately from `bpValid`.
`python tmp/linkpad_lowpressure_check.py --user-defined-180` is one non-human
target180 full-capture attempt with its own 190 mmHg host ceiling and 82-second
natural-completion deadline. It retains the same result/closeout distinction.

### 9.3 Contracts

- Standard BP #2 is 150/100 mmHg, 80 BPM, 0.65 cc; #1 is 120/80,
  80 BPM, 0.68 cc; #7 is 100/65, 80 BPM, 0.69 cc. These preset volumes are
  group-specific. User Defined has nine editable groups; Sys20-250,
  Dia10-200 mmHg, pulse volume0.1-2.4 cc in0.1 cc steps, HR30-250 BPM.
  The manual also says pulse volume and HR are interdependent. Its 0.70 cc
  screen is an example, not a universal default. Record mode, group number,
  pressure, HR, pulse volume and cuff selection at acquisition; unknown
  fields remain unknown. Do not import a historical1.5 cc bench setting.
- `--rate-probe` keeps the existing calibrated fresh-zero, ADS, safe-pin,
  pressure-ceiling and stream-freshness gates. It inflates once to150 mmHg,
  observes deflation until a fresh reading <=110 mmHg or45 seconds,
  then uses the existing stop -> vent -> fresh low -> seal closeout and
  restores target50. Its endpoint is intentionally incomplete (`calc=0`).
- `--low-band-probe` keeps the same gates, inflates once to120 mmHg, uses a
  host pressure ceiling135 mmHg, and observes until fresh pressure <=45
  mmHg or55 seconds. Natural-completion messages cannot extend the time
  limit. It always uses the same closeout and target50 restoration. At40Hz,
  a55-second acquisition would remain below3300 capture slots; a failed
  pressure, freshness, ADS or GPIO gate still aborts early.
- `--high-band-probe` keeps the calibrated fresh-zero, ADS, safe-pin,
  freshness and firmware-safety gates. It inflates once to180 mmHg, uses a
  host pressure ceiling190 mmHg and35-second total deadline, and stops at
  fresh pressure <=125 mmHg. Accept only first deflation pressure>=150,
  at least20 deflation samples, >=8 s duration and endpoint>=115 mmHg.
  Always stop -> vent -> fresh low -> seal, then restore target50. It is an
  intentionally incomplete `calc=0` capture, not a BP result.
- `--user-defined` retains the target150, host ceiling165 mmHg and75-second
  acquisition cap of `--standard`; it requires natural deflation completion,
  zero dropped samples and a completed calculation, but accepts `bpValid=false`
  as a complete raw capture. This never turns an invalid BP into a reportable
  result. Export's `calc=3` means calculation completed and BP failed.
- `--user-defined-180` uses the same preflight, fault/freshness checks and
  single-run closeout, but targets180 mmHg, aborts at observed pressure190 mmHg,
  and requires natural completion within82 seconds from `start`. On every exit,
  stop -> vent -> fresh low pressure -> seal and restore `target 50`; check
  fresh samples again after seal before export. A naturally complete invalid
  BP is raw capture evidence only. Do not repeat inflation just to make the
  firmware validity flag pass. The sampled host abort does not guarantee an
  absolute peak below190 mmHg between samples; firmware protection remains
  independent. Do not use target190 until the connected pneumatic ratings
  and capture-budget margin are verified.

### 9.4 Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Unsafe preflight, stale stream, pressure >=165 mmHg | Abort and close out; no successful rate record |
| Deflation <=110 mmHg after >=8 s, starting >=120 mmHg | Emit rate evidence and close out |
| No endpoint by45 s, unexpected pressure trajectory | Abort and close out |
| Low-band probe reaches <=45 mmHg from >=90 mmHg after >=8 s | Emit rate evidence and close out |
| Low-band probe exceeds135 mmHg or does not reach45 mmHg by55 s | Abort and close out |
| High-band probe reaches190 mmHg, does not reach125 mmHg by35 s, or has an unexpected trajectory | Abort and close out; no successful high-band record |
| User Defined natural capture complete, BP invalid | Preserve full capture; report complete acquisition and `bpValid=false` |
| User Defined deflation still active at75 s | Stop/vent/seal; mark acquisition incomplete |
| User Defined 180 reaches190 mmHg, times out at82 s or loses fresh samples | Abort, close out and restore target50; no complete-capture claim |
| Post-seal pressure >1 mmHg | Reject export; vent -> fresh zero -> seal before retry |

### 9.5 Good / Base / Bad Cases

- Good: user-verified User Defined group, short probe, sealed fresh zero,
  retained raw capture, pressure-band-matched comparison.
- Base: 60 BPM / 2.0 cc truncated capture and 60/80 BPM / 0.7 cc short
  probes; compare only their common130-110 mmHg band, not a complete BP
  result. One run per setting cannot establish a causal rate effect.
- Low-band base: target120 / 80 BPM / 0.7 cc captures roughly100-45 mmHg
  before deliberate stop. Its low-pressure slopes cannot turn a different
  target150 acquisition into a verified full-duration capacity bound.
- High-band base: target180 / User Defined 150/100, 80 BPM, 0.7 cc,
  External Cuff captured164.77-125.10 mmHg in739 points/dropped0.
  Original voltage has six consecutive ~80 BPM peaks at164.0-158.5 mmHg
  before the first large valve-phase step. The pulse onset above164.77 is
  unobserved and the partial capture has no SBP/DBP result.
- Full User Defined base: target150 / 80 BPM / 0.7 cc yielded2185 points,
  dropped0, with `calc=3`. Strict export and production C replay agree on
  invalid BP, while a separate raw-voltage diagnostic estimates80 BPM.
- Bad: treat Standard BP #2's0.65 cc as the editable User Defined value or
  assert old80 BPM captures used1.5 cc without an acquisition record.

### 9.6 Tests Required

Run `python -m unittest tmp/test_linkpad_calc_stop.py -v` and compile the
host script with `py_compile`. Assert both the 110 mmHg success route and
45-second timeout, plus the low-band 45 mmHg success route and55-second
timeout, plus high-band 125 mmHg success,35-second timeout and190 mmHg
ceiling routes; issue stop/vent/seal and restore target50. Strictly decode each
exported raw capture; do not treat `calc=0` as a BP replay result.
Assert `--user-defined` accepts a naturally complete, invalid-BP capture
without relabeling it Standard BP or changing the invalid result. An early
or timed-out run still closes out and cannot report complete acquisition.
For `--user-defined-180`, test natural completion, 82-second timeout and
190 mmHg boundary abort with the same closeout and target restoration.

### 9.7 Wrong vs Correct

```text
Wrong: Set every 150/100 comparison to 1.5 cc because an older bench run used it.
Correct: Read and record the active mode/group/volume; change only the intended
         variable, and stop a slow probe before the capture budget is threatened.

Wrong: The User Defined raw capture completed, so its invalid BP candidates are measurements.
Correct: Preserve the verified waveform; report `calc=3` and keep BP invalid.
```

## 10. Offline height/area oscillogram study (2026-10-28)

### 10.1 Scope / Trigger

`tools/bp_oscillogram_study.py` explores whether complete exported voltage
contains a usable pulse-by-pulse oscillogram when production `smooth_v` yields
invalid or unstable BP features. It is host-only research, never a firmware
algorithm, clinical BP result, simulator-fault diagnosis or inflation command.
Height/area feature ideas come from DOI:10.3389/fphys.2025.1611096, whose
250 Hz patient/reference model is not reproduced by this 40 Hz study.

### 10.2 Signature

```powershell
python 'blood pressure monitor/tools/bp_oscillogram_study.py' `
  tmp/capture_export_20261028-212208.verified.ndjson
python 'blood pressure monitor/tools/bp_oscillogram_study.py' `
  tmp/capture_export_20261028-212208.verified.ndjson --step-padding-samples 20
```

Python API: `analyze(capture, step_padding_samples=40, upper_pressure=130)
-> dict`. The capture comes from `bp_capture.decode()`, and padding is an
integer in `0..80`. For a high-target complete capture, add
`--upper-pressure 170`. Only 130 and 170 are accepted; the default preserves
earlier 130 mmHg study results.

### 10.3 Contracts

- Require completed `calc=2/3`, exact 25 ms ticks through the reused
  label-free `estimate_pulse()` gate and dominant frequency in 0.9-2.5 Hz.
  Neither reference BPM nor SBP/DBP settings are inputs.
- Bandpass original exported `v`, detect positive peaks and neighboring
  troughs, and compute baseline-relative pulse height and positive area.
  Reject beats within `step_padding_samples` of any >=5 mmHg adjacent
  reported-pressure step. Bin retained beats at 5 mmHg from 50 to
  `<upper_pressure` (default130, optional170);
  require at least two beats in each occupied bin and eight occupied bins.
- Fit a robust Gaussian independently to height and area bin medians. A
  diagnostic height candidate needs at least two occupied bins on each side,
  >=10 mmHg observed span from peak to each end, endpoint amplitudes <80%
  of peak, fit R2 >=0.7, no fitted upper-bound hit, and bin/fit peaks within
  7.5 mmHg. The area feature is a cross-check, not a second voting BP model.
- JSON emits `status`, label-free `pulse`, beat/step counts and each feature's
  bins, bin peak, Gaussian peak/R2, tail ratios and occupied side-bin counts.
  A `diagnostic_only` status permits discussion of a MAP *candidate* only;
  it never authorizes compensated SBP/DBP, firmware thresholds or clinical use.
- For curves with at least eight occupied bins, `robustness` reports
  `peak_bin_beats`, `max_occupied_gap_mmhg`,
  `jackknife_fit_range_mmhg` and `jackknife_max_shift_mmhg`. The jackknife
  deletes each occupied pressure bin once and refits the same Gaussian;
  its shift is relative to the full-curve fitted center. An exploratory
  independent screen rejects peak support <3 beats, an adjacent occupied-bin
  gap >15 mmHg, or a maximum center shift >7.5 mmHg. `reasons` lists
  `weak_peak_support`, `pressure_coverage_gap` and/or
  `jackknife_unstable`. These are conservative research thresholds based on
  5 mmHg binning and the existing 7.5 mmHg peak-spread check, not reference-
  validated limits. `robustness.screen=pass` does not override
  `status=incomplete_oscillogram` or `unstable_peak`, and neither field is
  permission to report BP. A curve with fewer than eight bins retains
  `insufficient_bins` and the bin list, with no fitted robustness screen.

### 10.4 Validation & Error Matrix

| Input | Behavior |
| --- | --- |
| Invalid checksum/order/schema | Strict decoder fails before analysis |
| `calc=0/4`, unreliable pulse or dominant frequency outside study band | No MAP candidate |
| Fewer than 20 clean beats or eight occupied bins | Insufficient-data status |
| Missing high/low tail or endpoint >=80% of peak | `incomplete_oscillogram` |
| Weak fit, bound hit or bin/fit difference >7.5 mmHg | `unstable_peak` |
| Peak bin <3 beats, occupied gap >15 mmHg, or jackknife shift >7.5 mmHg | `robustness.screen=reject` with specific reason; existing `status` unchanged |
| Padding outside 0..80 samples | `ValueError` |
| Upper pressure other than130 or170 | `ValueError` |

### 10.5 Good / Base / Bad Cases

- Good: synthetic 75 and 115 mmHg pulse-amplitude peaks remain separated
  under 5 Hz valve noise and a pressure impulse, with no label input.
- Base: retained 120/80 and 100/65 captures yield distinct height-curve
  groups; several 150/100 rounds have incomplete upper-side evidence.
- Bad: `212208` can fit ~117 mmHg at short step padding but reaches the
  130 mmHg fit bound at 40 samples. Do not select the padding that matches
  the BP Pump 2 label and call this a recovered MAP.
- High-target diagnostic: the verified `223729` full capture has a height-bin
  maximum at127.5 mmHg and fits123.23 mmHg with40-sample step padding. Fits
  across0/20/40/60 padding are124.41/123.40/123.23/124.99 mmHg, with both
  tails below80% of the peak. This is a stable MAP candidate, not an SBP/DBP
  result or permission to replace the firmware's fixed MAP window. Its peak
  bin has only two retained beats; a three-beat minimum leaves only six
  occupied bins. In the earlier high-target `170426` Standard150/100 capture,
  the strongest bin is142.5 mmHg while the fit is117-124 mmHg over padding
  0/20/40/60; all are `unstable_peak`, and40-sample step exclusion leaves
  a40 mmHg internal bin gap. Future offline MAP quality checks must report
  peak beat support, internal pressure gaps and leave-one-bin-out sensitivity
  before considering a production selection rule.
- Prospective non-human check on2026-10-29: three User Defined150/100,
  80BPM,0.7cc, target180 captures passed `diagnostic_only` plus robustness
  pass with fitted centers118.26/119.26/119.88mmHg. A separately locked
  User Defined100/65,80BPM,0.7cc, target150 series passed only2/3 at
  40-sample step padding: its middle capture had six >=5mmHg pressure
  steps, only24 clean beats and six occupied bins. That result fails the
  prespecified low-condition repeatability gate, so the conditional
  six-capture nonoverlap test is not a validated result. At padding0 the
  middle capture has13 bins and fits77.39mmHg, but this post hoc setting
  does not change the locked2/3 decision. Keep both the failure and raw
  capture. Phase association of all six pressure steps with the200ms
  valve schedule guides diagnosis; it does not identify the physical
  cause without a simultaneous independent pressure trace. Neither
  prospective pilot establishes true MAP or authorizes firmware BP tuning.

### 10.6 Tests Required

Run `python -m unittest discover -s 'blood pressure monitor/test' -p 'test_*.py'`.
`test_oscillogram_study.py` must verify distinct unlabeled synthetic MAP
peaks, valve-only rejection, missing-upper-tail rejection and `calc=0`
rejection. It also verifies the 170 mmHg upper-bound path and rejects other
upper bounds. On retained captures, compare height/area fits and padding
0/10/20/30/40/60 without using panel labels to select parameters. No Keil
build or board operation is required for host-only changes.
Check synthetic sparse-peak and coverage-gap cases, plus a fully supported
curve, and a compact verified high-target bin shape that triggers jackknife
instability. Inspect the independent screen on retained high-target captures.

### 10.7 Wrong vs Correct

```text
Wrong: One padding choice fits the nominal 150/100 MAP, so publish the BP result.
Correct: Report the full padding sensitivity and incomplete high-side coverage;
         keep the firmware BP invalid and retain the original waveform.
```

## 11. Low-pressure tail and development capture decision (2026-11-01)

- Preserve every bp.capture/3 sample and the original bridge NDJSON, including the low-pressure tail. Declare the offline envelope pressure/sample window and beat-exclusion rule before comparing conditions; report both endpoint coverage and excluded-tail behavior. A weak tail alone does not invalidate an otherwise complete development capture.
- Record fresh raw/sensor/estimated zero before and after each run, vent -> consecutive fresh near-zero samples -> seal, safe pins and ADS/UART counters. The displayed estimate may hide a sealed raw rebound near zero. Such a rebound is a quality annotation and a reason to seek independent pressure evidence, not proof of a pneumatic or electrical cause.
- The 2026-11-01 Standard120/80 repeat validated 2289 samples at exact25ms ticks, no drops, and bit-equal production-C replay. Firmware reported56 BPM while the label-free 40..120mmHg offline cadence estimate was80 BPM. Treat transport integrity, pulse/envelope quality and simulator-label agreement as separate gates; valid=1 and replay equality do not validate BP accuracy.

## 12. Current-panel host capture gate (2026-11-01)

### Scope / Trigger

The development-only EK bridge runner requires fresh operator confirmation for each non-human Standard120/80 capture. The 0.68 cc panel value was recorded for the 2026-11-01 12:04 and 15:20 rounds; the two earlier rounds have unknown pulse volume and cannot be relabeled after capture.

### Signature and contracts

Run python tmp/bp_standard_capture_20261101.py --confirm-nonhuman-fixture --confirm-current-panel --panel-pulse-volume-cc 0.68 for the confirmed configuration. Optional --panel-photo PATH records an existing photo file. Missing confirmation, nonpositive/nonfinite pulse volume, or nonexistent photo exits before connecting to the EK bridge or writing serial commands. Metadata records the supplied panel value and evidence path; no photo leaves a specific missing-value reason.

The existing target150, host ceiling165mmHg, 2-second pressure freshness, 75-second activity deadline, vent/fresh-zero/seal closeout and target50 restoration remain in force. This is a host script change, not a firmware or calibration change. Preserve original NDJSON, verified MCU records and ticks. Earlier runs with unknown panel pulse volume cannot be treated as locked-volume repeats.

### Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| Confirmation or valid volume absent | Argument error before device connection |
| Unsafe IDLE/pins/calibration/ADS/UART/zero preflight | No start command |
| Pressure limit, stale sample, timeout or sensor fault | Stop attempt, bounded vent/fresh-zero/seal closeout; retain failed raw log |
| Complete transfer with weak peak support | Keep development waveform, reject validated envelope/MAP claim |

### Good / Base / Bad Cases

- Good: current fixture and panel confirmed, 0.68 cc recorded, exact25ms ticks, safe closeout and complete export.
- Base: complete export and 80 BPM in the long offline window, but only two clean beats in the peak pressure bin; retain raw development data and fail the prespecified robustness screen.
- Bad: infer the unknown panel pulse volume of earlier runs from this one or present firmware 56 BPM as the physical simulator rate.

### Tests Required

Syntax-check the runner, verify missing confirmations exit before bridge connection, check saved per-run metadata and SHA256, strict-decode the transfer, replay production C, and run the host suite. The 12:04 round passed these gates, with 2273 samples, no drops, exact25ms ticks, equal replay bits, and 114 host tests; its peak-support screen still rejected both height and area oscillograms.

### Wrong vs Correct

Wrong: the latest 0.68 cc panel reading fills the missing metadata of two earlier captures.
Correct: keep their pulse-volume fields unknown and compare only what each original run documented.

## 13. Read-only multiwindow pulse study (2026-11-01)

### Scope / Trigger

Use this host-only diagnostic when a complete capture has a plausible raw pulse cadence but the production first-256-point FFT chooses a different frequency bin. It does not change firmware, report clinical pulse, or validate BP accuracy.

### Signature

Run python 'blood pressure monitor/tools/bp_multiwindow_pulse.py' CAPTURE... --output REPORT.json. Each input must be one complete strict-decodable transfer. The CLI performs no serial or actuator I/O. analyze_capture(capture, stride=128) also accepts stride=256; other strides raise ValueError.

### Contracts

Require exact 25ms MCU ticks. A 256-point window is eligible only when all pressures lie in 40..120mmHg, after the first80 and before the final15 points. Apply linear detrending, Hann and the production 0.9..4Hz maximum-bin shape. Require the firmware 0.0008 magnitude/3-times-band-noise gate plus an exploratory 0.001V detrended RMS floor. Detrended RMS is not the same statistic as the existing long-window bandpass RMS. At least three passing windows and >=70% modal-bin support produce a rounded-bin candidate; otherwise return no candidate. Save every window and source SHA256. The 128-point stride overlaps; its votes are not independent beats.

### Validation & Error Matrix

| Input | Behavior |
| --- | --- |
| Invalid checksum/order or incomplete export | Strict decoder fails before analysis |
| Irregular MCU ticks | irregular_sampling, no candidate |
| Inadequate 40..120mmHg span, weak voltage or valve-only 5Hz | No candidate |
| Adjacent FFT bins split below 70% support | no_consensus, no candidate |

### Good / Base / Bad Cases

- Good: synthetic 60/80/100BPM signals with a disturbed first window retain a matching later-window diagnostic candidate.
- Base: current three Standard120/80 captures have first-window75/56/56BPM, nonoverlapping candidates75/84/75BPM and existing long-window80BPM. The overlapping 128-point rule abstains on all three.
- Bad: infer 1BPM precision or external accuracy from agreement within one 256-point FFT bin (9.375BPM), or tune a gate until the simulator label is selected.

### Tests Required

Run test_multiwindow_pulse.py for varied synthetic rates, half-bin firmware rounding, irregular ticks, insufficient pressure coverage, valve-only and very weak coherent signals. Run the full host suite and strictly decode every studied file. The 2026-11-01 study used 42 unique historical plus three current captures; 256-point stride returned candidates for34/45 and 128-point stride for5/45. All available candidates agreed with the same-source long-window diagnostic within one bin; this is not reference validation. Full host suite:119 tests passed.

### Wrong vs Correct

Wrong: replace the firmware first-window FFT with a 70%-vote rule because it matched the same-sensor offline estimate on selected records.
Correct: retain the study as diagnostic evidence, report abstentions and bin resolution, then validate a frozen candidate against varied rates with independent reference labels before firmware change.

## 14. Offline envelope bin-width candidate (2026-11-01)

### Scope / Trigger

Use this contract when comparing pressure-bin support in complete non-human oscillometric captures. The 10 mmHg width was selected after inspecting four 2026-11-01 development runs; those runs and the 42 historical captures are not an independent validation set. BP Pump 2 Standard BP displays preset parameters, not a live pressure reference. Pressure Source and Pressure Gauge are separate static test modes.

### Signatures

Run `python 'blood pressure monitor/tools/bp_oscillogram_study.py' CAPTURE... --upper-pressure {130,170} --bin-width {5,10}`. `analyze(capture, step_padding_samples=40, upper_pressure=130, bin_width_mmhg=5)` keeps the old 5 mmHg default. Invalid widths raise `ValueError`; the CLI rejects them before analysis. No serial or actuator I/O occurs.

### Contracts

Strictly decode each complete capture and use MCU ticks for timing. Preserve the original voltage and pressure points. The selected width determines left-closed, right-open bins beginning at 50 mmHg; all other beat extraction and robustness rules remain as implemented. Record `bin_width_mmhg`, search upper bound, source hash and all rejection reasons with every result. For the next independent batch, report 10 mmHg as the frozen candidate and 5 mmHg as the baseline sensitivity result, irrespective of which looks better. A diagnostic peak is neither reference MAP nor validated SBP/DBP.

### Validation & Error Matrix

| Input | Behavior |
| --- | --- |
| Invalid checksum/order or incomplete transfer | Strict decoder rejects before oscillogram analysis |
| Width outside 5 or 10 mmHg | CLI rejection or `ValueError` |
| Insufficient beats, coverage, fit or jackknife stability | Return abstention/rejection reasons and retain raw data |
| Missing panel or independent dynamic-pressure evidence | Keep development role; do not claim reference accuracy |

### Good / Base / Bad Cases

- Good: run both declared widths on every new capture and preserve passing and failing outcomes.
- Base: 2026-11-01 four known-panel development captures change from 0/4 to 4/4 joint height/area screens when widened from 5 to 10 mmHg; the 42 historical development captures change from 8/42 to 10/42. This is rule selection, not external validation.
- Bad: relabel old runs as independently validated because the post hoc 10 mmHg width passes, or use the Standard BP preset screen as a live pressure reading.

### Tests Required

Run `test_oscillogram_study.py`: default and explicit 5 mmHg analyses must match, explicit 10 mmHg must be recorded even for abstentions, and invalid widths must fail. Run the full host suite, regenerate the audit with `bp_bin_width_audit.py`, and verify source paths/hashes and group counts in `data/reports/offline_bin_width_20261101.json`. No Keil build/download is required for this host-only tool change.

### Wrong vs Correct

Wrong: choose the width that makes a seen run pass and call its fitted peak a BP Pump 2 reference MAP.
Correct: label the 10 mmHg rule as a post hoc candidate, freeze it before new independent captures, report the 5 mmHg baseline too, and obtain a separate synchronized pressure reference for accuracy claims.

## 15. Preset 3 high-pressure development boundary (2026-11-01)

- The non-human Standard BP / Preset 3 / External Cuff 200/150, 80 BPM,
  0.60 cc round exported 2289 complete samples with no drops and exact 25 ms
  MCU intervals. Strict decode and production-C host replay matched envelope
  and feature bits. This verifies transfer and same-source reproducibility only.
- Firmware reported 190/77 mmHg, 75 BPM and valid=1. The separate 40..120
  mmHg cadence diagnostic estimated about 80 BPM. The reported DBP differs
  substantially from the panel setting; valid=1 is not a BP accuracy gate.
- Production C restricts its MAP search to 80..100 mmHg. In this round the
  selected smooth envelope was 0.008690 V at 89.128 mmHg, giving a 60% DBP
  threshold of 0.005214 V and a three-point crossing at 82.383 mmHg. The
  fixed -5 mmHg compensation yields the reported DBP 77. The 160..170 mmHg
  segment reaches 0.012592 V, so the fixed MAP window is a plausible source
  of mismatch for this preset; no single same-source round establishes a
  replacement window or reference BP.
- The previously fixed 170 mmHg search upper bound was chosen for a 150/100
  setting. At 200/150, the 5 mmHg height fit hit this bound with two clean
  beats in the highest bin; the 10 mmHg height fit also hit the bound and
  failed jackknife stability. Keep this capture in development and report
  both failed screens. Any wider bound for Preset 3 must be declared before
  a new independent batch; do not reclassify this seen round as passing.
- The BP Pump 2 Standard BP preset is a setting, not synchronized independent
  pressure evidence. A clinical or simulator accuracy claim needs a separate
  synchronized reference and an independently evaluated batch.
- A read-only, post hoc extension of the beat listing found 3, 4 and 3 clean
  beats in 170..180, 180..190 and 190..200 mmHg, respectively, but none in
  200..210 mmHg under the existing extraction rules. The height medians rise
  again in 180..190 after falling in 170..180; this single capture does not
  establish a stable high-pressure tail or justify changing the frozen screen.

## 16. Development-only offline envelope abstention (2026-11-01)

- `tools/bp_envelope_gate.py` reads the retained development manifest, verifies
  each complete capture's SHA256, strictly decodes it, and calls the existing
  `bp_oscillogram_study.analyze()` for both 5 and 10 mmHg bins. Incomplete
  attempts abstain without decoding. The gate never estimates SBP/DBP.
- A run is an `analyzable_candidate` only if height and area both return
  `diagnostic_only` with `robustness.screen=pass`. Missing features, incomplete
  tails, unstable fits or rejected robustness cause explicit `abstain` reasons.
  All development rows retain `bp_output_allowed=false` and null BP estimate.
- The existing 130/170 mmHg study bounds apply to 120/80 and 150/100. For
  200/150, the 170 mmHg bound is diagnostic only and adds
  `upper_bound_not_declared_for_preset3` even if another check happens to pass.
  The 10 mmHg rule was selected using four of these runs, so their candidate
  decisions are not independent validation. Preserve the 5 mmHg baseline.
- This read-only gate is separate from firmware `valid`; deploying an on-device
  abstention rule requires a separate design, host-C tests, Keil/RAM gates and
  non-human verification. No calibration or actuator behavior changes here.

## 17. Multi-setting feature readiness (2026-11-01)

- `tools/bp_multisetting_study.py` joins the retained development manifest and
  envelope gate using their hashes and run IDs, and reuses strict decode plus
  the existing 10 mmHg height/area study for gated candidates. Preserve failed
  attempts and null features for abstentions.
- Current 120/80, 150/100 and 200/150 settings yield 4, 1 and 0 candidates.
  Two of the 120/80 runs lack recorded pulse volume; the third and fourth
  record 0.68 cc. The fourth has a complete 2369-point export and passes the
  10 mmHg development envelope gate, but its post-capture sealed-zero raw
  remains about 11..16 counts above its pre-capture sealed-zero range even
  after a second vent/fresh-zero/seal. Cross-run zero comparability is unresolved.
  The sole 150/100 run records 0.65 cc, while 200/150 has no qualified
  high-pressure envelope. The two known-volume 120/80 candidates cannot yet
  establish trustworthy same-condition repeatability because of zero drift.
- Do not infer a multi-setting SBP/DBP correction from these data. Report
  feature peaks as development diagnostics; require prospectively fixed panel,
  volume, pneumatic and quality rules, sufficient same-condition repeats, and
  a separate untouched evaluation batch before adopting a candidate formula.
  Static Pressure calibration remains a separate completed measurement.

## 18. Post-capture sealed-zero recovery evidence (2026-11-01)

- In a later pump-off PC1 repeat, two open segments averaged raw
  1407.283/1406.305, followed by sealed 1337.975/1335.430. The final
  30-second sealed read-only mean was 1337.288 versus a 1342.870
  pre-switch baseline. Repeated valve-state association and a safe final
  pin readback still do not identify pressure versus electrical cause.
  Keep inflation and model fitting blocked pending independent zero evidence.
  See `data/reports/valve2_zero_repeat_20261101-154528.md`.

- Preserve raw ADS counts across pre-capture sealed, post-capture sealed,
  vent/fresh-zero/seal and later read-only windows. Compare window means and
  within-window drift; a clipped `est=0.0` is not a physical zero certificate.
- The Preset 1 round first shifted from raw mean 1342.405 to 1395.725 after
  capture, then 1353.785 after a second vent/seal. Two later 30-second
  read-only windows averaged 1344.810 and 1343.020. Recovery toward the
  pre-capture mean does not distinguish residual pneumatic pressure from
  electrical or mechanical sensor-chain drift. The read-only windows did not
  independently re-read actuator pins.
- Keep same-volume development candidates separate from verified
  same-condition repeatability until zero state and safety state are
  independently documented. Do not change static calibration or fit BP
  coefficients to force agreement. The source hashes and limitations are in
  `data/reports/preset1_zero_recovery_20261101.md`.

## 19. Shared offline envelope and bin-origin stability (2026-11-05)

### Scope / Trigger

Use for `bp_standard_adaptive.py` and `bp_standard_diagnostics.py`. This is
development sensitivity analysis, separate from the deployed C algorithm and
independent BP accuracy validation. Do not silently replace old reports.

### Signatures

- `bp_standard_envelope.extract(capture)` -> extraction status/reason, beats,
  raw diagnostics and rejection counts.
- `bin_beats(beats, origin=0.0)`, `summarize_bins(rows)` and
  `assess_stability(beats)` own unrounded height/area features and gates.
- Adaptive output schemas are `bp.standard_adaptive/3` and
  `bp.standard_adaptive_capture/3`; diagnostics schemas increment to `/2`.

### Contracts

- Strictly decode complete captures first. Inference reads only calc state,
  float32 raw voltage/pressure and MCU ticks. Settings, preset labels, header BP
  results and exported firmware envelopes must not influence inference.
- Require calc2/3, >=800 points, exact25ms intervals. Select the longest
  contiguous eligible interval after80/before15 samples and20..300mmHg.
  Require >=600 samples and >=50mmHg span inside that single interval; never
  concatenate separated windows for Welch. Report discarded eligible samples.
- Every accepted trough-bracketed beat must lie wholly within the selected
  interval. Preserve >=5mmHg step exclusion with40-sample padding.
- Both callers consume the same unrounded extraction, median bins and envelope
  summaries. Round only for presentation. Diagnostics expose extraction errors,
  baseline errors, all occupied bins and origin sensitivity rather than inventing
  plausible features from an invalid capture.
- Fixed10mmHg bin origins0/2.5/5/7.5 must all pass support/gap/tail/height-area
  gates. All height/area peak centers together must span <=15mmHg. A comparable
  local peak >=90% of the main peak and >=30mmHg away causes ambiguity rejection.
  These thresholds are development rules, not validated measurement error limits.
- All outputs retain null SBP/DBP and `bp_output_allowed=false`. On sensitivity
  rejection, the primary peak is null; retain baseline peak and origin reasons
  as descriptive evidence, not a validated MAP or confidence interval.

### Validation & Error Matrix

- Incomplete calculation / non25ms ticks -> explicit extraction abstention.
- No sufficiently long contiguous pressure interval ->
  `fragmented_pressure_window`; weak signal/cadence retain their own reasons.
- Inadequate peak support/tails or competing peak -> baseline abstention.
- Any origin fails -> `bin_origin_gate_failed`; otherwise peak span>15 ->
  `bin_origin_peak_unstable`.
- Old firmware identity or valid1 is not evidence of BP accuracy; this offline
  change neither repairs the C80..100 MAP window nor its fixed-10/-5 offsets.

### Good / Base / Bad Cases

- Good: target275 baseline215 but origin peak range212.5..230 -> abstain,
  retain all variants and record that17.5mmHg is sensitivity, not true error.
- Base: late20mmHg boundary reentries are discarded; use the longest valid
  contiguous segment and report the discarded count.
- Bad: choose the bin origin closest to the panel label, concatenate separated
  windows, or call a same-source peak agreement independent accuracy validation.

### Tests Required

Run `python -m unittest discover -s "blood pressure monitor/test" -p "test_*.py"`.
Assert invalid diagnostics, fragmented-window rejection, edge reentry selection,
valve-step exclusion, competing peaks, label/firmware-envelope independence,
shared unrounded diagnostics, and target275 real-data sensitivity rejection.
Retain synthetic pressure/cadence range and low-tail abstention tests. These
tests do not prove clinical or simulator BP accuracy.

### Wrong vs Correct

Wrong: flash a global-maximum/ratio replacement because one default bin gave215.
Correct: retain all13 attempts in the20261105 stability manifest, report5 of8
complete captures as candidates and all3 high-setting abstentions, and withhold
deployment until frozen independent multi-setting evidence exists.

## 20. Peak instability localization (2026-11-05)

### Scope / Trigger

Use `tools/bp_peak_instability.py` to explain sensitivity of a shared offline
envelope, without changing extraction, gates, calibration or deployed firmware.
This diagnoses a numerical mechanism; physical disturbance sources need separate
evidence. Reports retain all13 attempts, including5 incomplete captures.

### Signatures

- `variants(beats)` -> four fixed origins, all bin members, shared summary,
  top-three smoothed bins and their actual0.25/0.5/0.25 contributors.
- `deletion_sensitivity(beats, baseline_variants)` -> every one-beat deletion,
  all four origin statuses/peaks/reasons, changed origins and outcome counts.
- `diagnose(capture)` -> extraction, fixed beats, variants, stability, descriptive
  local dips, deletions and valve observability; `bp_output_allowed=false`.
- `audit(manifest_path, root=ROOT)` -> `bp.peak_instability/1`, input/code hashes
  and environment. CLI accepts `--manifest` and `--output-prefix`.

### Contracts

- Reuse section19 features and gates unchanged. Top-two margin is
  `1 - second_smoothed / maximum_smoothed`; adjacent bins are allowed. This is
  a descriptive margin, not another acceptance gate or independent peak count.
- Delete each fixed extracted beat in turn, rebin and summarize all origins.
  Do not re-extract, cherry-pick deletions or call this independent repeatability,
  a statistical jackknife interval, true BP error or a corrected measurement.
  `peak_changed_trials` counts deletions changing height or area at any origin,
  even when a perturbed origin fails support/tail gates.
- Local amplitude dips compare time-ordered neighboring accepted beats inside
  baseline peak +/-30mmHg; do not reject them as proven artifacts.
- Check raw, metadata and verified SHA256 before strict decode. Preserve failed
  attempts; do not decode an incomplete capture into a plausible envelope.
- Schema1/2/3 valve evidence lacks a complete pulse-event clock:
  `phase_alignment_possible=false`. Schema4 permits alignment only with a
  complete nonempty trace (section21). Never infer valve phase from `tick%200`.
  Zero >=5mmHg steps does not exclude smaller valve effects. Same-source
  waveforms cannot establish dynamic accuracy.
- Outputs stay under `data/reports`, cannot collide with manifest/evidence,
  and cannot overwrite any existing report; use a fresh prefix to reproduce.

### Validation & Error Matrix

- Source hash mismatch / invalid capture -> explicit exception, no silent skip.
- Extraction abstention -> retain reason; no variants/deletion analysis.
- Deletion reduces peak support -> preserve `incomplete_or_weak_peak` and all
  other origin outcomes rather than retaining only passing subsets.
- Missing pulse timing -> unresolved physical cause, no phase-lock conclusion.
- Existing output -> CLI error before any report is written.

### Good / Base / Bad Cases

- Good: target275 has73 beats; height top-two margins0.36..2.49%, only3..4
  beats in leading bins; four-origin combined peaks212.5..230. Retain rejection.
- Base:11 of73 deletions change at least one origin's peak. Four deletions
  happen to pass stability; retain them alongside62 unstable and7 gate-failed
  outcomes. Do not substitute a passing deletion for the original record.
- Bad: attribute221.35mmHg/22.05mV dip to a specific valve pulse without timing,
  or interpret17.5mmHg sensitivity as calibrated pressure error.

### Tests Required

Run the full host/Python suite and `test_peak_instability.py`. Assert sharp versus
flat margins, reconstructable weighted bin contributions, a single-beat peak
shift retaining support failure, absent valve phase even with threshold traces,
invalid extraction, no mutation/inference changes, hash mismatch, output overwrite
rejection and retained target275 evidence. Visually inspect the scientific plot.

### Wrong vs Correct

Wrong: delete one of the four favorable beats and publish the resulting peak.
Correct: preserve all73 perturbations, keep original BP withheld, and plan
same-condition repeats with synchronized valve event logging before attributing
physical cause. A synchronized independent dynamic pressure trace is required
for a waveform accuracy claim.

## 21. Synchronous valve command trace (2026-11-05)

### Scope / Trigger

Schema4 records PC1 GPIO command edges on the sample HAL tick clock, enabling
command-phase alignment. This does not measure mechanical valve motion.

### Signatures

`BP_Algorithm_RecordValvePulse(uint32_t tick, uint8_t requested_width)` records
OPEN; `BP_Algorithm_RecordValveClose(uint32_t tick)` records actual CLOSE.
`BP_Algorithm_GetValveTiming()` returns count/errors/pending;
`BP_Algorithm_GetValvePulse(index, &open, &close)` reconstructs uint32 ticks.
`tools/bp_valve_phase_audit.py INPUT --lower 200 --upper 245` uses /4 exact edges.

### Contracts

- Store600 compact delta/width pairs (1200B), first absolute tick and metadata.
  Shared count/errors/pending/anchors are volatile. Append is O(1), no ISR log
  or allocation. uint32 wrap is supported; reset invalidates old entries.
- Start/cancel critical sections preserve the incoming interrupt mask. Cancel
  clears ownership before closing pending pulses; a late ISR cannot reseal vent.
- Order: begin, points, valve, steps, timing, pulses, features, end. Example:
  `{"schema":"bp.capture/4","type":"timing","n":25,"errors":0,"complete":1}`
  then indexed pulse rows with `i`, `open`, `close`. Timing/pulse rows enter FNV;
  export remains one line per task. Pending pulse rejects export start.
- Complete means errors=0, pending=0 and count=aggregate pulses. Strict decoder
  supports1..4, validates keys/order/count/wrap/width and aggregate consistency.
- Align by recorded GPIO edges; never infer phase from `tick%200`. ADC aperture,
  mechanical motion and independent dynamic pressure remain unmeasured.

### Validation & Error Matrix

| Condition | Behavior |
| --- | --- |
| More than600 entries | Sticky bit1; keep incomplete prefix |
| Open interval outside1..255ms | Sticky bit2; stop appending |
| Width outside0..255ms | Sticky bit4; stop appending |
| Duplicate/unmatched edge | Sticky bit8; stop appending |
| Pending CLOSE at export | Reject start |
| Corrupt/truncated/count-mismatched transfer | Decoder rejects |
| Missing/incomplete/empty timing | No exact phase claim |

### Good / Base / Bad Cases

Good: zero diagnostic exports200 points and25 complete5ms pulses. Base: early
cancellation records shorter actual width. Bad: declare a retained prefix complete
or call command-correlated pressure changes proven mechanical artifacts.

### Tests Required

Actual-C regression covers wrap, bounds, capacity, ordering, cancellation and
export; Python covers schema compatibility/corruption. Require Keil0/0,
>=2048B RAM headroom,4096B reserved stack, runtime watermark, verified download
and zero-pulse hardware check before inflation.

### Wrong vs Correct

Wrong: rewrite a capture firmware ID to allow replay with newer code.
Correct: replay each ID from matching production sources in `data/provenance/`.
