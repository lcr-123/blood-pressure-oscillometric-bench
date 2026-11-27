# Safety Rules

This firmware controls a real pump and valves. Treat safety behavior as part of every firmware change.

## Pressure Limits

- `BP_MAX_PRESSURE_MMHG` is the hard over-pressure protection threshold.
- `BP_INFLATE_TARGET_MMHG` should remain below the over-pressure limit.
- If pressure reading fails or returns an impossible value, the control logic should prefer stopping the pump and venting.

## Pump And Valve Defaults

- `MX_GPIO_Init()` and `BP_Control_Init()` must leave sealed idle state:
  PB8 HIGH, PC1 LOW, and PC8 HIGH.
- Inflation must close PC1 before opening PB8 and starting the pump on PC8.
- Deflation or emergency stop must set PC8 HIGH and PB8 HIGH before setting PC1 HIGH.
- Valve macros must not write PC8; only the pump API owns the relay output.
- `BP_Control_Stop()` must stop PWM, stop the pump, close the inflation valve, and open the deflation path long enough to release cuff pressure.
- Any new error path in measurement control should explicitly describe pump and valve state.

## Blocking Calls

- Short `HAL_Delay()` calls are already used during reset and pressure stabilization.
- Do not add long blocking WiFi, serial, or display work to the measurement path without confirming emergency stop and over-pressure checks still run.

## Calibration

- Pressure conversion constants in `ads1115.h` are hardware-dependent.
- Changes to divider ratio, sensor model, ADS1115 PGA range, or supply voltage require updating conversion logic and documenting the reason.
- The fitted MPXV5050GP covers 0-50 kPa (about 0-375 mmHg gauge). The active
  hardware calibration as of 2026-10-25 is `cal write 82.326 -19.887`
  (source: `calibration_data/manual_static_2026-10-25.json`); a full-chip erase clears it, so
  rewrite and read it back before any pressure test.
- Human testing still requires a successful full-range non-human run with the same
  cuff, tubing, power supply, target, and firmware image.

### Calibration Restore Contract

1. **Scope / Trigger**: applies after a Keil full-chip erase, or whenever `cal`
   reports `UNCAL` on the unchanged MPXV5050GP/divider hardware.
2. **Signatures**: write `cal write 82.326 -19.887`, then query `cal`.
3. **Contracts**: the write values come from
   `calibration_data/manual_static_2026-10-25.json`; the readback must report
   `VALID`, slope `82.326`, and intercept `-19.89` at the firmware's display
   precision before any pressure test. Host scripts that embed a restore command
   must use the same values. `88.300/-19.960` is rollback-only and
   `26.5/-70.6` belongs to the removed MPXV7007DP path.
4. **Validation / Error Matrix**: `UNCAL`, mismatched readback, changed sensor,
   divider, PGA, or supply -> do not inflate; re-establish the hardware-specific
   calibration instead of copying a historical value.
5. **Good / Base / Bad Cases**: good = full erase, exact write, matching `VALID`
   readback; base = calibration survived and already matches, so do not rewrite;
   bad = a legacy helper silently writes a rollback or old-sensor coefficient.
6. **Tests Required**: syntax-check restore helpers, search active scripts and
   current guidance for stale `cal write` literals, and perform target readback
   before the non-human pressure gate.
7. **Wrong vs Correct**: wrong = restore `88.3 -19.96` because an older test log
   used it; correct = follow the current calibration artifact and verify
   `82.326/-19.89` from the target.

## Medical Accuracy

This code is project firmware for development and bring-up. Do not present algorithm output as clinically validated without calibration, test data, and validation against a reference device.

## Nonblocking Fault State

- BP_Control_EmergencyStop() must stop the pump, close PB8, open PC1, latch a
  BP_Fault_t value, and return without HAL_Delay().
- Emergency vent remains open until BP_Control_Reset(), seal, or another explicit
  bench command changes it. Do not automatically seal a cuff after a fixed delay.
- Full-measurement sensor initialization/read failure, inflate timeout, and
  over-pressure all use the same emergency-stop path.
- Relay-only start/open must sample pressure independently of diagnostic streaming.
  They may run for at most 60000 ms and must stop at the configured target first.
- ADS1115 failure while the pump, post-target hold, or deflation PWM is active must immediately enter
  emergency vent; diagnostic streaming must never be a safety dependency.
- Normal deflation completion must close PC1 and skip all remaining PWM writes in
  that loop iteration. After manual or emergency venting, confirm low pressure, send
  `seal`, and verify PC1 LOW so the coil is not left energized.
- Relay-only controlled deflation uses a 200 ms scheduling period and ends each
  short PC1 pulse from `HAL_SYSTICK_Callback()`. `SysTick_Handler()` must call
  `HAL_SYSTICK_IRQHandler()` so ADS1115 and UART blocking time cannot stretch the
  nominal pulse. Emergency vent, `vent`, `seal`, normal completion, and sensor
  failure must cancel the pending pulse countdown before writing their final PC1
  state.
- Before tuning deflation or oscillometric thresholds, run a sealed non-human hold
  with PB8 HIGH, PC1 LOW, and PC8 HIGH. If passive pressure loss is comparable to or
  faster than the 3 mmHg/s controlled-deflation target, repair the pneumatic path;
  software PWM cannot regulate a system that already leaks faster than its target.
- With valid calibration, boot pressure >=15 mmHg must enter RESIDUAL_PRESSURE and
  vent, covering MCU reset during inflation.
- Idle diagnostic pressure failures record a fault but do not own actuator GPIO.
  A pending post-target hold retains automatic safety ownership; see the contract below.
- Buffer overflow must invalidate the capture and use SAMPLE_OVERFLOW emergency
  vent at every caller; see [Capture Reliability](./capture-reliability.md).
  ADS1115 recovery must occur only after the active caller can stop/vent.

## Post-Target Hold Fault Contract

- Scope: `s_deflate_hold_until_ms != 0U` is active acquisition even though the
  inflation pump is stopped. `ManualPump_TimeoutTask()` samples every 25 ms in
  both inflate and hold, independently of `stream start/stop`.
- Hold-only sampling shares over-pressure checks but returns before target and
  inflate-timeout branches. Above-target pressure must not restart the 1000 ms
  deadline. `PressureStream_Task()` prints the safety sample cache during hold.
- Any failed safety read invalidates the cache and invokes
  `ManualPump_EmergencyStop(SENSOR_READ)` before UART output or recovery. It
  cancels hold, PWM, pulse countdown and pending calculation before stopping the
  pump, closing PB8 and opening PC1. A failed read at the deadline cannot start PWM.
- `pressure`/`p` during a pending hold has the same failure protection. An already
  offline sensor cancels/vents before attempting any reinitialization. After an
  active failed read, defer stream recovery using the 1000 ms offline retry clock.
- Explicit `seal` cancels the pending hold and releases automatic ownership.
  A later idle diagnostic failure records its fault without changing GPIO.
- Required regression: compile actual main/control functions; inject HAL_ERROR,
  HAL_BUSY and HAL_TIMEOUT with stream ON/OFF and before/at the deadline; assert
  cancellation before GPIO, safe pump/valve order, vent before log/recovery, no PWM
  restart, healthy deadline/cache behavior, explicit query failure, over-pressure,
  and seal followed by idle fault without GPIO writes.
- Wrong: mark ADS offline and let the pending one-second timer start PWM.
  Correct: cancel and vent on the first failed read; recovery cannot resume it.

## Host Sealed-Hold Diagnostic Contract

- For a relay-only target-stop hold, wait for the actual `target reached` line,
  send `seal`, and verify PB8 HIGH / PC1 LOW / PC8 HIGH before observing.
  `seal` cancels `s_deflate_hold_until_ms` and PWM through
  `DeflateControl_Cancel()`; `close` only disarms the pump and closes PB8,
  so `close` alone does not cancel the pending automatic deflation.
- During the active observation, a pressure `sample failed`, stream `read failed`,
  ADS retry-init, corrupted line or reboot invalidates the comparison immediately.
  Stop and close out using vent -> fresh near-zero -> seal. A recovered ADC or a
  host freshness gap below two seconds does not restore the comparison's validity.
- Read final `fault`; non-NONE invalidates the hold even when the script reaches
  its end. Preserve the raw transcript and record invalidity separately from
  procedural completion. Test sensor-failure rejection and cleanup reachability
  offline before another physical round.

## Independent Watchdog

BP Pump2 Standard BP has no Stop control. Official manual paper3-15/PDF51 says
HOME returns to Main; HOME does not prove unloading. If MCU vent does not reach
fresh zero, keep pump off/vent, request HOME exit and manual unloading, then wait
for continuous fresh near-zero before seal. Never force seal after timeout or
request unavailable BP Stop. Preserve failed closeout and link recovery/export.

- IWDG uses prescaler 64 and reload 2499, nominally 4 seconds at a 40 kHz LSI.
- Freeze IWDG during debugger halt before starting it.
- Refresh IWDG from the main loop only after command, timeout, stream, and measurement
  safety tasks return. Do not refresh it from an interrupt.
- Keep physical PA0/PA1 polling disabled during the current relay-only stage; USART3
  start and stop are the approved bench substitutes.
