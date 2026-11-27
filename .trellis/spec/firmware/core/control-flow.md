# Control Flow

## Startup

`main.c` initializes in this order:

1. `HAL_Init()`
2. `SystemClock_Config()`
3. `MX_GPIO_Init()`
4. `MX_I2C1_Init()`
5. `MX_USART1_UART_Init()`
6. `MX_USART2_UART_Init()`
7. `MX_USART3_UART_Init()`
8. `MX_TIM8_Init()`
9. One-shot USART3 ready probe
10. `BP_Control_Init()` in all bring-up modes so fault state and safe GPIO defaults exist
11. `ADS1115_Init(&hi2c1)` in all bring-up modes
12. `ESP8266_Init(&huart1)` only when WiFi bring-up is enabled
13. `BP_Algorithm_Init()` only when relay-only mode is disabled
14. `MX_IWDG_Init()` after startup diagnostics, immediately before the main loop

Preserve this order unless the peripheral dependency changes.

Debug startup probes must be one-shot and must run only after their peripheral is initialized. Do not leave a `while (1)` serial probe in startup, and do not transmit debug probe text on USART1 because USART1 belongs to the ESP8266 AT-command path.

## Main Loop

The main loop calls:

- `Debug_UART_RxTask()` and `Process_DebugCommand()` for USART3 recovery and
  main-loop command execution; bytes arrive through the USART3 interrupt.
- `ManualPump_TimeoutTask()` for relay-only 25 ms inflate/post-target-hold safety
  sampling, target stop, over-pressure and the 60000 ms manual pump limit.
- `PressureStream_Task()` for optional 50 ms diagnostic records, reusing the
  active inflate/hold/PWM sample cache. It does not schedule hold safety reads.
- `BP_Control_Task()` for measurement state transitions, pressure sampling, pump, and valve control.
- `ESP8266_Task()` for WiFi background work.
- `HAL_IWDG_Refresh(&hiwdg)` only after the loop's safety tasks return.

Keep long blocking operations out of the main loop unless the state machine remains safe.

The post-target one-second hold-to-PWM branch runs after manual safety and
diagnostic streaming. Read failure must clear the pending deadline before that
branch can execute. See [Post-Target Hold Fault Contract](./safety-rules.md#post-target-hold-fault-contract).

Physical PA0/PA1 polling remains disabled during relay-only bring-up. USART3 `start`
and `stop` are the current bench-test substitutes for start and emergency stop.

## Measurement State Machine

`bp_control.c` owns:

- `BP_STATE_IDLE`
- `BP_STATE_INFLATE`
- `BP_STATE_DEFLATE`
- `BP_STATE_COMPLETE`
- `BP_STATE_EMERGENCY`

Inflation starts with `BP_Control_Start()`. The current target is `BP_INFLATE_TARGET_MMHG = 200`.

During deflation, samples are added through `BP_Control_PressureTick()`, which reads ADS1115 raw voltage and passes pressure plus voltage to `BP_Algorithm_AddSample()`.

## Interrupt Callbacks

- `HAL_GPIO_EXTI_Callback()` routes ADS1115 ALRT/DRDY to `ADS1115_DataReadyCallback()`.
- `HAL_UART_RxCpltCallback()` routes USART1 receive completion to `ESP8266_RxCallback()`.
- USART3 receive completion accepts bytes only with ErrorCode NONE. The ISR
  buffers and recognizes commands; parameter parsing and actuator changes run
  from the main-loop snapshot, not an interrupt callback.

Keep callbacks short and avoid blocking calls inside interrupt-driven paths.

## USART3 receive and mailbox integrity (2026-10-31)

### 1. Scope / Trigger

Applies to USART3 errors, receive rearming and command handoff in main.c.
HAL can invoke RxCplt before aborting an ORE receive; rearming there can erase
ErrorCode and accept a corrupted byte. Pending parameters also need isolation.

### 2. Signatures

`HAL_UART_ErrorCallback`, `Debug_UART_RxTask`, `Debug_CommandAcceptByte`,
`Debug_CommandTake(char *snapshot)`. Status adds
`[UART3] rx_errors=<uint16> rx_state=0x<hex>`; the error count saturates.

### 3. Contracts

Do not accept or rearm an errored RxCplt. ErrorCallback clears SR/DR flags,
rejects the partial line and pending non-stop/vent command, and rearms READY
once. Main retries READY once per pass, leaving BUSY RX intact. No GPIO, I2C,
logging, blocking abort or retry loop in these RX callbacks.

Freeze the 48-byte mailbox until a bounded PRIMASK-preserving copy. Parse only
that snapshot. Busy input can replace it only with complete stop/vent; discard
other pipelined commands and partial tails. Errors, invalid characters and
overflow reject the line through the next CR/LF. Send ordinary commands one
at a time and await a device response.

`Debug_I2CScan` must reject active acquisition/calculation or unsafe actuator
pins before any bus call. Idle scan passes seven-bit addresses shifted left
once to HAL, retaining bounded trials/timeouts.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| ORE with/without RXNE | Reject frame, preserve emergency command, restore RX |
| PE/NE/FE | Reject damaged line; do not execute its suffix |
| Pending command + ordinary input | Preserve accepted parameters |
| Pending command + complete stop/vent | Replace with emergency command |
| Invalid/overlength input | Reject whole line, never truncate into a command |
| Main enters with PRIMASK set | Leave it set after snapshot/rearm check |
| Active/unsafe i2cscan | Reject before I2C; no actuator changes |

### 5. Good / Base / Bad Cases

Good: ORE without RXNE recovers; after a clean delimiter status works again.
Base: target30 remains target30 despite a later cal-write line while pending.
Bad: unconditionally rearm RxCplt and thereby clear the vendor error state.

### 6. Tests Required

Run actual vendor IRQ/receive/end-transfer functions with production callbacks
and parser in `test/host/uart_rx_regression.c`; cover errors with/without RXNE,
resynchronization, emergency priority, snapshots, overflow, saturation and
PRIMASK. `i2c_scan_regression.c` asserts shifted addresses and pre-I2C gates.
Run the full host suite, Keil rebuild and RAM/stack gate. Idle target reads
confirm communication only; loaded acquisition requires separate validation.

### 7. Wrong vs Correct

Wrong: parse parameters from the ISR-owned buffer after releasing the command.
Correct: copy the frozen mailbox under a short preserved interrupt mask, then
parse the local snapshot while ISR reception continues.

## USART3 Actuator Debug Command Contract

### 1. Scope / Trigger

- Applies when `Process_DebugCommand()` handles a complete lowercase command received on USART3.

### 2. Signatures

- `open\r\n`: command token `open`.
- `close\r\n`: command token `close`.
- `vent\r\n`: open the deflation valve.
- `seal\r\n`: close the deflation valve.
- `start\r\n`: in relay-only bring-up mode, enter the same actuator state as `open`.
- `stop\r\n`: in relay-only bring-up mode, stop inflation and enter the vent state.

### 3. Contracts

| Command | PB8 (`VALVE1_CTRL`) | PC1 (`VALVE2_CTRL`) | PC8 (`PUMP_RELAY`) |
| --- | --- | --- | --- |
| `start` (relay-only) | LOW | LOW | LOW |
| `stop` (relay-only) | HIGH (released) | HIGH | HIGH |
| `open` | LOW | LOW | LOW |
| `close` | HIGH (released) | unchanged | HIGH |
| `vent` | HIGH (released) | HIGH | HIGH |
| `seal` | unchanged | LOW | unchanged |

Valve commands use `VALVE1_OPEN/CLOSE()` and `VALVE2_OPEN/CLOSE()` for their own
GPIO only. Pump commands use `PUMP_START/STOP()`; valve macros must never change PC8.
Combined command handlers must keep transition order visible.

### 4. Validation & Error Matrix

- Exact actuator command -> apply the table above and print the commanded pin state.
- Any other token -> report the existing unknown-command message and do not change actuator pins.

### 5. Good / Base / Bad Cases

- Good: `open` or relay-only `start` first closes PC1, then makes PB8 LOW and PC8 LOW for inflation.
- Good: `vent` first stops the pump (PC8 HIGH), closes the inflation path (PB8 HIGH), then opens the deflation valve (PC1 HIGH).
- Base: repeated actuator commands are idempotent for the pins they control.
- Bad: opening the deflation valve while PC8 is LOW or PB8 is LOW leaves inflation hardware active.

### 6. Tests Required

- Build the Keil target with zero errors.
- On non-human hardware, observe PB8 LOW and PC1 LOW after `open` or relay-only `start`; observe PB8 HIGH after `close`.
- Observe PC8 for LOW after `open` and HIGH after `close`.
- After `vent`, observe PB8 HIGH, PC1 HIGH, and PC8 HIGH. After `seal`, observe PC1 LOW.
- From `vent`, execute `start` and assert PC1 changes LOW before PC8 changes LOW.

### 7. Wrong vs Correct

```c
/* Wrong: starts the pump while the deflation valve may still be open. */
PUMP_START();

/* Correct: close deflation, open inflation, then start the pump. */
VALVE2_CLOSE();
VALVE1_OPEN();
PUMP_START();

/* Correct: stop inflation hardware before opening the deflation valve. */
PUMP_STOP();
VALVE1_CLOSE();
VALVE2_OPEN();
```

## USART3 Pressure Diagnostic Contract

### 1. Scope / Trigger

- Applies during relay-only bring-up after I2C1 and USART3 are initialized.
- Startup probes ADS1115 at address `0x48`; sampling never changes actuator GPIO.

### 2. Signatures

- `pressure\r\n` or `p\r\n` -> call `ADS1115_ReadSample(ADS1115_Sample_t *)`.
- `ADS1115_Init(I2C_HandleTypeDef *)` returns `HAL_OK` only after device-ready and
  config-register reads both succeed.

### 3. Contracts

Successful output fields all come from the same AIN0 conversion:

| Field | Type / unit | Meaning |
| --- | --- | --- |
| `raw` | signed 16-bit code | ADS1115 conversion register |
| `ads` | integer mV | voltage present at ADS1115 A0 |
| `sensor` | integer mV | divider-reconstructed sensor voltage; provisional |
| `est` | 0.1 mmHg | provisional pressure estimate, always marked `UNCAL` |

The conversion uses AIN0 single-ended, +/-4.096 V PGA, 128 SPS, comparator disabled,
and a 25 ms ready timeout. A failed sample clears the main-loop ready flag so the next
command retries initialization.

### 4. Validation & Error Matrix

- ADS1115 absent at boot -> print init failure and keep sealed-idle actuator state.
- ADS1115 reconnected -> next `pressure` retries initialization before sampling.
- I2C or conversion timeout -> print `sample failed status=<n>`; do not print stale data.
- Successful sample -> print all four fields and `UNCAL`.

### 5. Good / Base / Bad Cases

- Good: A0 voltage agrees with a multimeter within ADS1115 quantization and meter tolerance.
- Base: repeated commands at constant pressure produce stable raw/A0 readings.
- Bad: treating `sensor` or `est` as calibrated before confirming divider resistors and
  reference pressures in Stage 3.

### 6. Tests Required

- Build the Keil target with zero errors.
- Boot once with ADS1115 disconnected and confirm PB8 HIGH, PC1 LOW, PC8 HIGH.
- Reconnect ADS1115, execute `pressure`, and confirm retry initialization succeeds.
- Compare reported `ads` mV with a multimeter at A0 at ambient and one non-human pressure.
- Confirm pressure commands leave PB8, PC1, and PC8 unchanged.

### 7. Wrong vs Correct

```c
/* Wrong: reads a possibly stale conversion register. */
ADS1115_ReadRaw(&raw);

/* Correct: starts AIN0 conversion, waits with timeout, then derives one sample. */
ADS1115_Sample_t sample;
if (ADS1115_ReadSample(&sample) == HAL_OK)
{
    /* raw, ads voltage, sensor voltage, and estimate are coherent. */
}
```

## USART3 Bring-up Transport Contract

### 1. Scope / Trigger

- Applies whenever relay-only startup or a hardware driver reports diagnostics on USART3.

### 2. Signatures

- `ADS1115_Init(I2C_HandleTypeDef *)` returns status without writing a serial transport.
- `ADS1115_GetConfig(void)` returns the latest successfully probed config register.
- `Debug_CommandPoll(void)` polls USART3 and recovers peripheral receive errors.
- `BP_Control_Init(void)` configures state and fail-safe GPIO only; it does not write a serial transport.

### 3. Contracts

- Hardware drivers return status/data and do not call `printf()` during startup.
- `main.c` owns bring-up messages and sends them with `Debug_UART_Write()`.
- `BP_Control_Init()` must not call `printf()`, `HAL_UART_Transmit()`, or any other transport API.
- `main.c` reports the BP control initialization result with `Debug_UART_Write()` after the initializer returns.
- USART3 receive error recovery reads SR followed by DR, discards the partial command,
  and leaves the next complete line parseable.
- ADS1115 failures and USART3 recovery never change PB8, PC1, or PC8.

### 4. Validation & Error Matrix

- ADS1115 online -> report address and config, then reach `System Ready`.
- BP control init reached -> print `[BP_Control] Init OK calibration=<VALID|UNCAL>`, then continue to the ADS1115 probe.
- ADS1115 offline -> report a clear failure, then still reach `System Ready`.
- USART3 ORE/noise/framing/parity error -> discard the partial line and accept the next line.
- Incomplete command without CR/LF -> retain it until terminated; do not execute it early.

### 5. Good / Base / Bad Cases

- Good: `BP_Control_Init()` returns before `main.c` emits the calibration status through the established USART3 writer.
- Good: startup reports ADS state and `open`/`pressure` remain responsive.
- Base: an absent ADS1115 does not prevent relay-only command processing.
- Bad: a driver calls `printf()` while the selected debug transport is still part of
- Bad: any startup initializer emits its own `printf()` before `System Ready`, so one module can stall the whole console path.
  the startup path.

### 6. Tests Required

- Keil build must report zero errors and zero warnings.
- Static regression: the `BP_Control_Init()` function body contains no `printf`, and `main.c` owns its startup message.
- Boot with ADS1115 present and absent; both cases must reach `System Ready`.
- Send `open`, `stop`, and `pressure` with Enter after startup.
- After a malformed serial line, send a complete command and confirm recovery.

### 7. Wrong vs Correct

    /* Wrong: driver initialization owns startup logging. */
    printf("[ADS1115] Init OK\r\n");

    /* Correct: driver returns data and main.c owns the selected transport. */
    ready = (ADS1115_Init(&hi2c1) == HAL_OK) ? 1U : 0U;

    /* Wrong: BP control initialization owns startup logging. */
    BP_Control_Init(); /* Internally calls printf(). */

    /* Correct: initializer owns state/GPIO; main owns transport output. */
    BP_Control_Init();
    Debug_PrintADS1115InitResult(ready);

## USART3 Safety And Diagnostics Contract

### 1. Scope / Trigger

- Applies while BP_BRINGUP_RELAY_ONLY=1.
- Extends the existing actuator and pressure commands without enabling the full
  measurement state machine or physical PA0/PA1 polling.

### 2. Signatures

- help, status, pins, fault
- stream start, stream stop
- Existing start, stop, open, close, vent, seal, pressure, and p remain valid.
- Safety API: BP_Control_EmergencyStop(BP_Fault_t),
  BP_Control_RecordFault(BP_Fault_t), BP_Control_Reset().

### 3. Contracts

- start and open first require a valid Flash calibration and a successful ADS1115
  pressure sample. They then enter PB8=LOW, PC1=LOW, PC8=LOW and arm the
  target-pressure controller plus a 60000 ms absolute timeout.
- stop is the serial substitute for PA1: it immediately sets
  PC8=HIGH, PB8=HIGH, PC1=HIGH and returns without a delay.
- pressure / p remains a one-shot coherent sample and never owns actuator GPIO.
- stream start emits pressure records for telemetry; stream stop stops display only.
  Inflation samples ADS1115 every 25 ms independently of stream state. During active
  inflation and deflation, the stream prints the safety/control sample cache and does
  not perform a second conversion.
- Relay-only deflation updates `g_last_pressure_mmhg` from its own 25 ms algorithm
  samples. Deflation rate control and the below-15 mmHg completion rule therefore do
  not depend on stream state.
- An ADS1115 failure during inflation or deflation immediately stops the pump, closes
  PB8, opens PC1, and latches SENSOR_READ. Terminal branches leave the loop before
  later PWM code can overwrite the final valve state.
- Normal deflation completion closes PC1 and exits the current loop iteration.
- `pump` continuous mode is blocked because it bypassed target and timeout protection.
- After reset, a valid calibrated reading >=15 mmHg latches RESIDUAL_PRESSURE and
  opens PC1 so a reset during inflation cannot leave a pressurized cuff sealed.
- Full-state-machine ADS read failure, inflate timeout, or over-pressure calls
  BP_Control_EmergencyStop() and leaves the vent open.
- BP_SENSOR_CALIBRATION_VALID=0 blocks BP_Control_Start() before pump startup.
- The IWDG nominal timeout is 4 seconds at a 40 kHz LSI, is frozen during debugger
  halt, and is refreshed only after main-loop safety tasks complete.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Unknown serial command | Print Unknown; use help; do not change GPIO |
| start / open while UNCAL or ADS preflight fails | Do not start pump; report fault and vent on sensor failure |
| pressure reaches configured target | Stop pump, close PB8, hold, then begin controlled deflation |
| start / open exceeds 60000 ms | Fault MANUAL_TIMEOUT; stop pump and vent |
| Serial stop | Fault USER_STOP; immediate nonblocking vent |
| ADS absent during diagnostic | Record SENSOR_INIT; keep actuator state |
| ADS read fails during stream | Record SENSOR_READ; stop stream |
| ADS read fails during inflation or deflation | Fault SENSOR_READ; stop pump and vent; no later PWM overwrite |
| Reset with calibrated pressure >=15 mmHg | Fault RESIDUAL_PRESSURE; keep pump off and vent |
| Normal deflation reaches <15 mmHg | Close PC1; do not execute another PWM phase |
| `pump` command | Report blocked; do not start pump |
| Full measurement requested while uncalibrated | Fault UNCALIBRATED; do not start pump |
| Main loop stalls after IWDG starts | MCU resets after the approximate timeout |

### 5. Good / Base / Bad Cases

- Good: with stream disabled, start reaches its target from independent 25 ms samples,
  stops the pump, deflates, and ends PB8=HIGH, PC1=LOW, PC8=HIGH.
- Good: stream start, status, pins, and fault remain responsive while no full
  measurement state machine is running.
- Base: pressure and p report a coherent sample without changing actuator GPIO.
- Bad: using stream output as the source of truth for target or deflation control.
- Bad: executing a PWM phase after normal completion or emergency vent.
- Bad: refreshing IWDG inside an interrupt that can run while the main loop is hung.
- Bad: using a diagnostic ADS failure to silently leave a full measurement pump running.

### 6. Tests Required

- Run: python -m unittest discover -s "blood pressure monitor/test" -p "test_*.py" -v
- Build the Keil target and require zero errors and zero warnings.
- With 12 V disconnected, verify all old commands and all new diagnostic commands.
- With a non-human dummy cuff, run with stream stopped and verify target stop,
  independent deflation, final PC1 LOW, and no reset.
- Inject or disconnect ADS1115 during a low-pressure non-human test and verify
  SENSOR_READ leaves PC8 HIGH, PB8 HIGH, and PC1 HIGH.
- Reset with >15 mmHg residual pressure and valid calibration; verify
  RESIDUAL_PRESSURE and PC1 HIGH.
- During Keil debug halt, confirm IWDG debug freeze prevents an unexpected reset.

### 7. Wrong vs Correct

Wrong:

    if (stream_enabled) {
        g_last_pressure_mmhg = ReadPressure();
    }

Correct:

    if (manual_pump_active && sample_due) {
        if (ADS1115_ReadSample(&sample) != HAL_OK) {
            BP_Control_EmergencyStop(BP_FAULT_SENSOR_READ);
            return;
        }
        g_last_pressure_mmhg = sample.pressure_mmhg;
    }

## Fixed peak-window comparison profile (2026-11-05)

### Scope / Trigger

`PEAK_WINDOW_20261105` changes requested deflation speed for a nonhuman comparison;
BP arithmetic, calibration and extraction are unchanged.

### Signatures

`profile` queries; `profile normal|peak` calls `DeflateProfile_Set(0|1)`.
`DeflateTargetSpeed()` supplies the controller target.

### Contracts

Default normal. At target>=200, peak requests1.8mmHg/s within closed200..245,
3.0 outside; normal stays3.0. Target<200 and diagnostic stay2.0. Readback includes
mode/window/speeds/high_target_only; this is configuration, not achieved speed.
Existing400ms controller,200ms period and1ms pulse resolution are unchanged.
Writes require safe export gate, no active export and fresh pressure[-1,1];
NaN fails, no GPIO write. Existing parser cancels an active export before handling
non-export commands. Host records set/query and fixed parameters; restore
normal/query and target50 only after vent -> fresh zero -> seal.

### Validation & Error Matrix

Bad mode, stale/invalid ADS/calibration, unsafe pins, active acquisition or nonzero
pressure rejects write. Preserve278host/280firmware,2s freshness, bounded active
deadline and overflow abort. Nominal96.7s/3867points is only a planning estimate.

### Good / Base / Bad Cases

Good: measure actual fixed-band slope and beat support after one recorded trial.
Base: lower target ignores peak. Bad: assume1.8 was achieved from command ACK.

### Tests Required

Actual-C selector checks200/245 boundaries/normal/lower target/diagnostic. Gate
regression checks all pin combinations, activity, freshness, finite boundaries
and restore. Full suite, Keil/RAM/stack, verified flash and zero-pulse check precede
inflation. Compare retained captures using frozen features/gates.

### Wrong vs Correct

Wrong: change inference thresholds to make the comparison pass.
Correct: retain every origin and failed outcome; distinguish observed stability
from independent pressure accuracy and repeated-run reproducibility.
