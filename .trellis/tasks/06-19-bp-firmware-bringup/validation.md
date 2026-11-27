# Validation Notes

## 2026-10-31 load-off switching comparison

Operator OK to BP Stop/load-side12V disconnected; no independent voltage reading.
Runner syntax and3 offline guard checks pass. Nine cycles(3 each PB8-only,
PC1-only,PB8+PC8)passed;before/after readtest400 each,ADS0/0,UART0,NONE/ONLINE.
Closeout60 fresh near-zero then seal,post5s100VALID zeros,safe pins,pump OFF.
1484 fresh display records. No firmware/calibration/target changes or load return.
Manual close and natural target-stop have different GPIO order; cannot claim
loaded cause fixed or pump damaged. Details/hashes/failure preflight retained in
data/reports/load_off_switch_20261031-170340.md. Task remains in_progress.

## 2026-10-31 reading-path isolation diagnostic

114 host tests and zero-warning Keil build pass. Authorized download Verify OK
16:52:09; fresh READ_PATH_TEST_20261031 boot and established calibration restore.
Board readtest:400 conversions/10000ms,PASS_READ_ONLY,ADS errors0/recoveries0,
UART errors0,IDLE/ONLINE/NONE. Stack1224/free2872/reserved4096. No pump start.
Final vent->fresh zero->seal;5s99 fresh VALID samples0 and safe sealed pins.
Static reading did not reproduce the loaded-stop fault; root cause remains open.
Full wiring,build/download,method,hashes,limits and retained evidence:
`data/reports/read_path_test_20261031.md`.

## 2026-06-19 Serial / Boot Bring-up

- Firmware download is valid: the MCU can run the newly built code outside Debug.
- BOOT / reset path is usable after download and reset.
- CMSIS-DAP virtual serial COM port works; loopback test passed.
- USART3 debug output path works with:
  - STM32 `PB10 / USART3_TX` -> DAP `RX`
  - common `GND`
  - `115200 8N1`
- The earlier "no serial output" symptom was caused by a short 5-second startup probe window being easy to miss. Continuous UART output confirmed self-run and serial receive.
- PA4 buzzer testing confirmed firmware execution, but the buzzer module affects PA4 voltage/drive behavior. Treat PA4 buzzer behavior as a hardware/driver issue, not a flashing issue.

## Current Temporary State

- Resolved on 2026-06-20: `Debug_UART_Probe()` is now a one-shot USART3 startup message and no longer blocks normal firmware flow.
- The probe does not transmit on USART1, so it does not interfere with the ESP8266 AT-command path.

## Next Step

- Continue with PA0/PA1 button start/stop testing and ADS1115 pressure-read bring-up.

## 2026-06-20 Main Loop Restore And Button Entry

Firmware change:

- `Core/Src/main.c` keeps the PA0/PA1 debounced button polling path active in the main loop.
- `Debug_UART_Probe()` prints `[Debug] USART3 ready` once after USART3 and TIM8 initialization.
- Normal startup now continues into `ADS1115_Init(&hi2c1)`, `ESP8266_Init(&huart1)`, `BP_Control_Init()`, `BP_Algorithm_Init()`, then the main loop.

Wiring for validation:

- Debug serial: STM32 `PB10 / USART3_TX` to USB-serial or CMSIS-DAP `RX`, common `GND`, terminal at `115200 8N1`.
- Start button: `PA0 / BTN_START` to a momentary switch that shorts to `GND` when pressed. Internal pull-up is enabled.
- Stop button: `PA1 / BTN_STOP` to a momentary switch that shorts to `GND` when pressed. Internal pull-up is enabled.
- Pump PWM output: `PC8 / TIM8_CH3` to the pump driver input. Do not connect the pump to a human cuff for this first validation.
- Valves: `PC0 / VALVE1_CTRL` and `PC1 / VALVE2_CTRL` to the valve driver inputs.
- ADS1115: `PB6 / I2C1_SCL`, `PB7 / I2C1_SDA`, ADS1115 address `0x48`, common `GND`, ADS1115 powered from 3.3 V.
- ESP8266: USART1 remains reserved for AT commands; do not use USART1 for debug serial.

Non-human safety validation first:

- Keep the cuff disconnected from any person.
- Prefer testing with pump power disconnected or with the pump outlet vented to open air before any closed-cuff test.
- Confirm `BP_Control_Init()` leaves pump stopped, `VALVE1` closed, and `VALVE2` closed at boot.
- Press `PA1 / BTN_STOP` during any active test and confirm pump stop plus deflation valve action before connecting a cuff.

Keil build/download steps:

- Open `blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx` in Keil MDK.
- Build the project and confirm `Core/Src/main.c` is included in the project tree.
- Download to STM32F103ZET6.
- Reset the board or power cycle it after flashing.

Expected observations:

- USART3 terminal prints `[Debug] USART3 ready`, then the normal system-ready logs.
- The firmware does not repeatedly print `USART1` / `USART3` forever.
- The main loop remains active; PA0 press from idle logs `[Button] START pressed`.
- PA1 press while not idle logs `[Button] STOP pressed` and enters the stop/deflate path.
- USART1 is left for ESP8266 traffic only.

## 2026-06-22 Active-Low Pump Relay And USART3 Commands

Firmware change:

- `Core/Src/tim.c` now initializes `PC8` as a normal GPIO output for a low-level
  trigger pump relay during bring-up.
- `PC8 = HIGH` means relay released and pump off; `PC8 = LOW` means relay active
  and pump on.
- `PUMP_SET_DUTY()` / `PUMP_START()` / `PUMP_STOP()` keep the existing
  `bp_control.c` interface, but relay mode treats any non-zero duty as pump on.
- `USART3` debug input accepts `start` and `stop` commands terminated by Enter.
  The UART interrupt only buffers command state; measurement start/stop runs in
  the main loop.

Wiring for current validation:

- Debug serial:
  - STM32 `PB10 / USART3_TX` to USB-serial `RX`.
  - STM32 `PB11 / USART3_RX` to USB-serial `TX`.
  - Common `GND`.
  - Terminal `115200 8N1`.
- Pump relay control:
  - STM32 `PC8` to relay module `IN`.
  - STM32 `GND` to relay module `GND`.
  - Relay module `VCC` to the module-required supply, usually `5V`.
  - Relay power contacts: `12V+ -> COM`, `NO -> pump +`, `pump - -> 12V-`.
  - `NC` is not connected.
- Existing inflation valve:
  - STM32 `PC0 / VALVE1_CTRL` to the valve driver input.
  - Valve driver power uses the valve-rated supply and shares ground with STM32.
- Deflation valve:
  - `PC1 / VALVE2_CTRL` is still reserved, but the external deflation valve is
    not connected in the current hardware state.
- Pressure chain:
  - ADS1115 `SCL -> PB6`, `SDA -> PB7`, `VDD -> 3.3V`, `GND -> GND`,
    `ADDR -> GND`.
  - MPXV7007DP powered from `5V`; its divided output goes to ADS1115 `A0`.
  - MPXV7007DP `P1` connects to the cuff pressure node; `P2` stays open to air.

Non-human safety validation first:

- Do not connect the cuff to a person because the deflation valve is not
  connected.
- Prefer leaving pump 12V disconnected for the first firmware boot after
  flashing.
- On boot, confirm the relay is not active. A low-level trigger relay must be
  released because firmware drives `PC8` high during `MX_TIM8_Init()` and
  `BP_Control_Init()`.
- Keep a direct way to remove 12V pump power. Because the deflation valve is not
  connected, any cuff pressure must be released manually by opening the tube or
  disconnecting the cuff.

Keil build/download steps:

- Open `blood pressure monitor/MDK-ARM/blood pressure monitor.uvprojx`.
- Build the project and confirm `Core/Src/main.c`, `Core/Src/tim.c`, and
  `Core/Src/bp_control.c` are included in the Keil project tree.
- Download to STM32F103ZET6 and reset or power cycle the board.

Expected observations:

- USART3 prints `[Debug] USART3 ready`.
- Startup logs include `PC8=Pump relay active-low` and
  `Type start or stop on USART3, end with Enter`.
- Sending `start` plus Enter on USART3 prints `[DebugCmd] START` and starts the
  measurement inflate path. The relay should activate only after this command.
- Sending `stop` plus Enter prints `[DebugCmd] STOP` and stops the pump relay.
- Unknown commands print `Unknown, use start or stop`.
- With pump 12V connected and the cuff not on a person, pressure should rise
  when `start` activates the pump and must be manually released after `stop`
  until the external deflation valve is installed.

## 2026-06-23 Relay Lights During Debug

Firmware adjustment:

- `Core/Src/gpio.c` now also configures `PC8 / PUMP_RELAY_Pin` during
  `MX_GPIO_Init()` and writes it high before application modules start.
- `Core/Src/tim.c` still writes `PC8` high again during `MX_TIM8_Init()`.

Validation notes:

- For a low-level trigger relay, the relay can still turn on before firmware
  reaches `MX_GPIO_Init()` because reset/debug-halt leaves the MCU pin in its
  reset input state.
- During Keil Debug, if execution is halted at the beginning of `main()`, press
  Run so firmware reaches `MX_GPIO_Init()` before judging the relay state.
- Keep pump 12V disconnected while checking this behavior. Verify only the relay
  indicator first.
- If the relay remains active after startup logs print on USART3, measure the
  relay `IN` pin voltage:
  - near `3.3V` or module high level: relay should be off;
  - near `0V`: relay is being triggered or pulled down.
- If relay input floats during reset/debug, add an external pull-up on relay
  `IN` to a safe logic high level used by the relay input module, then re-test
  before reconnecting pump power.

## 2026-06-23 USART3 Start Command Not Reaching Main Loop

Observed serial output:

- CMSIS-DAP banner is printed by the probe.
- Firmware repeatedly prints `[Debug] USART3 ready`.
- `System Ready` is not printed, so `start` is not processed by the main loop.

Firmware adjustment:

- `main.c` now defines `BP_BRINGUP_ENABLE_ESP8266` as `0` by default.
- ESP8266 initialization is skipped during pump/pressure bring-up so missing
  ESP8266 wiring cannot delay entry into the main loop.
- Boot checkpoints were added around ADS1115, ESP8266, and BP control init.

Expected next serial output after rebuild/download:

- `[Debug] USART3 ready`
- `[Boot] ADS1115 init...`
- `[ADS1115] Init OK...` or `[ADS1115] Init FAILED...`
- `[Boot] ADS1115 init done`
- `[ESP8266] Skipped for pump/pressure bring-up`
- `[Boot] BP control init...`
- `[Blood Pressure Monitor] System Ready @ 72MHz`
- `Type start or stop on USART3, end with Enter`

If output stops after `[Boot] ADS1115 init...`, inspect ADS1115 I2C wiring
before testing pump control. If `System Ready` prints, USART3 `start` / `stop`
commands should be tested with pump 12V still disconnected first.

## 2026-06-23 Relay-Only Bring-up Mode

Firmware adjustment:

- `main.c` now has `BP_BRINGUP_RELAY_ONLY = 1`.
- Relay-only mode skips ADS1115 initialization, ESP8266 initialization, button
  polling, and the blood-pressure state machine.
- USART3 `start` directly calls `PUMP_SET_DUTY(PUMP_DUTY_FULL)` and
  `PUMP_START()`.
- USART3 `stop` directly calls `PUMP_STOP()`.

Expected serial output after rebuild/download:

- `[Debug] USART3 ready`
- `[Boot] Relay-only bring-up mode`
- `[ESP8266] Skipped for pump/pressure bring-up`
- `[Blood Pressure Monitor] System Ready @ 72MHz`
- `Type start or stop on USART3, end with Enter`

Validation:

- Keep pump 12V disconnected.
- Send `start` plus Enter; expect `[DebugCmd] START` and relay indicator on.
- Send `stop` plus Enter; expect `[DebugCmd] STOP` and relay indicator off.
- If only `[Debug] USART3 ready` appears after rebuild/download, verify Keil is
  building and downloading this project/target rather than an older image.

## 2026-06-23 Download Versus Debug Run

Observation:

- `[Debug] USART3 ready` appears after entering Debug, but normal Download does
  not produce firmware logs.

Interpretation:

- This is not caused by button polling or ESP8266 in relay-only mode.
- Normal Download may program flash without starting the CPU, depending on Keil
  and CMSIS-DAP settings.
- Entering Debug and pressing Run starts code execution, which explains why the
  USART3 ready message appears only after Debug.

Firmware adjustment:

- USART3 debug commands now use main-loop polling of `USART3->DR` instead of
  `HAL_UART_Receive_IT(&huart3, ...)`.
- This avoids USART3 receive interrupt state interfering with subsequent debug
  `printf()` output during relay-only bring-up.

Validation:

- After Download, press the board reset key or power-cycle the board.
- Confirm BOOT0 is low / boot-from-flash.
- In Keil Debug, if stopped at `main()`, press Run before judging UART output.
- In Keil target/debug settings, enable reset-and-run behavior if available.

## 2026-06-23 Only USART3 Ready Prints

Observation:

- Firmware prints `[Debug] USART3 ready` but no later boot text.

Firmware adjustment:

- Relay-only boot and debug-command logs now use `Debug_UART_Write()`, which
  calls `HAL_UART_Transmit()` directly.
- Relay-only `start` / `stop` logs also use `Debug_UART_Write()`.
- USART3 command reception remains polling-based in the main loop.
- A checkpoint `[Boot] after probe` is printed immediately after
  `[Debug] USART3 ready`.

Validation:

- After rebuild/download/debug-run, expected first two firmware lines are:
  `[Debug] USART3 ready` and `[Boot] after probe`.
- If only the first line appears, inspect for reset/fault immediately after the
  first UART transmit and verify the debugger is not stopped before the next
  statement.
- If both lines appear, continue checking the subsequent relay-only boot lines.

## 2026-06-23 Stop Command Relay Does Not Release

Firmware adjustment:

- `Pump_Stop()` now clears the stored pump duty and drives `PC8` high.
- `Pump_IsOn()` reads back `PC8`; relay-only `start` / `stop` commands print
  the interpreted pin state after changing the output.

Expected logs:

- After `start`: `[Pump] PC8=LOW relay=ON`
- After `stop`: `[Pump] PC8=HIGH relay=OFF`

Interpretation:

- If `stop` prints `PC8=HIGH relay=OFF` but the relay indicator stays on, the
  relay module input logic, wiring, or power reference does not match the
  active-low assumption. Measure relay `IN` relative to relay `GND`.
- If `stop` prints `PC8=LOW relay=ON`, firmware or pin configuration is still
  holding the output low and should be debugged before reconnecting pump power.

## 2026-06-23 Manual Valve Commands

Firmware adjustment:

- Relay-only UART commands now include direct valve controls:
  - `open` -> `VALVE1_OPEN()` -> `PC0=HIGH`
  - `close` -> `VALVE1_CLOSE()` -> `PC0=LOW`
  - `vent` -> `VALVE2_OPEN()` -> `PC1=HIGH` (reserved for deflation valve)
  - `seal` -> `VALVE2_CLOSE()` -> `PC1=LOW`
- Startup help text now lists `start stop open close vent seal`.

Non-human validation:

- Do not connect cuff to a person.
- Keep pressure low and be ready to disconnect 12 V pump power.
- For the currently connected single valve, use `open` before `start`.
- Test sequence:
  1. `open` -> expect `[Valve1] OPEN PC0=HIGH`.
  2. `start` -> expect `[DebugCmd] START`; pump relay command active.
  3. Observe whether air reaches the cuff/common pressure node.
  4. `stop` -> expect pump command off.
  5. `close` -> expect `[Valve1] CLOSE PC0=LOW`.
- Because the deflation valve is not installed, release any cuff pressure
  manually by opening the tube or disconnecting the cuff.

## 2026-06-23 Pressure Sensor Read Command

Firmware adjustment:

- Relay-only UART commands now include:
  - `pressure` or `p` -> start one ADS1115 A0 conversion and print raw data.
- Relay-only boot initializes ADS1115 so pressure reads can be tested without
  running the blood-pressure state machine.

Expected output:

- `[Pressure] raw=<adc> ads=<mV>mV sensor=<mV>mV`
- `ads` is the ADS1115 A0 voltage after the divider.
- `sensor` is the estimated MPXV7007DP output before the 10k/20k divider.

Non-human validation:

- Keep cuff off any person.
- MPXV7007DP `P2` open to atmosphere; `P1` connected to the cuff/common pressure
  node.
- At zero differential pressure, MPXV7007DP output should be around 2.5 V, so
  ADS1115 A0 should be around 1.6-1.7 V with the 10k/20k divider.
- Send `pressure` repeatedly. With no pressure change, raw and voltage should be
  reasonably stable.
- Lightly squeeze the cuff or apply a small pressure to `P1`; `raw`, `ads`, and
  `sensor` should increase. Releasing pressure should bring them back near the
  starting value.

Troubleshooting:

- `ADS1115 start failed` or `read failed`: check ADS1115 `VDD=3.3V`, `GND`,
  `SCL=PB6`, `SDA=PB7`, `ADDR=GND`, shared ground, and I2C pull-ups.
- `ads` near 0 mV: check sensor power, divider wiring, and A0 connection.
- `ads` above 3300 mV: stop testing and inspect divider before continuing.

## 2026-06-23 Pressure Command Startup Regression

Observation:

- After adding pressure reads, USART3 appeared unresponsive again.

Root cause:

- Relay-only boot called `ADS1115_Init(&hi2c1)`.
- `ADS1115_Init()` uses `printf()`, which is not reliable in the current
  bring-up UART/Keil configuration and can prevent later direct UART logs from
  appearing.

Firmware adjustment:

- Added `ADS1115_InitSilent(&hi2c1)` to set the ADS1115 driver handle without
  printing.
- Relay-only boot no longer initializes ADS1115.
- The `pressure` command calls `ADS1115_InitSilent(&hi2c1)` immediately before
  starting an ADS1115 conversion.

Expected boot output is restored before any pressure command is sent.

## 2026-08-25 USART3 Command Path And ADS1115 Startup Recovery

Observed:

- After enabling the Stage 2 startup probe, USART3 transmitted startup text but
  `open`, `pressure`, and other received commands stopped responding.
- USART3 remains mapped to PB10 TX and PB11 RX; no remap conflict was found.

Root cause analysis:

- Category E (implicit assumption) plus D (integration coverage gap).
- `ADS1115_Init()` coupled the I2C driver to stdio output during startup.
- The earlier silent-init workaround was later bypassed when the required startup
  probe called the logging initializer again.
- The USART3 polling path also lacked explicit ORE/noise/framing/parity recovery.

Firmware correction:

- `ADS1115_Init()` no longer calls `printf()`.
- The driver stores the probed config and exposes it with `ADS1115_GetConfig()`.
- `main.c` reports initialization through direct USART3 writes.
- USART3 polling clears receive errors and discards any partial command.
- Relay-only mode and actuator pin behavior are unchanged.

Build validation:

- Keil ARM Compiler 6.22: `0 Error(s), 0 Warning(s)`.
- `main.c`, `ads1115.c`, and `i2c.c` remain in the Keil project.

Required non-human hardware validation:

1. Disconnect actuator 12 V power and reset the board.
2. Confirm startup reaches `System Ready`.
3. Send `open` plus Enter and confirm a response.
4. Send `stop` plus Enter and confirm a response.
5. Send `pressure` plus Enter and confirm a sample or a clear ADS1115 error.
6. Confirm pressure reads do not change PC0, PC1, or PC8.
7. Keep MPXV7007DP testing below 40 mmHg and do not connect a human.

Hardware result:

- User confirmed all required non-human checks passed on 2026-08-25.
- Representative zero-pressure sample:
  raw=15024 ads=1878mV sensor=2638mV est=0.2mmHg UNCAL.
- Raw-to-A0 conversion is coherent: 15024 * 0.125 mV = 1878 mV.
- The A0 multimeter reading agreed, repeated samples were stable, and the
  pressure command did not change PC0, PC1, or PC8.
- Stage 2 is complete. Stage 3 owns divider/sensor reconciliation and calibrated
  pressure conversion; the current est value remains uncalibrated.

## 2026-08-25 Stage 3 Divider Reconciliation

- Sensor confirmed as MPXV7007DP.
- Measured divider: 6.823 kohm from sensor OUT to ADS1115 A0 and 17.96 kohm
  from A0 to GND.
- Firmware divider reconstruction scale updated from 1.40476 to 1.37990.
- The prior sample raw=15024 / ads=1878 mV reconstructs to approximately
  2591 mV with the measured divider.
- Zero voltage and sensitivity remain uncalibrated; collect non-human reference
  points below 40 mmHg before changing those constants.

## 2026-08-25 Calibration-Wait Safety Hardening

Firmware changes:

- Relay-only mode remains enabled; physical PA0/PA1 button polling remains disabled.
- USART3 start and stop remain the bench substitutes for the two buttons.
- Added a unified BP_Fault_t model and nonblocking emergency vent.
- Full measurement remains locked while calibration is invalid.
- Relay-only start/open now automatically stops and vents after 5000 ms.
- Added help, status, pins, fault, stream start, and stream stop.
- Added nominal 4-second IWDG with debugger freeze and main-loop refresh.
- Added iwdg.c and stm32f1xx_hal_iwdg.c to the Keil project and synchronized .ioc.

Software validation:

- Static safety contracts: 11 tests passed.
- Keil ARM Compiler 6.22: 0 Error(s), 0 Warning(s).
- Existing start/stop/open/close/vent/seal/pressure/p tokens are covered by tests.
- New diagnostics, actuator-independent pressure reads, emergency ordering,
  calibration lock, timeout, and IWDG project sync are covered by tests.

Required wiring for the next non-human test:

- USART3: PB10 TX to USB-serial RX, PB11 RX to USB-serial TX, common GND,
  terminal at 115200 8N1 with text transmit/receive.
- PC0 to the inflation-valve MOSFET driver input, PC1 to the deflation-valve
  MOSFET driver input, and PC8 to the active-low relay input.
- STM32, ADS1115, driver board, relay module, and 12 V supply grounds must be common.
- ADS1115 remains PB6 SCL, PB7 SDA, VDD 3.3 V, ADDR GND; MPXV7007DP output
  remains divided into A0.
- PA0 and PA1 need not be connected for this test.

Non-human validation sequence:

1. Disconnect pump/valve 12 V power. Build, download, reset, and reach System Ready.
2. Confirm the startup log reports relay-only mode, UNCAL, and IWDG enabled.
3. Send help, status, pins, and fault. Initial pins must be PC0 LOW, PC1 LOW,
   PC8 HIGH; status must show RELAY_ONLY and UNCAL.
4. Send pressure and p. Confirm the established UNCAL record format and unchanged pins.
5. Send stream start. Confirm roughly four pressure records per second, then send
   stream stop and confirm output stops.
6. Send start or open with actuator 12 V still disconnected. Confirm the relay
   indicator/PC8 goes active, then after about 5 seconds observe:
   [Safety] Manual pump timeout 5000ms; PC0=LOW PC1=HIGH PC8=HIGH.
7. Send pins and fault. Expect PC0 LOW, PC1 HIGH, PC8 HIGH and MANUAL_TIMEOUT.
8. Send start again, then immediately send stop. Expect immediate vent pins and
   USER_STOP without a 3-second serial freeze.
9. In Keil debug, halt execution for more than 5 seconds after IWDG starts, resume,
   and confirm debugger freeze prevented an unexpected reset.
10. Leave the firmware running for at least 30 seconds and confirm commands remain
    responsive and no spontaneous watchdog reset occurs.

Safety limits:

- Do not connect a human.
- For the 5-second timeout test, keep actuator 12 V disconnected or leave the pump
  outlet open to atmosphere so pressure cannot accumulate.
- If 12 V is later enabled for a brief dummy-cuff check, keep a direct power cutoff,
  watch the reference pressure continuously, and stop below 40 mmHg because the
  fitted MPXV7007DP cannot cover blood-pressure inflation range.

Hardware result: pending user execution.

## 2026-08-26 BP_Control Startup Transport Regression

Observation:

- After reset, USART3 printed only `[Debug] USART3 ready`.
- `[Boot] after probe` and all command responses were absent.

Root cause analysis:

- Category E (implicit transport assumption) plus D (integration coverage gap).
- `BP_Control_Init()` called `printf()` between the two probe messages,
  repeating the earlier ADS1115 startup transport failure.
- Existing tests did not forbid startup logging inside `BP_Control_Init()`.

Firmware correction:

- `BP_Control_Init()` now owns only BP state reset and sealed-idle GPIO setup.
- `main.c` reports calibration state through `Debug_UART_Write()`.
- A static regression test now rejects `printf` in `BP_Control_Init()`.
- Pump/valve ordering, commands, IWDG, and ADS1115 conversion are unchanged.

Software validation:

- Static safety contracts: 12 tests passed.
- Keil ArmClang 6.22: 0 errors and 0 warnings.
- `main.c` and `bp_control.c` remain present in the Keil project.

Required non-human hardware validation:

1. Disconnect pump and valve 12 V power; do not connect a human.
2. Wire USART3 PB10 TX to USB-serial RX and PB11 RX to USB-serial TX;
   use common GND and 115200 8N1.
3. Build and download `blood pressure monitor.uvprojx` in Keil, run, then reset.
4. Expect `USART3 ready`, `[BP_Control] Init OK calibration=UNCAL`,
   `[Boot] after probe`, the ADS1115 result, `System Ready`, and the IWDG line.
5. Send `help` plus CR/LF and expect the two `[Help]` lines.
6. Send `pins`; expect PC0 LOW, PC1 LOW, and PC8 HIGH.
7. Run for at least 10 seconds; startup text must not repeat.

Hardware result: passed on 2026-08-26 per user confirmation. Startup continued past
`USART3 ready`; help/status/pins/fault, pressure/p, stream start/stop, the 5000 ms
manual timeout, immediate serial stop, and watchdog boot stability all behaved as
documented during non-human testing.

## 2026-09-19 Sensor-Agnostic Calibration Foundation (software)

Firmware changes:

- `Core/Inc/ads1115.h`: `MPXV7007_SENSITIVITY_V_PER_KPA` corrected from the
  erroneous 0.57f to the datasheet value 0.286f (transfer function
  `Vout = 5.0V*(0.057*P + 0.5)`), which removes the previous ~2x pressure
  under-read.
- New `Core/Src/bp_cal.c` + `Core/Inc/bp_cal.h`: calibration persistence in the
  last internal-Flash page (`0x0807F800`) with magic word `"CAL1"` and CRC16.
  Stores the sensor-agnostic linear model
  `pressure_mmhg = slope_mmhg_per_unit * sensor_voltage_v + intercept_mmhg`.
- `ADS1115_ReadSample()` pressure conversion now routes through
  `BP_Cal_GetPressure_mmHg()`: a stored, CRC-valid record is used when present;
  otherwise the default MPXV7007DP constants apply and results stay UNCAL.
- `BP_Control_IsCalibrationValid()` is now runtime state: valid only when a
  stored calibration record loads successfully. `BP_SENSOR_CALIBRATION_VALID`
  stays 0 as the compile-time default, so behavior without a stored record is
  unchanged.
- New USART3 commands: `cal` (show status/parameters), `cal clear` (erase the
  record), `cal write <slope> <intercept>` (write + read-back verify + report).
- Command buffer enlarged from 24 to 48 bytes to hold parameter lines.
- `bp_cal.c` added to the Keil project; static contract tests extended to 17.

Software validation:

- Static safety contracts: 17 tests passed (added sensitivity-constant, runtime
  calibration validity, pressure-route, flash/CRC/verify, and cal-command
  checks).
- Calibration tool suite: 4 tests passed (21 total across both suites).
- Keil ARM Compiler 6.22: 0 Error(s), 0 Warning(s).
- `bp_cal.c` present in the Keil project; `stm32f1xx_hal_flash.c` already
  included.

Required non-human hardware validation (pending user execution):

1. Disconnect actuator 12 V power; do not connect a human.
2. Build, download, reset; confirm startup logs `[Cal] no valid record; UNCAL
   defaults` and `[BP_Control] Init OK calibration=UNCAL`.
3. Send `cal`; expect `[Cal] UNCAL (no stored record); defaults zero=2.62V
   sens=0.286V/kPa`.
4. Send `cal write 75.0 -37.5`; expect `written+verified ... -> VALID` and the
   `[Cal] VALID slope=75.000 ...` status line.
5. Send `cal`; expect the stored values with `zero=0.500V sens=0.1000V/kPa`.
6. Reset the board; confirm the record survives reset (`[Cal] stored record
   valid`) and `[BP_Control] Init OK calibration=VALID`.
7. Send `cal clear`; expect cleared; reset and confirm UNCAL again.
8. Confirm pressure/p and pins are unchanged by the cal commands.

Expected post-fix zero-pressure estimate with defaults: at the known 15024 raw /
2638 mV sensor zero, the corrected 0.286 V/kPa default reports roughly
`est=3mmHg UNCAL` instead of the previous ~0.2 mmHg (the 2x sensitivity error
is removed; exact zero/gain still comes from the BP Pump 2 calibration).
### 2026-09-19 auto pressure streaming (EK-OmniProbe data source)

- `main.c`: pressure stream now auto-starts after boot (IWDG init) at 250 ms
  intervals; `stream stop` / `stream start` still toggle it manually.
- `Debug_PrintPressureSample()` now prints runtime calibration state
  (`VALID` / `UNCAL`) instead of a hardcoded `UNCAL`.
- Keil build 0 Error(s) 0 Warning(s); 21 unit tests pass.
- Expect after download+reset: `[Stream] auto-started every 250ms ...` then one
  `[Pressure] raw=... ads=...mV sensor=...mV est=...mmHg UNCAL` line per 250 ms
  over USART3. EK-OmniProbe COM6 115200 8N1 can then capture the stream.

## 2026-10-17 Pressure-independent safety hardening

Observed failure:

- With `stream stop`, relay-only inflation used a stale `g_last_pressure_mmhg` and
  passed a 50 mmHg target; pressure later exceeded 80 mmHg.
- ADS1115 command reads failed while the pump remained active, followed by an MCU
  restart. The restart left residual pressure sealed until an explicit vent.
- Relay-only deflation also relied on stream reads for rate control and completion.
- A terminal `VALVE2_CLOSE()` or emergency vent could be overwritten by the PWM code
  later in the same loop iteration.

Corrections:

- Inflation now samples ADS1115 every 25 ms regardless of stream state and vents on
  the first failed sample.
- Start requires valid calibration plus a successful sensor preflight.
- Deflation updates pressure/cache from its own 25 ms algorithm sample and vents on
  read failure.
- Normal completion and sensor-failure branches leave the current loop before PWM can
  write PC1 again.
- Continuous `pump` mode is blocked.
- A calibrated boot reading >=15 mmHg triggers RESIDUAL_PRESSURE emergency vent.

Verification:

- 27 Python tests passed.
- Keil rebuild: 0 Error(s), 0 Warning(s); existing sources remain in uvprojx.
- `UV4 -f`: Full Chip Erase, Programming Done, Verify OK; calibration restored and
  read back as slope=88.300, intercept=-19.96.
- Non-human, stream OFF: target 20 -> stopped at 20.3 mmHg, entered deflation,
  printed `Deflate done; valve2 closed`, then measured 3.4 mmHg.
- Final state: PC0 LOW, PC1 LOW, PC8 HIGH, pump OFF, fault NONE.

Human-data prerequisite:

- Before any human run, repeat once on a non-human cuff at the intended human target
  (normally 30 mmHg above expected SBP) and confirm no reset, ADS failure, excessive
  peak, or delayed stop.
- Every run ends with pressure confirmation, `seal`, and `pins`; PC1 must be LOW.

## 2026-10-18 SysTick deflation pulse and sealed-hold diagnosis

Firmware correction:

- Restored the controlled-deflation scheduler to 200 ms (5 Hz), above the
  0.9-4 Hz pulse-analysis band.
- Added a SysTick-owned pulse countdown so the nominal 2 ms PC1 HIGH pulse closes
  independently of the 8-12 ms blocking ADS1115 conversion and UART work.
- `SysTick_Handler()` now calls `HAL_SYSTICK_IRQHandler()`.
- Emergency stop, manual `vent`, `seal`, normal completion, sensor failure, and a
  new inflation start cancel a pending pulse before setting the terminal valve state.
- Replaced modulo phase writes with one pulse start per elapsed 200 ms period; late
  main-loop execution does not emit catch-up pulses.

Software verification:

- 30 Python tests passed, including SysTick closure and vent/seal cancellation
  contracts.
- Keil rebuild and download: 0 Error(s), 0 Warning(s).
- `main.c` and `stm32f1xx_it.c` remain present in the Keil project.
- Full-chip download cleared calibration; restored and read back
  `cal write 84.054 -19.374` as VALID.

Non-human results with BP Pump 2 Standard BP 120/80, 80 BPM, External Cuff,
adult cuff on rigid cylinder:

- Target reached 182.8 mmHg. During the one-second pre-deflation hold, while PC1
  remained LOW and no pulse was active, pressure fell from about 178.0 to
  145.7 mmHg.
- Controlled deflation then ran from 144.5 to 14.4 mmHg in about 16.0 seconds.
  Firmware calculation failed because the high-pressure SBP envelope crossing was
  lost before usable sampling.
- Offline analysis still found a dominant 82.2 BPM component and a DBP-side crossing
  near 77.7 mmHg, consistent with the BP Pump signal being present.
- A second run cancelled automatic hold/deflation immediately at 182.7 mmHg and kept
  PC0 LOW, PC1 LOW, PC8 HIGH. With no valve pulses, pressure still fell from
  179.3 to 32.3 mmHg in 12 seconds (about 12.3 mmHg/s average; about 33 mmHg in
  the first second). This proves the dominant failure is pneumatic leakage or cuff
  relaxation rather than pulse timing.
- Both runs ended with `vent`, pressure near 1 mmHg, `seal`, and
  `pins`: PC0 LOW, PC1 LOW, PC8 HIGH.

Required next hardware validation:

1. Keep the setup non-human and vent to near 0 mmHg before touching tubing.
2. With actuator power off, identify each three-way valve's COM/NO path by an
   unpowered low-pressure continuity test; do not infer it from an unfamiliar label.
3. Confirm the unused normally-open outlet on both valves is capped airtight, then
   inspect the cap, tee, quick connector, cuff bladder, and sensor tubing.
4. Repeat the 180 mmHg sealed hold. Passive loss must be below the 3 mmHg/s
   controlled-deflation target before another algorithm run is meaningful.

Follow-up after sealing the unused valve ports:

- Repeating PC0 LOW / PC1 LOW / pump OFF produced essentially the same result:
  179.6 to 32.7 mmHg in 12 seconds. The external port caps were not the dominant
  cause.
- Added a guarded `holdopen` diagnostic that stops the pump, keeps PC1 LOW, holds
  PC0 HIGH, and automatically emergency-vents after 15 seconds. Static contracts
  increased to 31 tests; Keil rebuild/download remained 0 errors and 0 warnings;
  calibration `84.054 / -19.374` was restored and verified after download.
- PC0 HIGH / PC1 LOW / pump OFF also lost pressure rapidly, about 184.5 to
  24.9 mmHg in 12 seconds. Therefore the loss is not specific to the inflation
  valve's de-energized path.
- BP Pump 2 Operators Manual pages 3-3, 3-8/3-9, 3-14/3-15, and B-2/B-3 confirm:
  Standard BP supplies simulated volume pulses while the DUT performs inflation
  and deflation; external-cuff compliance depends strongly on cuff volume and
  wrapping tightness.
- Correction after re-reading the specification sheet: the `<2 mmHg/min` internal
  leak specification applies **with a minimum volume of 300 cc**. The main manifold
  is only about 20 cc; selecting Internal Adult adds about 290 cc for a total of
  310 cc. A high displayed mmHg/min value from External Cuff with only a short
  capped tube cannot be compared directly with the `<2 mmHg/min` specification and
  does not by itself prove the Tester is faulty.

Next isolation step:

1. For a BP Pump 2 self-leak baseline, seal the pressure port, explicitly select
   `Cuff: Internal Adult` (310 cc total), and wait for the leak rate to become
   available after a stable pressure interval. Only this >=300 cc configuration
   may be compared with the `<2 mmHg/min` specification.
2. For external-path diagnosis, disconnect the blood-pressure-monitor hose from
   the tee and cap that tee branch, leaving BP Pump 2 + tee + external adult cuff
   tightly wrapped on a non-compressible rigid mandrel. Treat this as a total-system
   leak/compliance measurement, not a direct Tester self-leak specification check.
3. Compare isolated external path versus the complete monitor path under the same
   cuff volume and wrapping; do not infer Tester failure from pressure-rate readings
   taken with materially different pneumatic volumes.

## 2026-10-27 Standard BP Capture And `/2` Replay

- Test remained non-human. BP Pump 2 used External Cuff, 120/80 mmHg and
  80 BPM. Firmware was `CAPTURE_VALVE_20261025`; stored calibration read back
  VALID at `82.326 / -19.887`.
- A low-pressure stop test preceded the full run. The host requested stop while
  inflating toward 50 mmHg; observed peak was 25.1 mmHg. Pump-off/vent behavior
  was confirmed, followed by `vent` -> fresh low pressure -> `seal`.
- The Standard BP run reached 150.3 mmHg, held, and completed natural controlled
  deflation. Firmware reported `103/82 mmHg`, `84 BPM`, `valid=1` with
  Capture n=2129, dropped=0, duration=53200 ms and interval=25 ms. Calculation
  timing was work=1545 ms, wall=2224 ms, max_step=31 ms.
- The retained capture exported as `bp.capture/2`: one begin, 2129 points,
  exactly one valve row, one features row and one end row; checksum hash=27142329.
  Every adjacent MCU tick interval was 25 ms.
- Valve evidence recorded 267 pulses, period=200..200 ms, on-time=1..5 ms and
  four adjacent pressure steps at the 5.0 mmHg threshold. Phase bins were
  `[3,1,0,0,0,0,0,0,0]`; maximum rise was +5.367668 mmHg at index 409,
  phase 42 ms, and maximum fall was -7.810104 mmHg at index 408, phase 17 ms.
- Production-C replay reproduced `103/82 mmHg`, `84 BPM`, map index 700 /
  88.38955 mmHg, raw SBP feature 113.538109 mmHg and raw DBP feature
  87.66534 mmHg. Envelope and smoothed-envelope maximum absolute errors were
  both 0; envelope bits, feature bits and validity all matched.
- Post-export checks found cal VALID, ADS ONLINE, errors=0, recoveries=0,
  PC0/PC1 LOW, PC8 HIGH, pump OFF, and a stable 5-second zero-pressure snapshot
  (100/100 samples at est=0.0 mmHg). `USER_STOP` is the expected closeout latch.
- Evidence: `tmp/linkpad_lowpressure_20261027-213936.ndjson`,
  `tmp/linkpad_standard_20261027-214101.ndjson`,
  `tmp/capture_export_20261027-214442.ndjson`, its `.csv`,
  `.verified.ndjson` and `.replay.json`, plus
  `tmp/capture_preflight_20261027-214614.ndjson`.
- Three same-image valid result rounds are now 113/91 at 75 BPM, 99/81 at
  75 BPM, and 103/82 at 84 BPM. Descriptive mean/sample-SD/range are
  SBP 105.0/7.21/14 mmHg, DBP 84.67/5.51/10 mmHg, and pulse 78.0/5.20/9 BPM.
  Only the first and third rounds retain complete verified `/2` waveforms; the
  second capture was lost after MCU reset. This is not three-waveform
  repeatability, clinical accuracy, or ISO 81060-2 evidence. Runtime stack
  watermark remains pending.

## 2026-10-27 Three-Consecutive-Waveform Batch

- Continuing without firmware, calibration, threshold or timing changes produced
  two further non-human External Cuff Standard120/80,80BPM rounds. Together with
  the immediately preceding 103/82@84 round, this forms a three-run same-image
  batch with a complete verified `/2` waveform for every run.
- Run 2 reached 151.6 mmHg and reported `118/88 mmHg`, `75 BPM`, `valid=1`.
  Capture n=1921, dropped=0, duration=48000 ms; calculation work/wall/max-step was
  1390/1998/30 ms. Export hash=2299046525, valve pulses=241, period=200..200 ms,
  on-time=1..5 ms, and zero >=5.0 mmHg adjacent steps.
- Run 3 reached 151.3 mmHg and reported `114/90 mmHg`, `75 BPM`, `valid=1`.
  Capture n=1737, dropped=0, duration=43400 ms; calculation work/wall/max-step was
  1264/1817/30 ms. Export hash=332354659, valve pulses=218, period=200..200 ms,
  on-time=1..4 ms, and zero >=5.0 mmHg adjacent steps.
- Both new captures have exact 25 ms adjacent MCU tick intervals. Production-C
  replay reproduced target results, envelopes, smoothed envelopes, feature bits
  and validity with zero error.
- Batch results are `103/82@84`, `118/88@75`, `114/90@75`. Descriptive
  mean/sample-SD/range are SBP 111.67/7.77/15 mmHg, DBP 86.67/4.16/8 mmHg and
  pulse 78.0/5.20/9 BPM. This completes the three-consecutive-waveform acquisition
  gate only; it does not establish simulator accuracy, clinical accuracy,
  ISO 81060-2 compliance or valve causation.
- Each run closed out with `vent` -> fresh low pressure -> `seal`, safe pins and
  zero ADS errors/recoveries. External BP stop is henceforth inferred when at least
  40 consecutive fresh pressure records remain around 0 mmHg; panel Stop is not a
  routine prompt and is reserved for failure to settle or restart.
- New evidence: `tmp/linkpad_standard_20261027-215629.ndjson`,
  `tmp/capture_export_20261027-220211.*`,
  `tmp/linkpad_standard_20261027-220412.ndjson`, and
  `tmp/capture_export_20261027-220714.*`. Runtime stack watermark remains pending.

## 2026-10-28 Stack watermark bring-up and Standard BP

- The final `STACK_WATERMARK_20261027` image was downloaded with Keil `UV4 -f`
  and verified. The linker/runtime stack remains 4096 bytes; CubeMX metadata and
  the Keil project include the implementation. The firmware initializes its
  watermark at the first statement in `main`, after C runtime ZI clearing and
  before `HAL_Init`.
- Before pressure operation, Flash calibration was confirmed UNCAL after full
  erase. With IDLE, manual OFF, ADS ONLINE, fault NONE and PC0/PC1 LOW, PC8 HIGH,
  pump OFF, the unchanged validated coefficients were restored using
  `cal write 82.326 -19.887`. Firmware returned `written+verified`; an
  independent `cal` query read VALID 82.326/-19.89. A subsequent five-second
  observation contained 191 fresh near-zero records; ADS errors/recoveries were
  both zero. Evidence: `tmp/stack_watermark_cal_restore_20261027.ndjson`.
- Idle/diagnostic stack baseline was `used=1384 free=2712 reserved=4096
  saturated=0`. This is not the measurement/calculation/export-path maximum.
- A non-human target-50 active-stop test stopped at an observed 29.3 mmHg. The
  host confirmed immediate safe pump/valve pins, then performed
  `vent` -> consecutive fresh samples <=2 mmHg -> `seal`; final pins were
  PC0/PC1 LOW, PC8 HIGH, pump OFF. ADS errors/recoveries remained zero. Log:
  `tmp/linkpad_lowpressure_20261027-225516.ndjson`.
- A complete non-human External Cuff Standard BP run (120/80 mmHg, 80 BPM)
  reached 151.5 mmHg, held and naturally deflated. It reported 115/94 mmHg,
  84 BPM, `valid=1`; capture n=2313, dropped=0, duration=57800 ms, nominal
  interval=25 ms. Calculation work/wall/max-step was 1673/2406/31 ms. The host
  then completed `vent` -> fresh low pressure -> `seal`, confirmed safe pins,
  zero ADS errors/recoveries, and restored target 50. Log:
  `tmp/linkpad_standard_20261027-225743.ndjson`. This is simulator bench evidence,
  not clinical or ISO 81060-2 evidence.
- The subsequent export attempt did not reach the device: every bridge write ACK
  returned `Serial port not connected`, the five-second snapshot had zero samples,
  and no export records were received. Consequently the previously safe sealed
  state remains the last device-confirmed state, but this run has no `/2` export,
  production-C replay, or post-calculation/export stack measurement. Do not count
  it as a waveform-export or dynamic stack-watermark pass. Evidence:
  `tmp/capture_export_20261028-111017.ndjson`.
- Host suite: 77/77 passed. Keil static budget: RAM 63312/65536 B, headroom
  2224 B, known stack peak 1304 B plus 1024 B reserve within the 4096 B stack.
  These static checks complement the subsequently completed target high-water
  observation for the exercised Standard BP, calculation and export path.
- Wiring and next safe validation procedure are recorded in
  `stack_watermark_2026-10-27.md`. Resume with a connected serial bridge, first
  verify VALID/ONLINE, safe pins and fresh near-zero pressure; export this
  retained capture, run strict decoding and production-C replay, then query stack
  twice. Require unsaturated watermark with >=1024 B free for this exercised
  path. The planned reference matrix was later adjusted during live acquisition;
  see the dated results below.

## 2026-10-28 Reconnected waveform export and dynamic stack check

- The serial bridge returned after the earlier disconnect. The first read-only
  preflight confirmed IDLE, calibration VALID, ADS ONLINE, fault NONE, safe pins,
  146 fresh near-zero pressure records, and stack baseline 1448 used / 2648 free.
  At that point capture n=0, so the earlier 115/94 round could not be exported.
- Repeated the non-human Standard BP run with the same External Cuff, 120/80 mmHg
  and 80 BPM settings. It reached 150.7 mmHg, held, and naturally deflated to
  completion. Result: 117/86 mmHg, 75 BPM, valid=1; capture n=2305,
  dropped=0, duration=57600 ms, interval=25 ms. Calculation work/wall/max-step
  was 1664/2401/30 ms. Log: `tmp/linkpad_standard_20261028-113503.ndjson`.
- Closeout completed `vent` -> consecutive fresh low pressure -> `seal`; pins
  returned PC0/PC1 LOW, PC8 HIGH, pump OFF. The simulator had stopped naturally
  at zero external pressure; no panel Stop was needed. Fault USER_STOP is the
  expected host safety-closeout latch. ADS errors/recoveries remained zero.
- A first export preflight immediately after closeout saw residual 3.2 mmHg and
  correctly refused export. Its cleanup vented again and sealed only after fresh
  zero pressure. A second preflight then passed with 92 fresh samples at 0.0 mmHg;
  the following `/2` export completed with 2305 points, one valve row, features,
  and end hash `2425960936`. Logs:
  `tmp/capture_export_20261028-113643.ndjson` (safe refusal/cleanup) and
  `tmp/capture_export_20261028-113752.ndjson` (complete export).
- Strict offline decode and production-C replay passed. All 2304 adjacent MCU
  intervals were exactly 25 ms. Replay returned 117/86/75, valid=1, MAP index
  778; envelope and smoothed-envelope errors were zero, envelope and feature
  bits matched, and validity matched. Valve aggregate: 289 pulses at 200 ms,
  on-time 1..7 ms, two >=5 mmHg steps. Artifacts:
  `tmp/capture_export_20261028-113752.csv`,
  `tmp/capture_export_20261028-113752.verified.ndjson`, and
  `tmp/capture_export_20261028-113752.replay.json`.
- Two post-calculation/export stack readings both reported used=1536,
  free=2560, reserved=4096, saturated=0. This includes the Standard BP
  acquisition, cooperative calculation, export and subsequent diagnostic
  command path exercised in this image. Static stack budget also passes. It is
  target evidence for this exercised path, not proof of all interrupt/runtime
  paths. Logs: `tmp/stack_watermark_post_export_01_20261028.ndjson` and
  `tmp/stack_watermark_post_export_02_20261028.ndjson`.
- The first attempt at full capture export in the previous continuation was
  blocked by serial disconnect and the board reset cleared its buffer; it was
  not counted. The reconnected repeat above supplies the required complete
  waveform and dynamic stack evidence. Follow-up reference values were selected
  on the BP Pump 2 interface during live acquisition; actual settings and
  outcomes are recorded below. Never assume an undocumented raw protocol.

## 2026-10-28 Standard BP at 100/65 mmHg

- User set BP Pump 2 to 100/65 mmHg, External Cuff, 80 BPM. The non-human run
  reached 152.0 mmHg, held, and naturally deflated. Capture n=2233,
  dropped=0, duration=55800 ms, interval=25 ms. Algorithm reported calculation
  failure: MAP feature 80.4 mmHg, DBP feature 80.5 mmHg, so the DBP > MAP
  validity gate rejected the result. No valid SBP/DBP/pulse was published.
  Calculation work/wall/max-step was 1618/2333/31 ms. Log:
  `tmp/linkpad_standard_20261028-114507.ndjson`.
- Closeout completed `vent` -> fresh low pressure -> `seal`; final pins were
  PC0/PC1 LOW, PC8 HIGH, pump OFF. ADS errors/recoveries remained zero.
- A first export attempt failed the conservative host preflight at residual
  pressure 3.2 mmHg and ran its vent/low-pressure/seal cleanup. After the
  pressure stream settled near zero, export succeeded: 2233-point `/2`,
  `calc=3`, hash `4135543340`, 280 valve pulses at 200 ms, and three >=5 mmHg
  adjacent steps. Strict decode and production-C replay preserved invalidity,
  both feature arrays and feature bits; envelope/smooth maximum error was zero.
  All 2232 tick intervals were 25 ms. Artifacts:
  `tmp/capture_export_20261028-114718.ndjson`, `.csv`, `.verified.ndjson`, and
  `.replay.json`.
- Post-export stack was used=1536, free=2560, reserved=4096,
  saturated=0. ADS errors/recoveries were zero and pins were safe.
  `tmp/stack_watermark_post_100_65_20261028.ndjson`.
- This is a retained invalid simulator waveform, not a BP result or accuracy
  point. Preserve the existing validity gate and record it as a boundary sample;
  do not tune the algorithm from this single result. The next requested matrix
  point was subsequently changed by the user to 150/100 mmHg at 80 BPM, External
  Cuff.

## 2026-10-28 Standard BP at 150/100 mmHg

- The first user-directed non-human External Cuff run at 150/100 mmHg, 80 BPM
  reached 151.9 mmHg and naturally deflated. Capture n=2377, dropped=0,
  duration=59400 ms, interval=25 ms. Algorithm rejected the result: MAP feature
  95.1 mmHg, DBP feature 95.7 mmHg, so DBP exceeded MAP by 0.6 mmHg. Calculation
  work/wall/max-step was 1721/2485/32 ms. Log:
  `tmp/linkpad_standard_20261028-115054.ndjson`.
- After pressure remained 3.5..3.7 mmHg in the sealed state, an explicit second
  `vent` produced 100/100 fresh samples at 0.0 mmHg; then `seal` was applied.
  The first export preflight refusal is retained in
  `tmp/capture_export_20261028-115410.ndjson`; after verified zero-pressure
  closeout the `/2` export completed with 2377 points and hash `4277092157`.
  Valve aggregate: 298 pulses, 200 ms period, eight >=5 mmHg steps. Strict
  decode and production-C replay reproduced the invalid result and both feature
  arrays; envelope/smooth maximum errors were zero and validity matched.
  Artifacts: `tmp/capture_export_20261028-115410.csv`,
  `.verified.ndjson`, and `.replay.json`.
- A second run at the same reference reached 150.7 mmHg and naturally deflated.
  It produced a valid 120/94 mmHg, 84 BPM result with capture n=2241,
  dropped=0, duration=56000 ms, interval=25 ms. Calculation
  work/wall/max-step was 1623/2355/31 ms. Log:
  `tmp/linkpad_standard_20261028-115545.ndjson`.
- The valid repeat closed out via `vent` -> fresh low pressure -> `seal`. Its
  `/2` export passed with 2241 points, hash `274891698`, 281 valve pulses at
  200 ms and two >=5 mmHg steps. Production-C replay returned 120/94/84 valid;
  all ticks were 25 ms, envelope and feature bits matched, and maximum envelope
  errors were zero. Artifacts: `tmp/capture_export_20261028-115823.csv`,
  `.verified.ndjson`, and `.replay.json`.
- Both post-export checks reported stack used=1536, free=2560, reserved=4096,
  saturated=0. ADS errors/recoveries were zero and actuator pins were safe.
  Logs: `tmp/stack_watermark_post_150_100_20261028.ndjson` and
  `tmp/stack_watermark_post_150_100_repeat_20261028.ndjson`.
- At this reference, one of two rounds failed only because DBP feature was
  slightly above MAP; the other yielded a valid result. Keep both labeled as
  captured simulator cases and do not alter the current validity gate from this
  small sample.
- A further run had already begun at 150/100 when the user clarified the next
  requested point should be 100/65. It was allowed to finish without changing
  the active measurement: 150.5 mmHg reached, capture n=2289/dropped0/57200ms,
  then invalid with MAP=95.4 and DBP feature=96.0. Closeout reached fresh zero,
  sealed the valve, and the `/2` capture was exported/replayed: hash258344143,
  all ticks25ms, invalidity/features bit-equal, envelope errors0. Files:
  `tmp/linkpad_standard_20261028-120331.ndjson`,
  `tmp/capture_export_20261028-120531.ndjson`, `.csv`, `.verified.ndjson`,
  `.replay.json`.
- The user then confirmed the BP Pump 2 reference was 100/65. That run reached
  152.2 mmHg, held, naturally deflated, and captured n=2217/dropped0/55400ms.
  It was invalid: MAP feature=97.5 mmHg, DBP feature=98.2 mmHg; work/wall/max
  step=1606/2321/31 ms. A first closeout left residual 3.5..3.6 mmHg; an explicit
  `vent` followed by 100 fresh est=0 samples, then `seal`, restored closed zero
  pressure. `/2` export hash=2916754868, valve pulses=278, >=5mmHg steps=4.
  Strict decode and production-C replay matched invalidity, features and arrays;
  all ticks=25ms, envelope/smooth errors=0. Post-export stack=1536 used / 2560
  free, unsaturated. Files: `tmp/linkpad_standard_20261028-120655.ndjson`,
  `tmp/capture_export_20261028-120941.ndjson`, `.csv`, `.verified.ndjson`,
  `.replay.json`, `tmp/stack_watermark_post_100_65_repeat2_20261028.ndjson`.
- A second 100/65 capture then reached 151.9 mmHg and completed with a valid
  121/71 mmHg, 56 BPM result. Capture n=2379, dropped=0, duration=59450 ms,
  interval=25 ms; calculation work/wall/max-step was 1717/2487/31 ms. The first
  export check found ~3.5 mmHg residual, so the host vented again, observed 100
  fresh est=0 samples, sealed, and only then exported. `/2` export hash was
  `3025252081`, with 298 pulses at 200 ms and one >=5 mmHg step. Strict decoder
  and production-C replay matched 121/71/56 valid, with exact 25 ms ticks,
  equal feature/envelope bits and zero envelope/smooth error. Post-export stack
  was used=1536/free=2560/reserved=4096/saturated=0. ADS errors/recoveries=0;
  pins were safe. Artifacts: `tmp/linkpad_standard_20261028-121243.ndjson`,
  `tmp/capture_export_20261028-121553.ndjson`, `.csv`, `.verified.ndjson`,
  `.replay.json`, and `tmp/stack_watermark_post_100_65_repeat3_20261028.ndjson`.
- Across the three 100/65 runs recorded on this date, two had DBP features just
  above MAP (97.5/98.2 and 80.4/80.5) and were rejected; the later complete
  waveform returned valid 121/71/56. Keep all three outcomes. This small
  simulator batch is not clinical accuracy evidence and does not justify
  changing the algorithm or validity check.

## 2026-10-28 Standard BP at 150/100 mmHg: latest round

- With the user-confirmed BP Pump 2 setting of 150/100 mmHg, External Cuff,
  80 BPM, this non-human run reached 151.4 mmHg, held and naturally deflated.
  Result was valid 121/73 mmHg, 84 BPM. Capture n=2242, dropped=0,
  duration=56025 ms, interval=25 ms; calculation work/wall/max-step was
  1621/2357/31 ms. Log: `tmp/linkpad_standard_20261028-122857.ndjson`.
- The first export preflight saw residual pressure and safely vented again. After
  100 fresh near-zero samples, valve2 was sealed and the retained capture export
  passed: `/2`, 2242 points, hash `2309702183`, 281 pulses at 200 ms and one
  >=5 mmHg step. Strict decode and production-C replay returned 121/73/84
  valid; all MCU ticks were 25 ms, feature/envelope bits matched, and envelope
  and smoothed-envelope maximum error were zero. Artifacts:
  `tmp/capture_export_20261028-123230.ndjson`, `.csv`, `.verified.ndjson`, and
  `.replay.json`.
- Post-export stack reported used=1536, free=2560, reserved=4096,
  saturated=0. Calibration remained VALID, ADS errors/recoveries were zero,
  and actuator pins were PC0/PC1 LOW, PC8 HIGH, pump OFF. Log:
  `tmp/stack_watermark_post_150_100_20261028-123230.ndjson`.

## 2026-10-28 offline comparison of retained Standard BP waveforms

- Read-only comparison of the seven user-labeled 100/65 and 150/100 `/2`
  CSV exports and their exact production-C replay reports. The reference
  settings came from the user's BP Pump 2 panel confirmations; neither the
  serial export nor the replay contains a machine-readable simulator setting.
  Every waveform had 25 ms ticks and zero dropped samples. Values below are
  *raw feature pressures*, before the firmware's fixed -10/-5 mmHg offsets.

  | User label | Export ID | Deflate start | MAP feature | DBP feature | MAP-to-DBP time | Replay |
  | --- | --- | ---: | ---: | ---: | ---: | --- |
  | 100/65 | 114718 | 135.7 | 80.37 | 80.45 | 0.725 s | invalid |
  | 100/65 | 120941 | 136.2 | 97.46 | 98.19 | 0.400 s | invalid |
  | 100/65 | 121553 | 136.6 | 81.74 | 76.29 | 1.650 s | 121/71, 56 bpm |
  | 150/100 | 115410 | 134.7 | 95.13 | 95.73 | 0.400 s | invalid |
  | 150/100 | 115823 | 133.8 | 99.45 | 99.01 | 0.575 s | 120/94, 84 bpm |
  | 150/100 | 120531 | 134.0 | 95.39 | 96.02 | 0.450 s | invalid |
  | 150/100 | 123230 | 134.3 | 85.99 | 78.68 | 1.325 s | 121/73, 84 bpm |

- In all four invalid rounds, the first three-sample 60%-of-peak DBP
  crossing occurs only 0.400-0.725 s after the selected MAP sample. Net
  pressure *rises* 0.09-0.72 mmHg between these indices, with 6-11 individual
  rising 25 ms steps. This directly explains the `DBP > MAP` validity failure:
  the algorithm searches forward in time but assumes pressure strictly falls.
  The immediate cause of the reversals cannot be isolated from these exports
  alone; pulsation and valve modulation both remain possible contributors.
- The 32-sample (0.8 s) smoothed envelope can cross the DBP threshold within
  one simulated 80 bpm beat. In 114718, 115823 and 121553 it subsequently
  rises above that threshold during the next 2 s (73, 68 and 76 samples,
  respectively). Thus even a *valid* pressure ordering does not prove that the
  crossing describes the falling side of a multi-beat oscillometric envelope.
- The production MAP search is hard-limited to 80-100 mmHg. A simple
  `(SBP+2*DBP)/3` estimate for the two simulator labels is about 76.7 and
  116.7 mmHg, respectively; this formula is context, not a verified BP Pump 2
  MAP setting. The bounds exclude both estimates. The 100/65 run 114718 picks
  80.37 near the lower edge; the 150/100 run 115823 picks 99.45 near the upper
  edge. Therefore the current feature extractor and fixed offsets cannot be
  used to compare numerical SBP/DBP accuracy across these two settings.
- At the existing `target 150`, the retained deflation begins at only
  133.8-136.6 mmHg after the hold. No 150/100 waveform contains a deflating
  high-pressure region above the labeled 150 mmHg SBP. The acquisition buffer
  holds 2800 samples. The firmware aims for 3 mmHg/s, but the four measured
  mean deflation rates are only 2.016-2.131 mmHg/s. A previous rough 3 mmHg/s
  projection understated the capacity risk; the measured-rate projection is:

  | Export ID | Observed n | Rate mmHg/s | n at target 170 | n at 180 | n at 190 |
  | --- | ---: | ---: | ---: | ---: | ---: |
  | 115410 | 2377 | 2.016 | 2774 | 2972 | 3170 |
  | 115823 | 2241 | 2.130 | 2617 | 2805 | 2992 |
  | 120531 | 2289 | 2.081 | 2673 | 2866 | 3058 |
  | 123230 | 2242 | 2.131 | 2617 | 2805 | 2993 |

  The projection assumes the same pressure loss during hold and the same mean
  rate after changing the target; it is not a capacity guarantee. At 170 the
  worst observed pattern leaves only 26 samples; at 180 all four projections
  exceed capacity. Do not raise the target for another 150/100 capture until
  the acquisition budget and fail-safe behavior are redesigned and tested.
  Preserve the current overflow fault/vent behavior. The three parallel arrays
  use 20 bytes per extra point (`BP_Sample_t` 12 + two float envelopes 8).
  The worst target190 projection needs 370 more points than current capacity,
  or about 7400 additional RAM bytes, exceeding the last Keil static headroom
  of 2224 bytes. Simply increasing `BP_ALGO_MAX_SAMPLES` cannot fit that case.
- Next engineering step: test host-only beat isolation against all retained
  waveforms, including invalid cases, while preserving the raw captures and
  rejection labels. Independently size and test the capture-duration budget
  before any higher-target 150/100 acquisition. Do not change firmware
  thresholds, compensation, calibration, or physical settings based on this
  small simulator batch. This is simulator evidence, not clinical or ISO
  81060-2 accuracy evidence.

## 2026-10-28 host beat diagnostic and measured-rate budget

- Added `blood pressure monitor/tools/bp_beat_analysis.py`. It reuses the strict
  `bp_capture.decode()` checksum/order validator and only reads completed
  exports. NumPy and SciPy are required on the host. Example (repository root):

  ```powershell
  python 'blood pressure monitor/tools/bp_beat_analysis.py' tmp/capture_export_20261028-115410.verified.ndjson --bpm 80 --current-target 150 --future-targets 170 180 190
  ```

- It finds local peaks of the existing smoothed voltage envelope, excludes the
  first 2 s and last 15 samples, and checks peak spacing against the declared
  80 bpm. All seven saved 100/65 and 150/100 waveforms fail the 70% cadence
  gate: only 4.3%-26.7% of detected interpeak gaps lie within 20% of 750 ms;
  median gaps are 1.44-2.33 s. The tool therefore reports
  `cadence_unreliable` and **suppresses** MAP/SBP/DBP candidates for these
  waveforms. This is a failed beat-isolation prototype, not a new BP algorithm
  or proof that the simulator itself skipped beats. Synthetic regular beats
  pass the gate and produce diagnostic candidates.
- Three focused host tests pass, covering synthetic regular and wrong-cadence
  signals plus capacity overflow projection. The seven real strict exports
  were also run through the CLI and all candidates were suppressed. No
  firmware, threshold, compensation, calibration or actuator code was changed.
  No wiring, power or ground changes are needed: this tool runs on saved files
  from the existing USART3/CH340 export path. No Keil compile/download or
  pneumatic run is required for this validation. Before any later non-human
  high-pressure test, retain the established calibrated zero/safe-pin preflight,
  `vent -> fresh near-zero -> seal` closeout, and the current overflow vent.
- Full host suite after the host-only change: 80/80 passed. The next physical
  150/100 capture needs a bounded storage/acquisition design that preserves
  the intended pressure coverage, followed by firmware RAM/stack, Keil and
  non-human safety gates. Merely raising the target or buffer constant is not
  supported by this evidence.

## 2026-10-28 bounded 3300-point software image

- Implemented `CAPTURE_COMPACT_20261028` with private 8-byte pressure/voltage
  points, byte intersample tick deltas, and exact public uint32 tick recovery.
  Capacity is 3300 points (82.475 s between first and last at nominal 25 ms).
  Zero or >255 ms later gaps fail the entire capture; existing callers use the
  SAMPLE_OVERFLOW emergency vent. Float32 input bits, envelope arithmetic,
  valve timing, calibration, pressure limits and `/2` fields were not changed.
- Full real-C/host suite: 82/82 pass, including 2000/2800/3300 exports,
  irregular 1/255 ms ticks, uint32 rollover, nonrepresentable-gap emergency
  vent and retained old `/2` strict decode. New source is registered in the
  existing Keil project. Keil V6.22 Rebuild: 0 errors/0 warnings; RAM
  63416/65536 B (2120 B headroom), stack4096 B, known peak1304 B +1024 B
  reserve. HEX SHA256:
  `537B9FFD10ABD21E39EC51CF04EC2E97EE56E0AEADE32B8DA0CF215CE0F6155D`.
- Export begin now rejects `dropped_samples != 0`, including a bad tick gap;
  the real-C exporter lifecycle test verifies that no incomplete transfer starts.
- No flash, calibration write, pump, valve or BP Pump 2 operation occurred.
  Board runtime stack/export timing and any higher-pressure sample budget
  remain unverified. Wiring, power/ground checks, Keil download/calibration
  recovery, low-pressure non-human gate, serial observations and vent/seal
  closeout are in `capture_compact_2026-10-28.md`.

## 2026-10-28 compact image download and low-pressure board gate

- The separately authorized Keil download completed at 16:26:50: Full Chip
  Erase Done, Programming Done, Verify OK, Application running. Log:
  `tmp/compact_flash_20261028.log`; HEX SHA256 remains
  `537B9FFD10ABD21E39EC51CF04EC2E97EE56E0AEADE32B8DA0CF215CE0F6155D`.
  Board capture diagnostics now report capacity3300. Full-chip erase cleared
  calibration; restored only `cal write 82.326 -19.887`, with written+verified
  and independent VALID readback82.326/-19.89. Evidence:
  `tmp/compact_postflash_uncal_20261028.ndjson` and
  `tmp/compact_postflash_cal_20261028.ndjson`.
- Before the low-pressure exercise, a five-second bridge snapshot contained
  100 fresh samples, all est0.0mmHg. The existing non-human setup was retained.
  Ran one default `tmp/linkpad_lowpressure_check.py` exercise (target50, host
  stop trigger20mmHg; no inflation retry). Active-inflation stop was confirmed;
  observed serial peak32.2mmHg, below target. STOP reported
  PC0 LOW/PC1 HIGH/PC8 HIGH. Script exited0 after stop -> vent -> ten fresh
  <=1mmHg samples -> seal; final PC0/PC1 LOW, PC8 HIGH, pump OFF. USER_STOP
  is the expected test fault, not a spontaneous pressure/sensor fault. Log:
  `tmp/linkpad_lowpressure_20261028-163100.ndjson`.
- Independent post-test five-second check passed: 145 fresh near-zero samples,
  calibration VALID, ADS ONLINE, manual OFF, safe pins, errors0/recoveries0.
  Stack used1384/free2712/reserved4096/saturated0. Log:
  `tmp/compact_postlowpressure_20261028.ndjson`.
- The subsequent120/80 baseline and user-authorized single target190
  non-human run, including `/2` replay and post-export stack evidence, are
  recorded below.

## 2026-10-28 compact image baseline, export and runtime stack

- User confirmed External Cuff120/80mmHg,80bpm/non-human setup. Ran one
  `tmp/linkpad_lowpressure_check.py --standard`, exit0: target150 reached151.8,
  hold then natural deflation; n2161/capacity3300/dropped0/span54000ms.
  BP106/80,84bpm valid1, raw feature MAP86.2/SBP116.3/DBP85.8mmHg.
  Calculation work1559/wall2264/max_step31ms. Completed vent -> fresh low
  samples -> seal; target restored50. Acquisition log:
  `tmp/linkpad_standard_20261028-163326.ndjson`.
- First export preflight refused before sending `capture export`: pressure
  rebounded after sealing to3.1-3.5mmHg, outside the host <=1mmHg gate. The
  script safely repeated stop/vent, observed fresh zero samples, then sealed.
  Independent five-second snapshot subsequently had100 samples0.4-0.6mmHg.
  Failed preflight evidence: `tmp/capture_export_20261028-163445.ndjson`.
  No new inflation, calibration change or relaxed acceptance threshold.
- Retried export only, exit0. Complete `/2` has2161points, one valve row,
  features and end hash1601732005; firmware CAPTURE_COMPACT_20261028.
  Strict decoder and same-source production C replay passed; exact25ms ticks,
  envelope bits/feature bits/validity equal, both max errors0. Valve evidence:
  271pulses,200ms periods,1-5ms on-time, seven >=5mmHg steps in phase0-24ms.
  Raw and derived artifacts: `tmp/capture_export_20261028-163539.ndjson`,
  `.verified.ndjson`, `.csv`, `.replay.json`.
- Two post-export stack checks passed, both used1536/free2560/reserved4096,
  saturated0. Each independently checked fresh near-zero pressure, VALID
  calibration, ADS ONLINE, PC0/PC1 LOW, PC8 HIGH,pump OFF; ADS errors0 and
  recoveries0. USER_STOP remains the intentional cleanup fault. Evidence:
  `tmp/compact_postexport_stack1_20261028.ndjson` and
  `tmp/compact_postexport_stack2_20261028.ndjson`.
- Board baseline/storage/export gates passed, not simulator accuracy: output
 106/80 differs from the120/80 reference, consistent with existing feature
  extractor limitations. No firmware edits or flash occurred in these board
  runs.
- Offline `bp_beat_analysis.py` on the verified new export found
  `cadence_unreliable` (12 candidate peaks, median gap3050ms, cadence fraction0),
  so it suppressed new BP candidates. Its measured deflation rate is2.226mmHg/s
  from134.99 to14.8mmHg over54s; target170/180/190 projects2520/2700/2880
  samples (remaining780/600/420) for this particular pattern. Four archived
  150/100 patterns project as few as130 remaining at190. The local official
  BP Pump 2 operator manual PN2196592 lists0..400mmHg pressure-measurement
  range, but current cuff/tubing/fitting ratings are not recorded. The user
  later authorized one bounded non-human190 run; that run and its limits are
  recorded below.

## 2026-10-28 bounded 190 mmHg non-human acquisition

- User confirmed BP Pump2 Standard150/100,80bpm,External Cuff and accepted a
  single target190 non-human run. The pictured standard electronic cuff is
  labelled for arm circumference22-32cm; no pressure rating is visible. No
  claim is made that ClassI status or the BP Pump2 instrument range establishes
  the cuff/tubing/fitting pressure rating.
- Extended `tmp/linkpad_lowpressure_check.py` with fixed `--target190` mode:
  host pressure ceiling205mmHg, acquisition timeout105s, pressure freshness and
  firmware safety-fault checks, exactly one start/no retry, fail-safe
  stop/vent/low-pressure/seal cleanup, and target restoration to50. Added fake
  bridge tests for successful complete capture with invalid BP and over-ceiling
  abort/cleanup. `py_compile` passed and `tmp/test_linkpad_calc_stop.py` passed
 8/8. No firmware source, calibration or algorithm was changed.
- Preflight: five-second snapshot100 fresh samples at0.0mmHg; calibration
 82.326/-19.89 VALID, ADS ONLINE, manual OFF, PC0/PC1 LOW,PC8 HIGH,pump OFF,
  ADS errors0/recoveries0. Target reached190.4mmHg and stopped automatically.
  Natural deflation ended with `n=3153 capacity=3300 dropped=0 duration=78800ms
  interval=25ms`; capture margin147 points. Calculation work2267ms/wall3292ms,
  max_step33ms; board BP154/90,75bpm valid1. Log:
  `tmp/linkpad_target190_20261028-170050.ndjson`.
- First post-seal observation rebounded to3.6-3.9mmHg, so export was held.
  Repeated vent -> fresh0.0 samples -> seal, then observed another five seconds
  at0.0 before export. No re-inflation. The accepted export preflight observed
 92 fresh near-zero samples.
- Complete `/2` export contained3153 points, valve395 pulses/200ms period/
  on-time1-6ms/12 >=5mmHg steps, features and end hash3067838985. Strict decode
  and production-C replay passed with25ms ticks, equal envelope/feature bits,
  equal validity and zero max errors. Replay returned154/90,75, matching the
  board. Artifacts: `tmp/capture_export_20261028-170426.ndjson`,
  `.verified.ndjson`, `.csv`, `.replay.json`.
- Two separate post-export stack checks both used1536/free2560/reserved4096,
  saturated0; ADS errors0/recoveries0, calibration VALID, fresh near-zero,
  PC0/PC1 LOW,PC8 HIGH,pump OFF. Logs:
  `tmp/compact_target190_stack1_20261028.ndjson` and
  `tmp/compact_target190_stack2_20261028.ndjson`.
- Host beat analysis reports `cadence_unreliable`,28 candidate peaks, median
  interpeak2300ms and cadence fraction0.148 at configured80bpm. Therefore this
  run proves one compact-image acquisition and replay, not an accurate BP
  reading or an80bpm waveform. The full capture used95.5% of3300 points and
  left147; no repeat190 or higher target should be scheduled until the connected
  component ratings and a repeat-capacity budget are verified.

## 2026-10-28 non-human 100/65 capture with invalid BP

- User confirmed Standard100/65,80bpm,External Cuff and the existing non-human
  setup. Preflight snapshot:100 fresh samples at0.0mmHg; calibration VALID,
  ADS ONLINE, manual OFF, safe pins, ADS errors0/recoveries0. Firmware target150
  reached151.4, held and naturally deflated. Capture `n=2097 capacity=3300
  dropped=0 duration=52400ms interval=25ms`. Calculation failed with
  `DBGFAIL n=2097 map=782(86.3) sbp=1(122.9) dbp=1(86.6)`; the DBP feature is
  above MAP, so no BP result was accepted. Calculation work1514ms/wall2185ms,
  max_step30ms. The acquisition script correctly returned failure for BP
  validity, then completed stop/vent/low-pressure/seal and restored target50.
  Raw log: `tmp/linkpad_standard_20261028-171421.ndjson`.
- The first post-seal snapshot rebounded to3.7mmHg. Repeated vent -> 101 fresh
  samples at0.0 -> seal, then another five-second snapshot of100 samples at
 0.0mmHg. Export preflight passed with93 fresh near-zero samples; no reinflation.
- Full `/2` export has2097 points, `calc=3`, valve263 pulses at199-200ms,
  on-time1-5ms, zero >=5mmHg steps, end hash2790072925. Strict decode and
  production-C replay passed; ticks25ms, envelope and feature bits equal,
  validity equal(false), max errors0. Replay deliberately publishes valid0 and
  zeros SBP/DBP/Pulse. Artifacts: `tmp/capture_export_20261028-172032.ndjson`,
  `.verified.ndjson`, `.csv`, `.replay.json`.
- Two post-export checks both used1536/free2560/reserved4096/saturated0 with
  fresh near-zero pressure, calibration VALID, safe pins, pump OFF, ADS errors0
  and recoveries0. Beat analysis reports `cadence_unreliable` (18 peaks,
  median2100ms, cadence fraction0 at80bpm). Keep this waveform as an invalid
  research sample; it is not a successful BP result. The observed deflation
  rate is2.283mmHg/s and the capture leaves1203/3300 points unused. Stack logs:
  `tmp/compact_100_65_stack1_20261028.ndjson` and
  `tmp/compact_100_65_stack2_20261028.ndjson`.
- A second independent start at the same100/65 setup did not inflate: serial
  pressure remained0.0mmHg and firmware reported `[Safety] Manual pump timeout;
  emergency vent`. The one start attempt was not retried. Cleanup completed
  stop -> vent -> fresh near-zero -> seal and restored target50. No capture was
  produced. Follow-up snapshot:101 fresh samples at0.0mmHg; calibration VALID,
  ADS ONLINE, errors0/recoveries0, PC0/PC1 LOW,PC8 HIGH,pump OFF. Stack remains
  used1536/free2560/reserved4096/saturated0. Log:
  `tmp/linkpad_standard_20261028-172502.ndjson`;
  independent check: `tmp/compact_100_65_timeout_postcheck_20261028.ndjson`.
  Since the next round could not start, confirm BP Pump2 is back on Standard
  100/65,80bpm,External Cuff and its pulse/ready indication before another
  inflation; no panel Stop request is needed.
- User confirmed the100/65/External Cuff/ready state. A bounded target50
  diagnostic then passed: observed peak26.3mmHg, host stop at20, safe
  stop/vent/fresh low/seal, final pump OFF and sealed pins. It establishes that
  this low-pressure path could inflate, but does not identify why the preceding
  target150 run stayed at zero. No capture was expected. Log:
  `tmp/linkpad_lowpressure_20261028-173104.ndjson`.
- One new independent target150 run then reached150.8mmHg, held and naturally
  deflated. Capture `n=2177 capacity=3300 dropped=0 duration=54400ms
  interval=25ms`; board result118/68,56bpm valid1. Calculation work1571ms/
  wall2274ms/max_step31ms. Log:
  `tmp/linkpad_standard_20261028-173235.ndjson`.
- After seal, a five-second snapshot showed3.3-3.4mmHg. Repeated vent -> 100
  fresh0.0 samples -> seal, then another five-second100-sample snapshot at0.0.
  Export preflight passed with92 fresh near-zero samples. Complete `/2` export
  hash2604842734 recorded2177 points, calc2,273 valve pulses at200ms,
  on-time1-5ms, three >=5mmHg steps and terminal end. Strict decode and
  production-C replay passed: all ticks25ms, envelope/feature bits and validity
  equal, max errors0; replay returned118/68/56. Artifacts:
  `tmp/capture_export_20261028-173648.ndjson`, `.verified.ndjson`, `.csv`,
  `.replay.json`.
- Two post-export stack checks both used1536/free2560/reserved4096,
  saturated0, with fresh near-zero, VALID calibration, ADS ONLINE, errors0/
  recoveries0, PC0/PC1 LOW, PC8 HIGH, pump OFF. Host beat analysis remains
  `cadence_unreliable` at80bpm (20 peaks, median1525ms, cadence fraction0.105).
  Retain the waveform, but do not treat the firmware output or label as accuracy
  evidence. Stack logs: `tmp/compact_100_65_stack1b_20261028.ndjson` and
  `tmp/compact_100_65_stack2b_20261028.ndjson`.

## 2026-10-28 additional non-human 100/65 capture

- BP Pump 2 remained on Standard 100/65, 80 bpm, External Cuff. The firmware
  target was 150 mmHg; it reached 150.9 mmHg, stopped the pump automatically,
  held, then completed natural deflation. Capture: `n=1921 capacity=3300
  dropped=0 duration=48000ms interval=25ms`. Board result was 120/87, 56 bpm,
  `valid=1`; this differs from the simulator setting and is not accuracy
  evidence. Calculation work1387ms/wall1996ms/max_step30ms. Raw log:
  `tmp/linkpad_standard_20261028-174910.ndjson`.
- After initial seal, pressure rebounded to3.4-3.6mmHg. Repeated
  `vent` -> 100 fresh0.0 samples -> `seal`, then observed a further five seconds
  and100 samples at0.0mmHg. Export preflight passed with93 fresh near-zero
  samples; no new inflation occurred. Final five-second snapshot after checks
  also contained100 samples at0.0mmHg.
- Complete `/2` export hash1162268757 contains1921 points, `calc=2`, 241 valve
  pulses at200ms, on-time1-6ms, one >=5mmHg pressure step and a terminal end.
  Strict decode and production-C replay passed: ticks25ms, envelope and feature
  bits equal, validity equal, max errors0; replay returned120/87/56. Artifacts:
  `tmp/capture_export_20261028-175901.ndjson`, `.verified.ndjson`, `.csv`,
  `.replay.json`.
- Two independent post-export checks both reported1536 used/2560 free/4096
  reserved, saturated0, pattern `0xA5A5A5A5`; VALID calibration, ADS errors0/
  recoveries0, PC0/PC1 LOW, PC8 HIGH, pump OFF, and fresh low pressure. Logs:
  `tmp/compact_100_65_stack1c_20261028.ndjson` and
  `tmp/compact_100_65_stack2c_20261028.ndjson`.
- Host beat analysis at configured80bpm reports `cadence_unreliable` (16 peaks,
  median interpeak1475ms, cadence fraction0.067); retain as research waveform,
  not BP or pulse accuracy evidence.
- A second independent target150 run reached151.2mmHg, stopped the pump
  automatically, and completed natural deflation. Capture `n=2009 capacity=3300
  dropped=0 duration=50200ms interval=25ms`; board result119/79,56bpm, valid1.
  Calculation work1449ms/wall2106ms/max_step30ms. Raw log:
  `tmp/linkpad_standard_20261028-180227.ndjson`.
- Initial post-seal snapshot rebounded to3.1-3.4mmHg, so the capture was not
  exported yet. Repeated `vent` -> 100 fresh0.0 samples -> `seal`; a further
  five-second post-seal snapshot yielded101 samples at0.0mmHg. Export preflight
  then passed with93 fresh near-zero samples, with no reinflation.
- Complete `/2` export hash129349324 contains2009 points, `calc=2`, 252 valve
  pulses at200ms, on-time1-5ms, zero >=5mmHg steps and a terminal end. Strict
  decode and production-C replay passed: ticks25ms, envelope and feature bits
  equal, validity equal, max errors0; replay returned119/79/56. Artifacts:
  `tmp/capture_export_20261028-180524.ndjson`, `.verified.ndjson`, `.csv`,
  `.replay.json`.
- Two independent post-export checks both reported1536 used/2560 free/4096
  reserved, saturated0, pattern `0xA5A5A5A5`; VALID calibration, ADS errors0/
  recoveries0, PC0/PC1 LOW, PC8 HIGH, pump OFF, and fresh low pressure. Logs:
  `tmp/compact_100_65_stack1d_20261028.ndjson` and
  `tmp/compact_100_65_stack2d_20261028.ndjson`.
- Host beat analysis at configured80bpm reports `cadence_unreliable` (21 peaks,
  median interpeak1850ms, cadence fraction0.25); retain as research waveform,
  not BP or pulse accuracy evidence.

## 2026-10-28 third non-human 100/65 capture

- BP Pump 2 remained on Standard100/65,80bpm,External Cuff. Target150 reached
  151.1mmHg and the pump stopped automatically before natural deflation. Capture
  `n=2057 capacity=3300 dropped=0 duration=51400ms interval=25ms`; board result
  113/86,56bpm, valid1. Calculation work1484ms/wall2141ms/max_step31ms. Raw
  log: `tmp/linkpad_standard_20261028-180730.ndjson`.
- Initial post-seal snapshot rebounded to3.0-3.5mmHg. Repeated
  `vent` -> 100 fresh0.0 samples -> `seal`; a further five-second post-seal
  snapshot yielded101 samples at0.0mmHg. Export preflight passed with92 fresh
  near-zero samples, without reinflation.
- Complete `/2` export hash1210925668 contains2057 points, `calc=2`, 258 valve
  pulses at200ms, on-time1-5ms, zero >=5mmHg steps and a terminal end. Strict
  decode and production-C replay passed: ticks25ms, envelope and feature bits
  equal, validity equal, max errors0; replay returned113/86/56. Artifacts:
  `tmp/capture_export_20261028-181030.ndjson`, `.verified.ndjson`, `.csv`,
  `.replay.json`.
- Two independent post-export checks both reported1536 used/2560 free/4096
  reserved, saturated0, pattern `0xA5A5A5A5`; VALID calibration, ADS errors0/
  recoveries0, PC0/PC1 LOW, PC8 HIGH, pump OFF, and fresh low pressure. Logs:
  `tmp/compact_100_65_stack1e_20261028.ndjson` and
  `tmp/compact_100_65_stack2e_20261028.ndjson`.
- Host beat analysis at configured80bpm reports `cadence_unreliable` (19 peaks,
  median interpeak1762ms, cadence fraction0.0). Keep the waveform, but do not
  treat the firmware result or label as accuracy evidence.

## 2026-10-28 follow-up non-human 150/100 capture

- User confirmed BP Pump 2 Standard150/100,80bpm,External Cuff. The bridge
  initially returned two empty five-second snapshots; after a read-only `status`
  command, the 20Hz stream resumed. The cause is unconfirmed. A subsequent snapshot had100
  fresh0.0mmHg samples. The preflight confirmed calibration VALID at
  82.326/-19.887, ADS ONLINE, manual OFF, safe pins, no fault, and zero ADS
  errors/recoveries.
- With firmware target150, inflation reached151.4mmHg and the pump stopped
  automatically. After hold, natural deflation produced `n=2409 capacity=3300
  dropped=0 duration=60200ms interval=25ms`. Board result121/93,75bpm,
  valid1; calculation work1735ms/wall2520ms/max_step31ms. Raw log:
  `tmp/linkpad_standard_20261028-193921.ndjson`. This is simulator evidence,
  not a clinical or numerical accuracy result.
- Initial post-seal snapshot rebounded to3.6-3.7mmHg. Repeated
  `vent` -> 101 fresh0.0 samples -> `seal`; the post-seal five-second snapshot
  contained100 samples at0.0mmHg. Export preflight then passed with92 fresh
  near-zero samples. Final five-second snapshot after all checks also held at
  0.0mmHg. Target restored to50; PC0/PC1 LOW, PC8 HIGH, pump OFF.
- Complete `/2` export hash2959233494 contains2409 points, `calc=2`, 302 valve
  pulses at200ms, on-time1-6ms, five >=5mmHg pressure steps and terminal end.
  Strict decode and production-C replay passed: all ticks25ms, envelope and
  feature bits equal, validity equal, max errors0; replay returned121/93/75.
  Artifacts: `tmp/capture_export_20261028-194221.ndjson`, `.verified.ndjson`,
  `.csv`, `.replay.json`.
- Two independent post-export checks both reported1536 used/2560 free/4096
  reserved, saturated0, pattern `0xA5A5A5A5`; calibration VALID, ADS errors0/
  recoveries0, safe pins, pump OFF and fresh low pressure. Logs:
  `tmp/compact_150_100_stack1f_20261028.ndjson` and
  `tmp/compact_150_100_stack2f_20261028.ndjson`.
- Offline beat analysis at configured80bpm reports `cadence_unreliable` (22
  peaks, median interpeak1725ms, cadence fraction0.048). The deflation waveform
  starts at137.76mmHg and ends at14.68mmHg (mean2.045mmHg/s), leaving891 of
  3300 capture slots unused. Since the waveform starts below labeled150mmHg
  SBP, it cannot validate SBP. No higher-target repeat is scheduled without
  verified connected-part pressure ratings and a capture-capacity budget.

## 2026-10-28 offline raw-voltage cadence comparison

- Added a host-only `raw_cadence` field to `tools/bp_beat_analysis.py`, using
  the strictly decoded original `algorithm_input_v` (`v`) rather than the
  firmware's trailing 32-point/800ms smoothed absolute residual. It requires
  exact25ms MCU ticks, filters0.9-4Hz, measures peaks in the 40-120mmHg span,
  and cross-checks a Welch dominant bin. It emits no SBP/DBP/MAP candidate or
  device command. The existing `beats` field is unchanged.
- All16 retained strict `/2` exports spanning user-labeled 100/65,120/80 and
  150/100 (including the single target190 run) report raw
  `cadence_detected` at declared80bpm: dominant1.328Hz/79.7bpm,
  median interpeak750-775ms, cadence fraction0.886-0.957. The smoothed-envelope
  `beats` field reports `cadence_unreliable` for all16. Four newest captures:

  | Label | Export ID | Raw peaks | Raw fraction | Raw median | Smooth median | Board bpm |
  | --- | --- | ---: | ---: | ---: | ---: | ---: |
  | 100/65 | 175901 | 34 | 0.909 | 775ms | 1475ms | 56 |
  | 100/65 | 180524 | 37 | 0.944 | 775ms | 1850ms | 56 |
  | 100/65 | 181030 | 34 | 0.909 | 775ms | 1762ms | 56 |
  | 150/100 | 194221 | 45 | 0.886 | 775ms | 1725ms | 75 |

- An offline 256-point FFT approximation of the production first-window
  estimator selects56.2bpm at the 135-136mmHg start of each of those three
  100/65 captures. Windows starting at sample512 (about105-108mmHg) instead
  select75/84.4bpm. The 150/100 first window selects75bpm. This accounts for
  the board's unstable pulse-bin selection without proving which high-pressure
  component causes it. The data does not justify changing firmware FFT or BP
  coefficients yet; replayed pressure results and the simulator labels still
  differ, and target150 deflation begins below labeled150mmHg SBP.
- The focused raw-cadence synthetic regressions cover regular80bpm plus5Hz
  valve contamination, wrong cadence, valve-only, absent eligible pressure
  range and irregular MCU ticks. The final focused suite passed8/8 and the
  complete host suite passed87/87; Python compilation checks also passed. No firmware files,
  calibration, wiring, Keil image or actuator settings changed.
- This validation is offline: existing STM32 I2C1 PB6/PB7 to ADS1115/MPXV5050GP
  and USART3 PB10/PB11 to CH340 provided the saved captures; PC0/PC1 valves
  and PC8 pump relay are not driven by this tool. Keep the established module
  supply/logic levels and common ground; no new connection or voltage is
  prescribed. Keil compile/download and new serial acquisition are not needed
  for replay: run the host test command and the CLI on verified NDJSON, expect
  `raw_cadence.status=cadence_detected` while `beats.status` may remain
  `cadence_unreliable`. Any future non-human acquisition still requires safe
  pins, VALID calibration, ADS ONLINE, fresh zero pressure, then complete
  `vent` -> fresh near-zero -> `seal` closeout before human contact is considered.

## 2026-10-28 label-free offline pulse estimator

- `tools/bp_beat_analysis.py` now emits `pulse_estimate` without `--bpm` or a
  simulator label. It uses the strictly decoded original voltage, 40-120mmHg
  span, 0.9-4Hz bandpass, Welch frequency and time-domain peak spacing. It
  reports BPM only when RMS, spectral strength, peak count, peak spacing and
  half-segment frequency consistency all pass. The older `--bpm` comparison
  outputs and optional capacity projection remain available.
- All16 retained complete `/2` captures independently produced `pulse_bpm=80`
  and `status=estimated`, including the invalid-BP captures and the single
  190mmHg acquisition. Their separately recorded simulator setting was80bpm;
  no setting was supplied to this estimator. The underlying 512-point Welch
  frequency resolution is4.6875bpm, so the result is an approximate periodic
  signal estimate, not pulse accuracy or proof of physiological validity.
- Synthetic reference cases at60/80/100bpm with5Hz valve contamination were
  within5bpm. Valve-only, low-amplitude random noise, changing60/80bpm rate,
  irregular MCU ticks and absent40-120mmHg span produced no `pulse_bpm`.
  Focused tests passed12/12. Legacy CLI with `--bpm 80 --current-target 150
  --future-targets 150` still produced its prior comparison/capacity fields;
  CLI with only a capture path produced the new estimate.
- Final full host suite passed91/91 and `py_compile` passed for the tool and
  focused test module. Strictly decoding all16 retained exports without a BPM
  argument returned `pulse_estimate.status=estimated` and `pulse_bpm=80` for
  each; a different-rate physical reference was still untested at this stage.
  The later exploratory 60 bpm capture is documented below.
- This is offline analysis of saved USART3/CH340 exports; no MCU pin, supply,
  ground, calibration, pump, valve or Keil image changed. Verification uses
  `python -m unittest discover -s 'blood pressure monitor/test'` and the CLI
  on a verified NDJSON file. No Keil compile/download or non-human pressure
  run is needed for this host-only increment. A later board validation would
  require the documented PB6/PB7 ADS1115 pressure chain, PB10/PB11 USART3
  capture link, PC0/PC1 valves, PC8 pump relay, verified existing module
  supply/ground, a fresh zero-pressure safe-pin gate, and the full
  `vent` -> fresh near-zero -> `seal` closeout. Before any human contact,
  complete that non-human gate and an independent clinical validation plan.

## 2026-10-28 exploratory 60 bpm physical-reference capture

- User-confirmed non-human BP Pump 2 settings for this run: 150/100 mmHg,
  External Cuff, 60 bpm and **2.0 cc** pulse volume. The previous 80 bpm
  capture's pulse volume was not recorded at acquisition. The historical
  1.5 cc setting belongs to a different 2026-09-23 low-pressure bench trial,
  not a default for this Standard BP group. The user notes that the Standard
  BP pulse groups have different preset volumes and cites 0.65 cc as the
  standard for the relevant group; verify the active group's panel value
  before any controlled comparison. This is not a controlled single-variable
  BPM comparison.
  Existing wiring, power, ground, calibration and firmware were unchanged.
- Preflight had 100 fresh 0.0 mmHg samples, VALID calibration
  (82.326/-19.887), ADS ONLINE with zero errors/recoveries, PC0/PC1 LOW,
  PC8 HIGH and pump OFF. Target150 reached 150.1 mmHg and stopped pumping.
  Deflation remained near 50.7 mmHg at the host's 75 s limit. The script
  stopped, vented to fresh near-zero samples, sealed and restored target50.
  Capture retained 2882/3300 samples, dropped0, duration72025ms, but no
  natural completion or BP calculation occurred. Raw log:
  `tmp/linkpad_standard_20261028-202509.ndjson` (script exit1).
- Initial seal rebounded to about 3.0-3.4 mmHg. A second vent -> 100 fresh
  0.0 mmHg samples -> seal produced 99 further fresh 0.0 samples. The first
  export helper attempt with `--firmware` failed its host-only `sw=` precheck
  before sending `capture export`; its exception closeout again did stop ->
  vent -> fresh low -> seal. Evidence:
  `tmp/capture_export_20261028-203147.ndjson`. A retry without that optional
  precheck passed fresh sealed low-pressure, calibration, ADS and safe-pin gates.
- The retained capture exported completely as `bp.capture/2`: 2882 points,
  `calc=0`, dropped0, duration72025ms, checksum747035401, raw_kind2,
  firmware `CAPTURE_COMPACT_20261028`. Strict offline decode passed. Since
  `calc=0`, envelopes and BP features are absent; no production-C result or
  blood-pressure accuracy claim is made. Evidence:
  `tmp/capture_export_20261028-203223.ndjson`.
- Label-free original-voltage analysis of the 40-120 mmHg span used 2062
  eligible samples and 51 peaks. It estimated **61 bpm** (dominant1.016 Hz,
  median interpeak1000ms, cadence fraction1.0; both halves1.016 Hz), close to
  the independently confirmed 60 bpm panel setting. This is an exploratory
  periodic-signal estimate from a truncated capture, not a complete BP run or
  clinical pulse-rate validation. The prior 80 bpm capture
  `tmp/capture_export_20261028-194221.ndjson` estimated80 bpm.
- This run's captured deflation went from135.61 to42.18 mmHg in72.025 s,
  averaging1.297 mmHg/s, versus2.045 mmHg/s in the prior 80 bpm run. At that
  mean rate, reaching roughly15 mmHg would require about21 additional seconds
  and roughly850 more points, exceeding the418 free capture slots. The changed
  pulse volume and rate do not establish the cause of slower deflation. Do not
  repeat a target150 acquisition under these conditions until the rate and
  capacity risk are resolved. After export, a fresh five-second snapshot had
  100/100 samples at 0.0 mmHg with the valve sealed.

## 2026-10-28 bounded 60 bpm / 0.7 cc deflation-rate probe

- The user set a User Defined group to 150/100 mmHg, 60 bpm, 0.7 cc and
  External Cuff. The BP Pump 2 manual lists User Defined pulse volume in
  0.1 cc steps; the Standard BP #2 preset is 150/100, 80 bpm, 0.65 cc.
  These are distinct modes/settings. This probe changes only the declared
  pulse volume relative to the preceding 60 bpm / 2.0 cc run; the panel
  setting was user-reported, not electronically read back.
- A host-only `--rate-probe` mode was added to
  `tmp/linkpad_lowpressure_check.py`. It retains calibration, ADS, fresh-zero,
  safe-pin, pressure-ceiling and telemetry-freshness gates; starts once at
  target150; stops when fresh deflation pressure reaches <=110 mmHg or after
  45 seconds; and always does stop -> vent -> fresh low -> seal, restores
  target50 and reads pins/status/fault. Mock-bridge success and timeout tests
  passed (10/10 full helper suite); `py_compile` passed. No firmware code,
  Keil image, calibration, wiring or supply settings changed.
- Preflight: 100 fresh 0.0 mmHg samples, calibration 82.326/-19.887 VALID,
  ADS ONLINE/errors0/recoveries0, PC0/PC1 LOW, PC8 HIGH, pump OFF. Pump
  stopped at firmware target150.4 mmHg. The host probe observed deflation
  from135.2 to109.8 mmHg over15699 ms, mean1.618 mmHg/s, then deliberately
  stopped. Capture retained643/3300 points, dropped0, duration16050 ms;
  this is an intentionally incomplete, uncalculated BP sample. Log:
  `tmp/linkpad_rate_probe_20261028-205027.ndjson`.
- First sealed closeout rebounded to3.9 mmHg; the export preflight correctly
  rejected before issuing `capture export` (log
  `tmp/capture_preflight_20261028-205127.ndjson`). A repeat vent produced
  100 fresh0.0 samples; seal then produced101 fresh0.0 samples and passed
  independent safe-state preflight (log
  `tmp/capture_preflight_20261028-205217.ndjson`). The retained capture
  exported with `calc=0`, n643, dropped0, hash4138791489 and passed strict
  decode: `tmp/capture_export_20261028-205246.ndjson`. Post-export101 fresh
  samples were all0.0 mmHg. No BP result/replay success is claimed.
- On the common130-110 mmHg pressure band, a linear fit to original40Hz
  capture pressure vs MCU elapsed time gives1.573 mmHg/s for this 0.7 cc
  run (552 points), versus0.773 mmHg/s for the preceding 2.0 cc run
  (861 points). The earlier 80 bpm run gives2.206 mmHg/s (388 points),
  but its pulse volume is unknown. The 0.7 cc run is faster than the
  2.0 cc run in this band, yet one run per setting cannot establish the
  cause or guarantee a full target150 capture fits3300 points. No further
  full-pressure repeat should use the old capacity projection uncritically.
- Existing hardware route for this non-human check: STM32 I2C1 PB6/PB7 ->
  ADS1115/MPXV5050GP; USART3 PB10/PB11 -> CH340/OmniProbe; PC0/PC1 ->
  valve drivers; PC8 -> pump relay; BP Pump 2 Pressure Port -> existing
  External Cuff/tee path. The established module supply, common ground,
  polarity and pressure-rated tubing were retained without new voltage
  advice. Before any future power cycle, check disconnected wiring for
  shorts/polarity, then measure the established supply/logic points before
  running. No Keil build/download was needed because only a host probe
  changed; any future firmware flash must be built/verified in Keil and the
  calibration rechecked before pressure work. Serial gates and the complete
  non-human vent -> fresh zero -> seal sequence remain required before any
  human contact.

## 2026-10-28 bounded 80 bpm / 0.7 cc rate comparison

- User reported changing only HR from60 to80 bpm in the same User Defined
  150/100 mmHg, 0.7 cc, External Cuff group. Before the run, 100 fresh
  pressure samples were0.0 mmHg; sealed preflight found calibration VALID,
  ADS ONLINE/errors0/recoveries0, PC0/PC1 LOW, PC8 HIGH and pump OFF.
  Panel parameters are user-reported, not electronically read back.
- The same single-run `--rate-probe` stopped at a fresh110.0 mmHg reading.
  Firmware pump target was reached at152.0 mmHg; the diagnostic stream
  measured138.4 to110.0 mmHg in13249 ms (whole observed segment mean
  2.144 mmHg/s). Retained capture n546/3300, dropped0, duration13625ms;
  no natural completion or BP calculation was intended. Raw log:
  `tmp/linkpad_rate_probe_20261028-210006.ndjson`.
- The initial stop -> vent -> near-zero -> seal closed PC1 but sealed
  pressure rebounded to3.6-3.9 mmHg. Independent export preflight rejected
  before any capture command (`tmp/capture_preflight_20261028-210049.ndjson`).
  A second vent gave100 fresh0.0 mmHg samples, followed by seal and100
  fresh0.0 samples; safe-state preflight then passed
  (`tmp/capture_preflight_20261028-210136.ndjson`). Complete `/2` export
  had n546, dropped0, `calc=0`, hash538628828 and passed strict decode:
  `tmp/capture_export_20261028-210148.ndjson`. A final sealed five-second
  snapshot contained101/101 samples at0.0 mmHg. An independent final
  status/pins/cal/fault preflight also passed with92 fresh0.0 samples,
  safe pins and ADS errors/recoveries0:
  `tmp/capture_preflight_20261028-210342.ndjson`. No BP result is claimed.
- Linear fits of original40Hz pressure vs MCU elapsed time over the same
  130-110 mmHg band gave 1.761 mmHg/s for this80 bpm/0.7 cc probe
  (382 points) and1.573 mmHg/s for the preceding60 bpm/0.7 cc probe
  (552 points). The earlier60 bpm/2.0 cc capture gave0.773 mmHg/s
  (861 points). The short-run start-to-end means are not directly
  interchangeable because their start pressures differ; the common-band
  fits are the comparison metric. One run per setting and no electronic
  panel readback prevent a causal or repeatability claim. Full-duration
  capture capacity at these settings remains unverified. Offline band checks
  show the older complete80 bpm capture's 110-90/90-70/70-50/50-30 mmHg
  rates were2.397/2.021/1.724/1.921 mmHg/s, while the truncated60 bpm/2.0 cc
  capture's corresponding bands were1.447/1.192/1.863/1.436. Neither new
  0.7 cc probe extends below110 mmHg, so these older bands cannot be used
  as a verified low-pressure rate or capacity bound for the new setting.
- The existing PB6/PB7 ADS1115/MPXV5050GP, PB10/PB11 USART3/CH340,
  PC0/PC1 valve and PC8 relay wiring, established supply/common ground
  and non-human External Cuff path were retained. No firmware or Keil image
  changed, so no Keil build/download or calibration rewrite was performed.
  Any future power cycle begins with unpowered short/polarity checks, then
  measured established supply/logic points. Before any further pressure
  test, require fresh zero, safe pins, calibrated ADS and capacity-aware
  stop limits; before human contact, complete separate non-human validation.

## 2026-10-28 bounded low-pressure repeat at 80 bpm / 0.7 cc

- User kept the same User Defined 150/100 mmHg, 80 bpm, 0.7 cc, External Cuff
  simulator setting. The host-only `--low-band-probe` temporarily set the
  STM32 inflation target to120 mmHg to sample the lower pressure range;
  simulator BP settings were not changed by the script. User-reported panel
  settings were not electronically read back. Before inflation, 100 fresh
  samples were0.0 mmHg; independent preflight confirmed VALID calibration
  82.326/-19.887, ADS ONLINE/errors0/recoveries0, PC0/PC1 LOW, PC8 HIGH
  and pump OFF (`tmp/capture_preflight_20261028-210703.ndjson`).
- This single-run host mode retained the existing pressure freshness and
  actuator closeout gates, with target120, ceiling135, endpoint45 mmHg and
  fixed55-second deadline (at40Hz, below3300 capture slots). Success and
  timeout mock-bridge paths passed; all12 helper tests and `py_compile`
  passed before hardware operation. It was not allowed to extend the
  deadline on an early natural-completion message. No firmware, Keil
  project/image, wiring, power or calibration changed.
- Firmware pump stopped at120.7 mmHg. The serial diagnostic stream captured
  deflation from101.6 to44.2 mmHg in22698ms (mean2.529 mmHg/s), then the
  host deliberately stopped and executed vent -> fresh near-zero -> seal.
  Internal capture n920/3300, dropped0, duration22975ms, 25ms interval;
  no natural completion/BP calculation. Raw log:
  `tmp/linkpad_low_band_probe_20261028-210926.ndjson`.
- Sealed pressure first rebounded to3.7-4.0 mmHg; independent export
  preflight rejected before any `capture export` command
  (`tmp/capture_preflight_20261028-211012.ndjson`). A repeat vent gave100
  fresh0.0 mmHg samples; seal then gave100 fresh0.0 samples, and the
  independent status/pins/cal/fault preflight passed
  (`tmp/capture_preflight_20261028-211111.ndjson`). Full `/2` export passed
  checksum3933949926 and strict decode: n920, dropped0, `calc=0`,
  raw_kind2, 116 valve pulses, 200ms period, on-time1-4ms, steps0.
  File: `tmp/capture_export_20261028-211130.ndjson`. A final sealed
  five-second snapshot gave101/101 fresh0.0 mmHg samples; a separate final
  status/pins/cal/fault preflight passed with92 fresh0.0 samples, safe pins
  and ADS errors/recoveries0 (`tmp/capture_preflight_20261028-211249.ndjson`).
  This is an intentionally stopped raw capture, not a BP result.
- Linear fits of original40Hz pressure vs MCU elapsed time gave2.248,
  2.628 and2.535 mmHg/s for100-80,80-60 and60-45 mmHg respectively
  (357/291/236 points). For context, the prior complete80 bpm capture
  gave1.957/1.862/1.941 in those bands, but its pulse volume was not
  recorded; the truncated60 bpm/2.0 cc capture gave1.208/1.255/1.935.
  The new0.7 cc low-pressure data cover these pressure bands in one short
  run. A target120 capture is not a verified target150
  capacity bound, and pressure below45 mmHg remains unmeasured here.
- Existing STM32 PB6/PB7 I2C1 ADS1115/MPXV5050GP, PB10/PB11 USART3/CH340,
  PC0/PC1 valve drivers, PC8 pump relay, BP Pump 2 Pressure Port and real
  External Cuff/tee path were retained with established supply and common
  ground. No new voltage or wiring advice was issued. Before a future
  power cycle: unpowered short/polarity check, then measure established
  supply/logic points, then run. No Keil build/download was needed for
  this host-only change; future firmware flashing requires Keil build,
  download verification and calibration readback before pressure work.
  Any later human-contact use requires separate non-human safety and
  reference validation.

## 2026-10-28 full User Defined 150/100 capture at 80 bpm / 0.7 cc

- User kept the BP Pump 2 User Defined 150/100 mmHg, 80 bpm, 0.7 cc,
  External Cuff setting (panel setting user-reported, not electronically
  read back). A host-only `--user-defined` mode was added so the log does
  not call this a Standard BP preset. It preserves the existing single-run
  target150, ceiling165 mmHg, 75-second acquisition limit, fresh-pressure
  gate and stop -> vent -> fresh near-zero -> seal closeout. A naturally
  complete raw capture is retained even if the firmware reports invalid BP;
  mock-bridge suite passed13/13 and `py_compile` passed before hardware use.
  Firmware code, Keil image, calibration, wiring and supply were unchanged.
- Initial 101 fresh samples were0.0 mmHg; independent sealed preflight
  confirmed cal82.326/-19.887 VALID, ADS ONLINE/errors0/recoveries0,
  PC0/PC1 LOW, PC8 HIGH and pump OFF
  (`tmp/capture_preflight_20261028-211635.ndjson`). Firmware reached
  151.2 mmHg and stopped pumping. Deflation began at136.95 mmHg,
  below the simulator's labeled150 mmHg SBP; the observed serial peak was
  146.8 mmHg. Deflation naturally ended within the75-second host limit.
  Capture n2185/3300, dropped0, duration54600ms, all internal ticks25ms;
  1115 slots remained. Log: `tmp/linkpad_user_defined_20261028-211732.ndjson`.
- The firmware completed calculation but reported `BP calculation failed`.
  Diagnostics were MAP90.8, SBP feature130.0, DBP feature91.5 mmHg.
  `bp_algorithm.c` rejects `dbp > map_pressure` under its hard ordering
  gate, so the candidate pressures are not a reportable BP result.
  Independent raw-voltage analysis nevertheless estimated80 bpm from
  1479 eligible40-120 mmHg samples, 46 peaks, dominant1.328Hz,
  median interpeak775ms and cadence fraction0.933. It is a periodic
  signal estimate, not firmware pulse/BP validity or clinical accuracy.
- Natural end was followed by stop -> vent -> fresh low -> seal. The first
  sealed zero check rebounded to3.5-3.6 mmHg and export preflight rejected
  before sending the capture command
  (`tmp/capture_preflight_20261028-211946.ndjson`). Repeat vent gave100
  fresh0.0 samples; repeat seal gave100 fresh0.0 samples and passed
  independent preflight (`tmp/capture_preflight_20261028-212154.ndjson`).
  The complete `/2` export had n2185, dropped0, `calc=3`, hash3833782917,
  274 valve pulses at200ms, on-time1-6ms and nine >=5mmHg steps (seven
  in phase bin0, two in bin1). Strict decode and production C replay
  passed; envelope/smooth errors0, feature bits and validity equal.
  Files: `tmp/capture_export_20261028-212208.ndjson`, `.csv`,
  `.verified.ndjson`, `.replay.json`. These valve phase counts show
  association only, not proof of the BP failure mechanism.
- After export, a sealed five-second snapshot had100/100 fresh0.0 mmHg
  samples. Final independent status/pins/cal/fault preflight passed with
  93 fresh0.0 samples, PC0/PC1 LOW, PC8 HIGH, pump OFF, calibration VALID,
  ADS errors/recoveries0 (`tmp/capture_preflight_20261028-212327.ndjson`).
  The pressure trace ran136.95 to14.69 mmHg at mean2.239 mmHg/s; this
  single run verifies capture capacity at target150 for this setting,
  but not repeatability or capacity at higher targets. It cannot validate
  SBP because acquisition starts below the150 mmHg reference SBP.
- Existing non-human route remains STM32 PB6/PB7 I2C1 to ADS1115 and
  MPXV5050GP; PB10/PB11 USART3 to CH340; PC0/PC1 valve drivers; PC8 pump
  relay; BP Pump 2 Pressure Port through the existing tee and real
  External Cuff, with established module supplies and common ground.
  No voltage change is prescribed. Before future power-up, check
  unpowered short/polarity, then measure established supply/logic points.
  No Keil build/download was required for this host-only mode; any future
  firmware flash requires Keil build/verify and calibration readback.
  The non-human vent -> fresh zero -> seal gate must precede any human
  contact, which still requires separate reference and clinical validation.

## 2026-10-28 offline diagnosis of the 150/100 invalid result

- Read-only comparison of six retained User Defined 150/100, 80 bpm,
  External Cuff `/2` CSV exports and production-C replay reports. These
  labels are operator-confirmed panel settings, not values encoded by the
  captures. No new pressure run, device command, firmware edit or flash was
  performed. The most recent run `212208` has 2185 consecutive 25 ms
  samples, zero dropped samples, and exact replay agreement; its invalid
  result is not explained by capture truncation or a replay mismatch.
- The firmware confines its MAP search to 80-100 mmHg and chooses the
  maximum 32-sample-smoothed envelope there. DBP is the first three-sample
  crossing below 60% of that selected peak. The hard `DBP > MAP` check
  correctly rejects reversed feature pressures; it does not identify the
  source of the reversed values. A simple `(150+2*100)/3` reference is
  116.7 mmHg, outside the MAP search window, but the simulator's actual
  generated MAP was not independently measured. The fixed search window
  and fixed -10/-5 mmHg offsets were tuned for other conditions and cannot
  establish 150/100 accuracy.
- In all three invalid runs, the selected MAP sample is exactly 20 samples
  (500 ms) after a >5 mmHg downward pressure step:

  | Export | Step index / delta | MAP index / pressure | DBP index / pressure | MAP-to-DBP |
  | --- | ---: | ---: | ---: | ---: |
  | 115410 | 744 / -6.52 mmHg | 764 / 95.135 mmHg | 780 / 95.731 mmHg | 0.400 s |
  | 120531 | 584 / -7.30 mmHg | 604 / 95.390 mmHg | 622 / 96.015 mmHg | 0.450 s |
  | 212208 | 728 / -6.73 mmHg | 748 / 90.775 mmHg | 762 / 91.457 mmHg | 0.350 s |

- The MAP-to-DBP pressure rise is respectively 0.60, 0.62 and 0.68 mmHg.
  In `212208`, the nearby nine-point pressure medians also rise by about
  0.55 mmHg, so the rejected order is not only one isolated pressure sample.
  The three valid comparison runs (`115823`, `123230`, `194221`) have no
  >5 mmHg downward step within 40 samples before their selected MAP. Their
  reported results are 120/94, 121/73 and 121/93; passing the ordering gate
  does not demonstrate agreement with the 150/100 panel label.
- All recorded >=5 mmHg steps in these six runs occupy the first two 25 ms
  bins after a recorded valve pulse: invalid runs 8/8, 1/1 and 9/9;
  valid runs 2/2, 1/1 and 5/5. The `212208` split is 7 in bin 0 and 2 in
  bin 1; the other five runs' steps are all in bin 0. This supports timing
  association between pressure transients and the valve schedule, but the
  phase association alone does not distinguish valid from invalid rounds
  and is not an independent causal proof. The pressure port, valve/airway
  coupling, sensor response and BP Pump 2 output have not been isolated.
- Current attribution: the **software feature selection** is demonstrably
  sensitive to these transients and the 150/100 setting lies outside its
  justified MAP window. A valve-period-related *sensor-reported* pressure
  transient is strongly indicated. The single sensor channel cannot establish
  whether this is pneumatic or electrical coupling; a failed valve, failed
  sensor/ADS, or faulty BP Pump 2 is not established. The saved data do not
  support changing the validity gate, compensation, or MAP bounds by guesswork.
  Next diagnostic should compare pulse/valve-aware features offline or use a
  separately planned non-human synchronous reference-pressure measurement. No new
  inflation is needed for the present attribution.

## 2026-10-28 offline MAP-selection sensitivity check

- Read-only recalculation on the same six CSV exports. The production C source
  hash in the `212208` replay matches the present `bp_algorithm.c`. The
  extractor uses a centered +/-32-sample linear detrend and a trailing
  32-sample mean; the previous references here to a 20-sample smooth window
  were transcription errors. The three invalid-run MAP indices still happen
  to be 20 samples after their large downward steps; that timing is **not**
  one full smoothing window.
- For an exploratory exclusion, locate every consecutive pressure drop
  greater than 5 mmHg and exclude MAP candidates from 32 samples before
  through 63 after its index. This covers the centered detrend's affected
  indices and the following 32-point trailing mean. Keep the exported
  `smooth_v` values unchanged, preserve the production scan's first
  pressure-below-80 stop, and compare both 80-100 and 80-130 mmHg candidate
  windows. This is a selection sensitivity test, **not** a production-C
  replay or a validated artifact-removal algorithm.

  | Export | Production MAP (80-100) | Wide 80-130, no exclusion | Wide 80-130, excluded |
  | --- | ---: | ---: | ---: |
  | 115410 | 95.13 | 108.30 | 115.33 |
  | 120531 | 95.39 | 95.39 | 123.35 |
  | 212208 | 90.78 | 117.84 | 117.32 |
  | 115823 | 99.45 | 113.95 | 113.95 |
  | 123230 | 85.99 | 120.99 | 120.99 |
  | 194221 | 98.93 | 111.52 | 111.52 |

- The excluded wide-window candidates span 111.52-123.35 mmHg, near the
  simple 116.7 mmHg label-based MAP estimate, but this is not an independently
  measured BP Pump 2 MAP. The wide unexcluded window still selects a
  95.39 mmHg peak in `120531`; the strict exclusion shifts its pick to
  123.35 mmHg. The selection is therefore sensitive both to the search
  bounds and to how valve-phase transients are handled. Even a passing
  `DBP < MAP` order after exclusion would not validate SBP/DBP accuracy,
  because the original smoothed envelope was not recomputed, the
  extraction threshold would be reused, and deflation begins below the labeled
  150 mmHg SBP. Do not adopt either offline window or exclusion as a firmware
  parameter change from this six-run comparison alone.

## 2026-10-28 label-free beat oscillogram feasibility study

- Host-only `blood pressure monitor/tools/bp_oscillogram_study.py` strictly
  decodes complete `/2` captures, reuses the existing label-free spectral
  pulse gate, bandpasses original voltage at 0.9-2.5 Hz, and extracts each
  pulse's baseline-relative height and positive area between adjacent troughs.
  It excludes beats near >=5 mmHg adjacent pressure steps (default +/-40
  samples around each beat support), bins the remaining beats by 5 mmHg,
  and compares the strongest bin with a robust Gaussian curve fit. Neither
  the BP setting nor the firmware BP result is an input. It reports only
  research MAP candidates, never SBP/DBP or a clinical BP result.
- Evidence basis and limits: the 2025 area/height oscillogram study
  (DOI:10.3389/fphys.2025.1611096) measured 250 Hz cuff waveforms in 109
  patients with simultaneous invasive reference and discarded oscillograms
  whose peak lacked a falling tail on either side (>80% endpoint amplitude).
  Its published fits used invasive SBP/DBP as model inputs; its reported fit
  errors are **not** a stand-alone BP accuracy claim for our method. The 2023
  reduced-oscillogram model (DOI:10.1109/TBME.2022.3201433) likewise fitted
  patient curves with known invasive BP inputs. A 2025 validated-monitor
  study (DOI:10.1038/s41598-025-18850-w) found variable amplitude-dependent
  ratios matched that specific device better than fixed ratios; it does not
  supply transferable ratios for this simulator/cuff. The 2023 hybrid deep
  model (DOI:10.1109/JBHI.2023.3310868) trained on 245 people across three
  databases; 13 simulator captures provide no comparable training or
  clinical validation basis. Therefore only the *feature-extraction and
  completeness ideas*, not those papers' BP estimates, were tried here.
- Thirteen retained, checksum-verified 80 bpm exports were evaluated: four
  labeled 120/80, three 100/65, and six 150/100 (the last one User Defined
  0.7 cc; earlier 150/100 runs were Standard preset). Every original-voltage
  trace passed the independent ~80 bpm cadence gate. Results below use the
  default 40-sample step padding. `fit` is the height-oscillogram Gaussian
  center; quality is determined without a pressure label. A candidate is
  rejected if either side lacks two occupied 5 mmHg bins, an endpoint stays
  >=80% of the peak, or the binned maximum and fit differ by >7.5 mmHg.

  | User label | Export IDs | Height fit MAP (mmHg) | Quality |
  | --- | --- | --- | --- |
  | 120/80 | 214442, 220211, 220714, 113752 | 97.84, 93.39, 95.38, 94.79 | 4 diagnostic candidates |
  | 100/65 | 114718, 120941, 121553 | 78.58, 78.96, 78.24 | 2 candidates; 121553 unstable bin/fit peak (87.5/78.24) |
  | 150/100 | 115410, 115823, 123230 | 114.63, 115.92, 116.11 | 115410 upper side sparse; other 2 candidates |
  | 150/100 | 194221, 212208 | 118.26, 130.00 (fit bound) | both incomplete upper-side oscillograms |
  | 150/100* | 120531 | 79.21 | shape aligns with 100/65 group; label/state unverified |

  `*` The log says the `120531` run began before the operator requested the
  next 100/65 point; the simulator setting was not electronically recorded.
  Its 79.21 mmHg fit and 77.5 mmHg bin peak resemble the 100/65 captures,
  but the evidence cannot tell whether panel state changed during the run,
  simulator output varied, or the label is wrong. Do not count it as proof of
  a 150/100 algorithm failure or as proof of a BP Pump 2 fault.
- Default high-side completeness is conservative. At step padding 0/10,
  `212208` fits 116.37/116.69 mmHg but its high-tail amplitude is already
  79.4% of peak, near the 80% exclusion boundary. At padding 20/30 its only
  upper occupied bin is 127.5 mmHg; at 40/60 no upper bin remains and the fit
  hits the 130 mmHg bound. The latest invalid round therefore **cannot be
  robustly rescued** by this algorithm from the saved trace. `194221` has
  high-tail ratio 84.7% at every tested padding. The 2025-style area feature
  offered no consistent quality improvement over pulse height on these 40 Hz
  captures; in `194221`, area bin peak 107.5 and fitted center 118.22 mmHg
  disagree. This is a research comparison, not a firmware-ready estimator.
- Across the six 150/100 exports, 24 pressure falls >5 mmHg have median fall
  5.66 mmHg and median next-25-ms rebound 4.00 mmHg (71% of the fall),
  leaving median net 1.80 mmHg below the pre-step sample. Combined with the
  recorded valve phase, this supports a short valve-synchronous *reported*
  transient rather than treating each step as persistent leakage. One sensor
  cannot distinguish pneumatic response from valve-driver electrical pickup;
  ADS errors=0 rules out logged I2C faults, not analog interference.
- Conclusion: the existing fixed 80-100 mmHg MAP search and single crossing
  can manufacture invalid feature order despite intact, periodic raw data.
  Pulse extraction and a label-free MAP curve are feasible in well-covered
  rounds, but the algorithm does not solve every captured 150/100 round and
  cannot validate SBP: all those captures start deflation around 134-137
  mmHg, below the labeled 150 mmHg SBP. Missing upper-pressure information
  cannot be recovered without extrapolation. Preserve raw data and invalid
  result status; do not change production thresholds, compensation or safety
  gates from this study. If a full-BP result is required, a separately planned
  non-human acquisition/reference experiment must first supply the missing
  high-pressure region and an independent pressure trace.
- No serial/TCP command, BP Pump 2 operation, wiring, supply, calibration,
  firmware file, Keil project/image or pressure safety limit changed. The
  existing PB6/PB7 ADS1115/MPXV5050GP, PB10/PB11 USART3/CH340, PC0/PC1
  valves, PC8 pump relay and BP Pump 2 Pressure Port/tee/real External Cuff
  path remain the known non-human setup. Before any later power-up, check
  unpowered shorts/polarity, then established supply/logic voltages; before
  later inflation verify sealed fresh zero, safe pins and ADS state. Keil
  compile/download and calibration readback apply only to a later firmware
  change; any future measurement must close with vent -> fresh zero -> seal.
- The new synthetic tests cover two distinct unlabeled MAP curves with 5 Hz
  valve noise and an impulse, valve-only rejection, missing high-side tail,
  incomplete calculation and bounded padding. `py_compile`, a strict-export
  CLI smoke check and the complete 96-test host suite passed. No Keil build
  was needed because no firmware source or MDK project changed.

## 2026-10-28 hold-stage cause of missing 150 mmHg coverage

- Read-only inspection of ten retained 2026-10-28 `linkpad_standard_*` and
  `linkpad_user_defined_*` logs with 150 mmHg inflation target (including
  120/80, 100/65 and 150/100 simulator labels). The `target reached` events
  were 150.5-152.2 mmHg. The following `PWM started after hold` events came
  1006-1013 ms later, with the nearest fresh pressure readings 134.1-137.8
  mmHg; median reported loss was 15.95 mmHg, range 13.6-16.8 mmHg. The most
  recent run reported 151.2 mmHg at pump stop, 146.7 about 15 ms later,
  135.5 about 914 ms later, and 136.5 at deflation start.
- Current `main.c` sets `DEFLATE_HOLD_MS=1000`. At target it disarms the
  pump, closes valve1 and stops the pump; during the hold loop it closes
  valve2. `BP_Algorithm_Reset()` and the first controlled valve pulse occur
  only after the hold. Thus the upper-pressure loss precedes the deflation
  PWM and the capture's first sample. Short valve-synchronous pressure
  spikes later in deflation are a separate issue. Whether the hold loss is
  pneumatic relaxation/leakage, pressure-sensor response to pump stopping,
  or a BP Pump 2 interaction cannot be distinguished from this single
  sensor channel. It is repeatable at this setup/target, not proof that a
  specific component failed.
- A pulse/MAP algorithm cannot reconstruct the unrecorded 150 mmHg-and-above
  deflation region. Before seeking a full 150/100 SBP/DBP result, the next
  non-human acquisition design must preserve high-side pressure through
  the required simulator settling hold and stay within the verified 3300
  sample budget and existing pressure/time safety gates. Do not shorten the
  hold or raise the inflation target by guesswork on a person. A separately
  logged pressure reference and panel state would distinguish pressure
  behavior from an algorithm-only failure in that future bench test.
- A bounded read-only projection from the six observed 150/100 capture rates
  gives 2721-2996 points at target180, leaving 304-579 of the current 3300
  slots; at target190 it gives 2900-3192, leaving only 108-400. These are
  extrapolations assuming unchanged hold loss and deflation rate, not safe
  capacity guarantees. The slowest target180 projection is about 74.9 s,
  essentially at the existing 75 s host deadline; `--user-defined` also has
  a 165 mmHg ceiling intended for target150. Any later higher-target bench
  protocol must first redesign and test its host deadline/ceiling/abort
  margins and verify non-human pressure safety, rather than simply changing
  `target 180` or `target 190` on the running device.

## 2026-10-28 bounded 180-to-125 mmHg high-band probe

- The user approved one non-human short probe after the manual review showed
  no specified `SBP+10 mmHg` pulse-onset threshold. BP Pump 2 was left at the
  user-reported User Defined 150/100 mmHg, 80 bpm, 0.7 cc, External Cuff
  setting; there is no electronic panel readback. Existing PB6/PB7 ADS1115
  and MPXV5050GP, PB10/PB11 USART3/CH340, PC0/PC1 valve drivers, PC8 pump
  relay, established common ground/supplies, BP Pump 2 Pressure Port/tee and
  real external cuff wiring were retained. No supply, wiring, calibration,
  firmware, Keil project/image or pressure safety limit changed.
- A host-only `--high-band-probe` mode sets target180 mmHg for one run, with
  195 mmHg observed-pressure ceiling, 35 s total deadline, fresh stream and
  firmware-safety aborts. It deliberately stops near125 mmHg and always runs
  stop -> vent -> fresh low pressure -> seal, then restores target50. Success,
  timeout and over-ceiling mock paths passed; all16 helper tests and Python
  syntax checks passed before hardware operation. It does not retry inflation
  or count an incomplete capture as a BP result.
- Before start, a fresh five-second bridge snapshot had100/100 samples at
  0.0 mmHg. The mode's own status/pins/cal/fault preflight confirmed cal
  VALID, ADS ONLINE/errors0/recoveries0, manual OFF, PC0/PC1 LOW, PC8 HIGH,
  pump OFF and acceptable USER_STOP latch. Firmware reported target reached
  180.7 mmHg and stopped the pump; one-second hold then began deflation at
  164.77 mmHg. Serial high-band probe reached124.3 mmHg after18.199 s of
  deflation (mean2.225 mmHg/s) and stopped. Capture n739/capacity3300,
  dropped0, 18450 ms, every interval25 ms. Raw run log:
  `tmp/linkpad_high_band_probe_20261028-222216.ndjson`.
- The first vent/seal cleanup satisfied the host's <=2 mmHg short closeout
  gate but rebounded after sealing to5.0-5.5 mmHg over a later five-second
  snapshot. A second manual `vent` produced100/100 fresh0.0 mmHg samples,
  then `seal` produced another100/100 fresh0.0 samples. Independent
  status/pins/cal/fault export preflight passed with93 new0.0 samples, safe
  pins and ADS errors/recoveries0 (`tmp/capture_preflight_20261028-222527.ndjson`).
  The `/2` export decoded strictly: 739 points, hash3258760216, `calc=0`,
  93 valve pulses at200 ms, on-time1-6 ms, two >=5mmHg steps, no result
  features. Files: `tmp/capture_export_20261028-222538.ndjson`, `.csv`,
  `.verified.ndjson`, `.decode.json`. A final sealed five-second snapshot
  again had100/100 fresh0.0 mmHg samples. This is a deliberately stopped
  raw waveform, not a valid or invalid BP calculation.
- Offline, a third-order zero-phase 0.9-2.5 Hz bandpass on original40Hz
  `algorithm_input_v` found six consecutive positive peaks before the first
  large step: indices15/46/76/106/136/164 at cuff pressures
  164.0/162.3/161.0/160.0/159.2/158.5 mmHg. Their five intervals are
  775/750/750/750/700 ms (median750 ms, 80 bpm); filtered positive peak
  amplitudes are about3.3-5.0 mV. Later pulses continue near145-130 mmHg.
  Thus regular pulse activity is already visible above160 mmHg in this run.
  The export begins at164.77 mmHg, so it cannot identify the actual pulse
  onset at higher pressure or establish any manual-defined onset threshold.
- The two >=5mmHg steps occur at indices200/201: -11.20 then +7.65 mmHg,
  with the recorded valve phases in bins0/1. This is a short reported-pressure
  transient; it must not be treated as a physiological beat or direct proof
  of a valve fault. A single-sensor trace cannot distinguish pneumatic
  coupling from electrical/sensor effects. The high-band run confirms an
  acquired upper-pressure pulse segment but does not supply a complete
  descending oscillogram or a 150/100 SBP/DBP accuracy test.
- Future full-capture work remains non-human: verify the BP Pump 2 panel
  setting, unpowered connection/short checks before any power reconnection,
  then established supply/logic voltages and common ground; Keil build/download
  only after any later firmware edit, with calibration readback after flash.
  Confirm fresh zero, calibration, ADS, pump/valve pins and bounded capture
  before another pressure run. Observe high-side pulse continuity, valve-step
  phases, 3300-point capacity and timeout; finish every run with vent ->
  fresh near-zero -> seal. Human-contact validation remains separate.

## 2026-10-28 complete non-human User Defined 180 mmHg capture

- The operator-reported reference remained User Defined 150/100 mmHg, 80 BPM,
  0.7 cc, External Cuff; the panel has no electronic readback. One approved
  non-human full capture used `tmp/linkpad_lowpressure_check.py
  --user-defined-180`. Its host gates were target180, observed pressure
  ceiling195 mmHg and natural-completion deadline82 s from `start`; fault,
  stale samples or ceiling breach abort to stop -> vent -> fresh low -> seal
  and restore `target 50`. No retry inflation occurred.
- Preflight found fresh0.0 mmHg, valid calibration, ADS online with errors0,
  PC0/PC1 LOW, PC8 HIGH and pump OFF. Pump-stop pressure reached180.5 mmHg;
  one-second hold preceded deflation at about166.0 mmHg, a reported drop of
  about14.5 mmHg before the first capture point. Deflation completed naturally:
  n2569/3300, dropped0, span64200 ms, every MCU interval25 ms. Raw bridge
  log: `tmp/linkpad_user_defined_180_20261028-223452.ndjson`.
- Firmware calculated `calc=3` (invalid BP): MAP index1131/P83.206, SBP
  feature158.6 and DBP feature83.561 mmHg. DBP > MAP violates the existing
  ordering gate. Strict `/2` export and production-C replay matched all
  envelope/feature bits and validity, so this is the production algorithm's
  result on the saved inputs, not a decoding difference. Export:
  `tmp/capture_export_20261028-223729.ndjson` and its `.verified.ndjson`,
  `.csv` and `.replay.json` outputs.
- The export records322 valve pulses at200 ms, 1-6 ms on-time, and seven
  adjacent pressure falls >=5 mmHg, all in the first25 ms phase bin after a
  pulse. Indices1104 and1112 show -6.731 and -5.979 mmHg falls with immediate
  +4.800 and +4.388 mmHg rebounds. The firmware MAP at1131 follows those
  falls by675 and475 ms. These are valve-synchronous reported-pressure
  transients; the single sensor does not identify whether the cause is
  pneumatic, driver electrical pickup or sensor response.
- A label-free 0.9-2.5 Hz original-voltage beat study with the explicit170
  mmHg upper bound found dominant1.328 Hz (~79.7 BPM),74 detected peaks and
  7 pressure steps. At step padding0/20/40/60 samples, clean beats were
  55/46/43/37; height-bin maximum was127.5 mmHg throughout and Gaussian
  center124.41/123.40/123.23/124.99 mmHg. With40-sample padding, height
  fit R2=0.842, first/last occupied bins57.5/157.5 mmHg, low/high tail
  ratios0.361/0.240, and14 occupied bins. Area fit was123.26 mmHg,
  R2=0.769. Both feature curves pass the study's diagnostic completeness
  gate; neither yields clinical or simulator-validated SBP/DBP.
- The stable offline MAP candidate and high-side coverage show that the old
  missing-upper-segment problem was addressed for this round. The production
  code's fixed80-100 mmHg MAP search excludes the candidate and selects a
  local post-transient maximum near83 mmHg. The evidence strongly supports
  algorithm selection as the immediate invalid-result mechanism. It does
  not independently establish the simulator pressure waveform, absolute MAP
  accuracy or the physical source of the valve-synchronous steps. Keep the
  firmware BP invalid; do not tune ratio/compensation from this single run.
- First vent/seal closed out within the short host gate, but sealed pressure
  later rebounded to3.4-3.7 mmHg. A second vent produced100 new0.0 mmHg
  samples; after seal, another100 new samples remained0.0. Independent export
  preflight `tmp/capture_preflight_20261028-223718.ndjson` confirmed valid
  calibration, ADS errors0, PC0/PC1 LOW, PC8 HIGH and pump OFF. The final
  state is sealed at zero. No wiring, supply, calibration, firmware, Keil
  project/image or pressure safety limit changed.
- Existing non-human wiring remained BP Pump 2 Pressure Port -> tee ->
  MPXV5050GP P1 and real External Cuff, sensor P2 vented; ADS1115 on
  PB6/PB7, USART3/CH340 on PB10/PB11, valve drivers PC0/PC1 and active-low
  pump relay PC8 with established common ground and supplies. Before any
  future power reconnection, check unpowered shorts/polarity, then measure
  the already verified supply and logic nodes before running. Before any
  later inflation, confirm sealed fresh zero, ADS/calibration, safe pins,
  capture capacity and a bounded abort path; close with vent -> fresh zero
  -> seal. No human contact is authorized by this simulator test. Keil
  compile/download is required only after future firmware edits, followed
  by calibration readback if full erase is used.
- Verification: full host suite97 tests passed; host control suite19 tests
  passed. No Keil build was needed because no firmware source changed.

## 2026-10-28 offline cross-check before MAP algorithm changes

- Re-ran the label-free height/area study on the13 earlier labeled complete
  captures using its original <130 mmHg range and40-sample step padding,
  then compared both high-target complete captures with the explicit
  <170 mmHg range. The earlier group results reproduced the recorded table:
  four120/80 candidates at93.39-97.84 mmHg, two100/65 candidates at
  78.58-78.96 (third unstable), two well-covered150/100 candidates at
  115.92-116.11, three other150/100 captures incomplete, and the
  unverified-label `120531` near79.21. This is a consistency check on
  saved exports, not independent validation or a new training set.
- The high-target comparison is not a matched replicate: `170426` was
  operator-confirmed Standard150/100 at target190 (preset pulse volume
  0.65 cc), whereas `223729` was operator-reported User Defined150/100,
  80 BPM,0.7 cc at target180. At step padding0/20/40/60, `170426` has
  clean-beat counts65/52/46/40, a142.5 mmHg strongest height bin but
  Gaussian centers124.42/117.57/117.37/117.21 mmHg. Every setting is
  `unstable_peak` because bin/fit disagreement exceeds7.5 mmHg. The
  40-sample curve has no occupied bin from77.5 through107.5 mmHg;
  the jump from72.5 to112.5 is a40 mmHg gap in coverage. It cannot serve
  as a confirming MAP replicate for the later capture.
- In `223729`, the height fit remains123.23-124.99 mmHg across padding
  0/20/40/60 and the bin maximum stays127.5 mmHg. However, that maximum
  bin contains only two retained beats. Removing each occupied bin in turn
  moves the40-sample fitted center from118.76 to125.14 mmHg. Requiring
  three beats per occupied bin leaves only six bins, fewer than the study's
  eight-bin minimum. The existing `diagnostic_only` status is therefore a
  research candidate with limited peak support, not robust evidence for a
  production MAP estimator.
- Offline design direction: retain the original-voltage cadence gate;
  detect per-beat height and area with recorded valve-step neighborhoods
  excluded; bin by pressure; report beat support, internal pressure gaps,
  tail coverage and leave-one-bin-out sensitivity before accepting any
  candidate. Keep failures explicit as insufficient/unstable, and preserve
  the original capture plus the firmware's invalid flag. Pressure-step
  exclusion alone can erase broad parts of an oscillogram, while retaining
  valve-correlated impulses can create a false peak. The current sample set
  does not justify choosing a new exclusion width or peak-support threshold
  by reference-label agreement.
- No firmware algorithm, pressure threshold, compensation, Keil image,
  simulator setting, wiring or device state changed in this read-only step.
  Before a firmware candidate is accepted, it needs complete independent
  non-human reference traces across all reference groups/modes, predefined
  quality gates and held-out captures, then a bounded RAM/CPU/stack review.
  A simulator-only result cannot establish human BP accuracy.

## 2026-10-28 host-only oscillogram robustness screen

- Extended the offline `bp_oscillogram_study.py` report for curves with at
  least eight occupied bins. It now includes the strongest bin's retained
  beat count, maximum adjacent occupied-bin pressure gap, and the range and
  maximum shift of Gaussian centers after removing each bin in turn. The
  independent exploratory screen rejects support <3 beats, gap >15 mmHg,
  or shift >7.5 mmHg. Existing `status` and BP validity are unchanged;
  `screen=pass` alone never means a complete or clinically valid result.
- At default40-sample step padding and upper bound170, User Defined target180
  export `223729` remains `diagnostic_only` but the screen rejects
  `weak_peak_support`: strongest bin has2 beats, maximum gap10 mmHg,
  leave-one-bin-out center118.76-125.14 mmHg, maximum shift4.47 mmHg.
  Standard target190 export `170426` remains `unstable_peak` and rejects
  all three checks: strongest bin2 beats, gap40 mmHg, center114.12-137.19
  mmHg, maximum shift19.82 mmHg. Neither is a firmware-ready MAP estimate.
- Re-ran all13 earlier labeled captures with original <130 mmHg range and
  the same40-sample padding. Of the previous `diagnostic_only` curves,
  `113752`, `114718`, `120941`, `123230` and uncertain-label `120531`
  pass this independent screen; `214442`, `220211`, `220714` reject sparse
  peak support and `115823` rejects jackknife shift8.06 mmHg. The old
  `unstable_peak`/`incomplete_oscillogram` statuses remain unchanged even
  where the independent screen passes. This small, mode-mixed batch cannot
  calibrate the thresholds or establish BP accuracy.
- Added synthetic tests for sparse peak, internal pressure gap and a
  supported curve, plus a compact regression from the verified `170426`
  height-bin medians for the jackknife instability path. The complete host
  suite passed99/99 tests; the independent host control suite passed19/19,
  and Python syntax checks passed. No device command, pressure, calibration, firmware C,
  Keil project/image or wiring changed; the pneumatic circuit remains
  sealed after the earlier verified zero-pressure closeout.

## 2026-10-28 matched non-human User Defined 180 mmHg repeat

- The operator confirmed the BP Pump 2 remained on the User Defined
  150/100 mmHg, 80 BPM, 0.7 cc, External Cuff simulation page and the
  cuff was fixed to a non-human mandrel. The cuff, tubing and fittings have
  no available model/pressure rating; earlier 180/190 mmHg survival is
  observed bench history, not a component rating or human-use clearance.
  Existing pneumatic and electrical connections were unchanged. No new
  supply-voltage or connector recommendation was made.
- Before start, a fresh five-second OmniProbe snapshot contained100/100
  pressure samples at0.0 mmHg. The host `--user-defined-180` preflight found
  cal VALID (82.326/-19.887), ADS ONLINE/errors0, manual OFF, PC0/PC1 LOW,
  PC8 HIGH and pump OFF. Exactly one start reached180.7 mmHg and stopped
  pumping; after the one-second hold, natural deflation captured2921/3300
  points, dropped0, span73000 ms at25 ms MCU intervals. The host ceiling
  remained195 mmHg and the acquisition deadline82 s. Raw bridge log:
  `tmp/linkpad_user_defined_180_20261028-231713.ndjson`.
- Firmware completed calculation with `calc=3`/invalid BP: MAP index1484,
  P86.2; SBP feature155.3 and DBP feature86.8 mmHg, again violating
  DBP < MAP. This repeats the immediate fixed80-100 mmHg selection/order
  failure without establishing reference BP accuracy. The first host
  cleanup vented and sealed, but a later five-second post-seal snapshot
  showed100 samples at3.6-3.8 mmHg. A second `vent` produced100/100 fresh
  0.0 mmHg samples; after `seal`, another100/100 fresh samples remained0.0.
- The first export preflight passed without a firmware-marker argument;
  `status` does not emit `sw=`, so a preliminary optional marker assertion
  failed despite valid calibration/ADS/pins/pressure. During the first
  export, ADS logged one I2C read failure (`errors=1`) and recovered
  (`recoveries=1`); the transfer stopped after point2473 and lacked
  valve/features/end. The host timed out and executed stop -> vent -> seal.
  `tmp/capture_export_20261028-232144.ndjson` is incomplete and must not
  be decoded as a full capture. This fault happened after the 2921-point
  acquisition, which remained stored in MCU RAM.
- A subsequent no-inflation preflight confirmed the retained2921 points,
  fresh sealed0.0 mmHg, cal VALID, ADS ONLINE with errors1/recoveries1,
  and safe pins. One retry exported a complete `/2` capture:
  `tmp/capture_export_20261028-232501.ndjson`, `.verified.ndjson`, `.csv`
  and `.replay.json`; hash1623361286, 366 valve pulses at200 ms with1-6 ms
  on-time, seven >=5 mmHg pressure falls all in the first25 ms phase bin.
  Strict decode and production-C replay matched all envelope/feature bits
  and invalidity, with zero array error. The export `begin` confirms
  `CAPTURE_COMPACT_20261028`; the optional `sw=` status assertion is not
  needed for this image check. Final five-second sealed snapshot had
  101/101 new0.0 mmHg samples. No further inflation occurred.
- Compared with the earlier same-reported-setting target180 export `223729`,
  both traces begin deflation near165.5 mmHg, end near14.6 mmHg, retain
  exactly25 ms ticks and estimate80 BPM. The first took64.2 s/2569 points
  (mean2.351 mmHg/s); the repeat took73.0 s/2921 points
  (mean2.065 mmHg/s). At the predefined40-sample step padding and
  <170 mmHg upper bound, the first height fit is123.23 mmHg with a
  two-beat peak bin and `robustness=reject`; the repeat fit is117.02 mmHg
  (R2=0.863), strongest bin122.5 mmHg with four beats, maximum occupied
  gap15 mmHg and jackknife shift1.28 mmHg, so `robustness=pass`.
  Across padding0/20/40/60 the repeat fit is118.32/117.24/117.02/117.04
  mmHg and all four screens pass. The two fitted centers differ6.21 mmHg
  at the same default setting. Slower deflation provides more retained
  beats, but the cause of rate/curve variation is unproven with one pressure
  channel and operator-reported panel state. Neither offline MAP candidate
  is a reportable SBP/DBP or a clinical accuracy result.
- Existing STM32 PB6/PB7 ADS1115/MPXV5050GP, PB10/PB11 USART3/CH340,
  PC0/PC1 valves, PC8 pump relay and BP Pump 2 Pressure Port/tee/real
  external cuff path remained in place with established supplies and
  common ground. Before any future power reconnection, check unpowered
  shorts/polarity, then established supply/logic levels. Before any later
  non-human inflation, confirm sealed fresh zero, ADS/calibration, safe
  pins and bounded abort; close with vent -> fresh zero -> seal. No
  firmware source, Keil image or safety limit changed, so no Keil
  compile/download or calibration rewrite occurred this round.

## 2026-10-28 pressure-band and export-fault attribution

- Read-only comparison of the two verified User Defined target180 exports
  `223729` and `232501`. Pressure thresholds were located on a centered
  41-sample (~1 s) median-filtered version of each original40 Hz pressure
  trace; these crossing times are diagnostics, not new capture data. From
  160 to120 mmHg, the first run took11.27 s (3.55 mmHg/s) and the repeat
  took20.47 s (1.95 mmHg/s). From120 to20 mmHg, they took48.43 and
  48.30 s respectively (both ~2.07 mmHg/s). Thus the ~8.8 s whole-capture
  difference is concentrated above120 mmHg, especially 140-to-120
  (4.83 vs12.30 s). It is not evidence of a uniform deflation slowdown.
- At default40-sample pressure-step exclusion, high-side occupied beat bins
  in the first run include127.5/137.5 mmHg with2 beats each; the repeat
  includes122.5/127.5/132.5/137.5 mmHg with4/3/4/5 beats. The extra
  high-pressure residence supplies more per-bin evidence and helps explain
  why the repeat passes the exploratory robustness screen while the first
  fails peak support. It does not alone prove the fitted MAP difference
  (123.23 vs117.02 mmHg) is physiological or a specific simulator effect.
  Both exports record200 ms valve periods and1-6 ms overall on-time, but no
  per-pulse on-time history; no separate reference-pressure trace exists.
  The cause of the high-band rate variation remains undetermined.
- The first `232144` export stopped at point2473/2921; the last point and a
  new pressure-read failure share the same host timestamp. The saved
  diagnostic was `stage=5`, `status=1`,
  `reg=0x01`, `err=0x00000004`, HAL state0x20, SR1=0 and SR2=0x0003.
  In this source, stage5 is the I2C transmit that starts an ADS1115 single
  conversion; HAL error0x4 is AF/NACK, while state0x20 is READY at the
  snapshot. The stream path clears the fresh-pressure flag, and the main
  loop's `CaptureExport_IsSafe()` cancels an active export without an end
  record. The host continued waiting for its100 s export deadline because
  cancellation has no explicit terminal record. The observed `Init OK`
  came997 ms after the failure; later diagnostics showed
  errors1/recoveries1, and the retained2921-point capture exported on the
  next safe attempt. This is one transaction-level failure and a confirmed
  safe export-cancellation path, not proof of a failed ADS1115, bad wiring,
  a general export-load defect or capture loss. The incomplete transfer
  must never be merged with the complete retry. The strict decoder rejects
  `232144` with `no complete capture end`.
- No further serial command or pneumatic operation occurred during this
  analysis. The last observed post-seal pressure snapshot remained at
  0.0 mmHg. A future host-only improvement could detect an ADS read-failure
  event during export and terminate promptly, while preserving the same
  fresh-low/seal gate for a later retry; do not mask an incomplete transfer
  or relax the target safety predicate.

## 2026-10-28 host export failure reporting

- `tmp/linkpad_capture_io.py` now retains `[Pressure] sample failed` as a
  diagnostic and stops a pending export when a pressure/stream read failure
  has a bridge timestamp at or after that export command. The event-list
  position and timestamp both exclude old diagnostics, including queued
  messages delivered after the command. A complete `end` still takes the
  strict decode path first; incomplete files remain invalid. The existing
  exception closeout remains stop -> vent -> fresh low -> seal, and a later
  retry must pass the full post-seal preflight again.
- Four focused offline tests cover diagnostic retention, old-event exclusion,
  queued-old-event exclusion and new-failure detection. The full host suite
  passed 99/99; the control-script and new export-helper tests passed 23/23;
  `py_compile` passed. The saved `232144` bridge log shows the export command,
  point2473 and `[Pressure] sample failed` in one text batch, followed by
  `[Stream] read failed` in the next batch, with no `end`. This verifies the
  event format used by the host filter; the revised path was not exercised
  against live hardware.
- Wiring and validation boundary: the existing STM32 PB6/PB7 ADS1115 sensor
  path, PB10/PB11 USART3 bridge, PC0/PC1 valve outputs, PC8 pump relay, and
  BP Pump 2 external cuff circuit are unchanged; established power and common
  ground remain as previously documented. No reconnection, power change,
  Keil compile/download or calibration rewrite is needed for this host-only
  change. Before any later non-human run, check unpowered shorts/polarity,
  then established supply/logic levels; confirm fresh sealed zero, ADS/cal,
  safe pins and a bounded abort. Observe the serial failure diagnostic and
  incomplete export rejection, then close with vent -> fresh zero -> seal.
  This edit issued no device command or inflation. The last observed physical
  state remains sealed at 0.0 mmHg; it was not remeasured here.

## 2026-10-29 export failure-path replay and zero-pressure board check

- Added a fake-bridge integration test that feeds the two failure lines from
  `tmp/capture_export_20261028-232144.ndjson` through the real host `main()`
  export loop. It raises on the first fresh `[Pressure] sample failed` within
  one simulated second of `capture export`, emits no success result, and
  executes `stop` -> `vent` -> fresh zero -> `seal`. The saved incomplete
  transfer itself is rejected by the strict decoder with `no complete capture
  end`. The failure path was not deliberately induced on the live device.
- Full host suite passed 99/99, control and export-helper suite 24/24, and
  `py_compile` passed. A five-second read-only live snapshot before export had
  100/100 fresh 0.0 mmHg samples. Host preflight reported cal VALID
  (82.326/-19.887), ADS ONLINE, manual OFF, safe PC0/PC1/PC8 pins and pump
  OFF. The one no-inflation export of the retained 2921-point capture completed
  with `/2` end hash1623361286 and passed the host strict decoder:
  `tmp/capture_export_20261029-001116.ndjson`. Its n2921/duration73000ms
  matches the prior successful export. The log contains only `status`, `pins`,
  `cal`, `fault` and `capture export` commands, with no actuator command.
- A second five-second read-only snapshot after export again had 100/100
  fresh 0.0 mmHg samples. The preflight pins were sealed; the successful
  export sent no valve command, so no vent/seal cycle was needed. Existing
  PB6/PB7 ADS1115, PB10/PB11 USART3, PC0/PC1 valves, PC8 pump relay,
  external BP Pump 2/cuff circuit, power and common ground were unchanged.
  This host-only verification required no Keil compile/download. Any future
  pneumatic test must first use the established unpowered polarity/short
  check, established powered-level check, non-human fixture, fresh sealed
  zero/ADS/cal/pins gate and bounded abort; complete it with vent -> fresh
  zero -> seal.

## 2026-10-29 zero-pressure repeated-export attempt

- The planned three no-inflation exports could not proceed because the current
  MCU reports `[Capture] n=0 capacity=3300 dropped=0`; the earlier 2921-point
  RAM capture is no longer present. The cause of its disappearance was not
  observed; a power cycle/reset or another reset path cannot be distinguished
  from this check alone. No stored data was overwritten by this attempt.
- Before the first attempt, a read-only five-second bridge snapshot had
  100/100 fresh 0.0 mmHg samples. The export script preflight passed cal VALID
  82.326/-19.887, ADS ONLINE, manual OFF, PC0/PC1 LOW, PC8 HIGH, pump OFF,
  and zero pressure; ADS counters were errors0/recoveries0. The MCU rejected
  `capture export` as empty. The host issued stop -> vent -> fresh zero ->
  seal, raised `Export rejected`, and did not create a complete capture.
  Evidence: `tmp/capture_export_20261029-103539.ndjson`.
- After closeout, another five-second read-only snapshot had 100/100 fresh
  0.0 mmHg samples. A diagnostic-only host preflight confirmed PC0/PC1 LOW,
  PC8 HIGH, pump OFF, cal VALID, ADS ONLINE, errors0/recoveries0, and n0;
  evidence: `tmp/capture_preflight_20261029-103615.ndjson`. No inflation or
  BP Pump 2 operation occurred. The remaining two exports were not attempted
  because repeating an empty-buffer rejection would not test export
  stability. A new non-human acquisition would be required before that
  specific three-export test can resume. Existing wiring, supplies, common
  ground and Keil image were unchanged; no compile/download was needed.

## 2026-10-29 new non-human capture and three repeated zero-pressure exports

- The operator reconfirmed BP Pump 2 User Defined 150/100 mmHg, 80 BPM,
  0.7 cc, External Cuff readiness and a non-human fixed cuff. A fresh
  read-only snapshot gave 101/101 samples at 0.0 mmHg; host preflight found
  cal VALID 82.326/-19.887, ADS ONLINE/errors0/recoveries0, manual OFF,
  PC0/PC1 LOW, PC8 HIGH, pump OFF. Existing wiring, supplies and common
  ground were unchanged. One `--user-defined-180` acquisition used target
  180 mmHg, observed-pressure ceiling 195 mmHg and 82-second natural
  completion deadline. Peak was 181.3 mmHg; natural deflation retained
  2753/3300 points, dropped0, span68800ms at 25ms intervals. Firmware
  reported 148/90, 75bpm, valid1; this is simulator output, not a clinical
  reference result. Evidence: `tmp/linkpad_user_defined_180_20261029-103915.ndjson`.
- Acquisition cleanup issued stop -> vent -> fresh low -> seal, restored
  target50, and confirmed safe pins and ADS0/0. The first sealed snapshot
  rebounded to3.0-3.6mmHg, so export was held. A second vent produced
  100/100 fresh0.0mmHg samples; immediately sealing and observing another
  five seconds gave100/100 fresh0.0mmHg. No second inflation occurred.
- Three separate export invocations passed the full host preflight and strict
  `/2` decoder: `tmp/capture_export_20261029-104132.ndjson`,
  `tmp/capture_export_20261029-104258.ndjson`, and
  `tmp/capture_export_20261029-104420.ndjson`. Each has begin, 2753 ordered
  points, valve/features, complete end, hash4167954805 and duration68800ms.
  Independent strict decoding of all three files yielded identical objects.
  After rounds1/2/3, each five-second read-only snapshot had100/100 fresh
  0.0mmHg samples; diagnostic preflights confirmed the same n2753, sealed
  PC0/PC1 LOW, PC8 HIGH, pump OFF and ADS errors0/recoveries0. The three
  exports sent no actuator commands. Final evidence:
  `tmp/capture_preflight_20261029-104532.ndjson`.
- The first export additionally produced `.verified.ndjson`, `.csv`, and
  `.replay.json` via `bp_capture.py`. Offline production-C replay matched
  envelope and feature bits and validity exactly, with zero envelope/smooth
  array error; n2753 and all MCU intervals25ms were preserved. This checks
  data/replay integrity and does not turn the simulator result into validated BP.
- This establishes successful repeated readout of one retained capture under
  zero pressure; it does not establish that the earlier single I2C AF/NACK
  cannot recur or identify its physical cause. No firmware source, Keil
  project/image, calibration, pressure limit, or wiring changed, so no Keil
  build/download was needed. Before any further non-human pneumatic test,
  recheck unpowered shorts/polarity then established powered levels, fixture,
  fresh sealed zero, ADS/cal/pins and abort bounds; close with vent -> fresh
  zero -> seal. Connected cuff/tubing/fitting pressure ratings remain
  undocumented; no pressure above this run was attempted.

## 2026-10-29 matched User Defined 180 offline feature comparison

- Read-only comparison of three complete `/2` captures with operator-reported
  User Defined 150/100 mmHg, 80 BPM, 0.7 cc, External Cuff and firmware marker
  `CAPTURE_COMPACT_20261028`: `223729` (2569 points), `232501` (2921), and
  `20261029-104132` (2753). Strict decoding and production-C replay matched
  capture features/envelopes and validity. All have exact25ms MCU intervals,
  begin deflation near165.4-165.6mmHg and end near14.6-14.8mmHg; the offline
  label-free pulse estimator returns80bpm for all three. The panel setting
  was user-confirmed, not electronically recorded in the capture metadata.
- Pressure-band crossing times used a centered41-sample (~1s) median of the
  original40Hz pressure trace, with linear crossing interpolation. The
  160->120mmHg times/rates were11.29s/3.54mmHg/s,20.47s/1.95mmHg/s,
  12.54s/3.19mmHg/s respectively. The120->20mmHg times/rates were
  48.42s/2.07mmHg/s,48.31s/2.07mmHg/s,51.93s/1.93mmHg/s. High-pressure
  residence varies substantially despite similar endpoints and identical
  firmware; its physical origin cannot be assigned to BP Pump 2, valve or
  cuff without an independent simultaneous reference-pressure trace.
- Production C deliberately restricts MAP selection to80-100mmHg. It chose
  index1131/P83.21, index1484/P86.23, and index1111/P97.63mmHg. The first
  two exports have `calc=3`: DBP threshold points came only13/15 samples
  (0.325/0.375s) after MAP at raw P83.56/P86.80mmHg, i.e. +0.35/+0.57mmHg
  above the MAP sample, so the `dbp > map_pressure` hard gate rejected them.
  A centered41-sample pressure median at these MAP/DBP indices is
  83.86->83.80 and86.97->86.77mmHg, showing the inversion is on a small
  raw-pressure ripple while the threshold crossing itself is implausibly
  near the MAP peak. The third capture has `calc=2` and raw DBP P95.43,
  only21 samples/0.525s after MAP97.63, so the same gate passes; firmware
  reports148/90,75bpm valid1. Passing this gate is not an independent
  waveform-quality or clinical-accuracy result.
- The existing independent beat-height analysis (`upper_pressure=170`,
  40-sample exclusion around >=5mmHg pressure steps) gives fitted MAP
  candidates123.23,117.02,122.60mmHg. They are not interchangeable with
  firmware MAP or a reference BP. The first/third are rejected for peak-bin
  support of only2 beats; the third also has10.26mmHg maximum leave-one-bin-
  out shift and an incomplete upper tail at this exclusion setting. The
  second passes its exploratory robustness screen (4 beats at peak,1.28mmHg
  jackknife shift). Across step padding0/20/40/60, the third fitted center
  stays122.25/122.34/122.60/122.69mmHg, but quality rejects at every
  setting. Its apparent stability does not overcome missing peak support.
- Direct cause of the two invalid flags is the fixed-window MAP/near-immediate
  DBP threshold and raw-pressure ordering check in the production algorithm;
  the third `valid1` shows that this binary check is not a reliable quality
  screen. The independent pulse-shape evidence suggests the selected
  80-100mmHg feature is below the main beat-height region in these three
  traces, but the candidate itself is not validated against an independent
  pressure reference. Do not tune MAP window, SBP/DBP ratios or compensation
  to these three labels. Next software work should remain offline: define
  beat support, pressure coverage, tail and temporal-separation rejection
  gates on separate held-out captures, then assess MCU memory/time/safety
  before any firmware algorithm change. No device command or inflation was
  performed for this comparison.

## 2026-10-29 reproducible retained-capture batch audit

- Added the read-only `blood pressure monitor/tools/bp_capture_batch_report.py`
  and generated `capture-batch-audit.md` in this task directory. The script
  enumerates sorted `tmp/capture_export_*.verified.ndjson`, strictly decodes
  each complete export, records the input-byte SHA-256, and reuses the existing
  40-sample step-padding beat-height study. Its upper bin bound is 170 mmHg
  when the first sample is >=150 mmHg, otherwise 130. It reconstructs the
  first three-point 60%-of-MAP-smoothed-envelope DBP crossing and asserts its
  pressure bits equal the exported DBP feature.
- All 28 archived verified exports decoded. States: 17 firmware valid, 10
  firmware invalid and 1 uncalculated. Two invalid exports have no DBP
  feature; among the other 25, 22 MAP-to-DBP gaps are <=0.75 s: 14/17 valid
  and 8/8 invalid-with-DBP. All eight invalid-with-DBP captures show raw
  DBP pressure above MAP. This identifies a recurrent threshold-timing and
  pressure-order issue, but 0.75 s is one 80-BPM beat, not a validated
  rejection cutoff. The independent beat-height quality screen disagrees
  with firmware validity on individual captures; neither result establishes
  a clinical BP estimate.
- These are historical, selected, mode-mixed captures that were already used
  during exploration. The export does not encode BP Pump 2 panel settings or
  an independent reference pressure trace. They cannot be described as a
  held-out validation set, used to select new MAP/SBP/DBP constants, or used
  to attribute high-band variation to hardware versus the simulator.
  Freeze the next analysis rules before collecting a separate labeled set;
  include independent pressure evidence if attribution or accuracy is the
  question. This audit issued no serial/bridge command, inflation, valve
  action, calibration write, firmware edit, or Keil download. Last observed
  device state remains the earlier sealed, near-zero state, not remeasured
  in this offline pass.
- Verification: Python syntax check passed; the script decoded all 28 files,
  produced 28 table rows, and reproduced the known three high-target feature
  pressures/timings. After prospective captures were added, the report CLI
  gained inclusive `--through 20261029-104132` so the same 28 archived
  inputs remain reproducible. The final frozen report SHA-256 is
  `2B402240EF289FD71AD40A0B810C8D4DD1A1AF5D8AD0125BBECB3ED948DA9CFF`.
  No Keil build/download is needed for this host-only script; no `.c`/`.s`
  source was added or moved, so the Keil project source list is unchanged.
- Wiring/physical validation boundary: this offline command reads saved
  NDJSON only. For any later non-human recapture, retain the documented
  STM32 PB6/PB7 I2C1-to-ADS1115 pressure sensor, PB10/PB11 USART3 bridge,
  PC0/PC1 valve controls, PC8 pump relay and External Cuff/BP Pump 2 path;
  follow the existing wiring plan for module power and common ground, with
  no new voltage or connector assumption. Before power, verify polarity,
  continuity and absence of shorts; after power, measure the established
  supply/logic points. Before inflation, require a fixed non-human cuff,
  sealed fresh near-zero serial pressure, valid ADS/calibration, safe pins,
  pump OFF and a bounded abort. During capture, observe the serial pressure,
  dropped count and complete export hash; expected offline result is strict
  decode and a deterministic report. Close any pneumatic run with `vent` ->
  fresh near-zero samples -> `seal`. This increment did not exercise that
  physical sequence and makes no human-use claim.

## 2026-10-29 prospective non-human matched waveform pilot

- Locked a three-slot protocol before P1 (`prospective-waveform-protocol-20261029.md`,
  SHA-256 `CDFD3E315F1C776AC9D6AF5E9A317AA015AC29C66759930BF46A9BC2B7CA8730`).
  The operator reconfirmed the unchanged 150/100 mmHg, 80 BPM, 0.7 cc,
  External Cuff setting and fixed non-human cuff. All three planned slots
  P1/P2/P3 were acquired in order at target180; no slot was selected or
  replaced based on its result. Full file paths, hashes and metrics are in
  `prospective-waveform-results-20261029.md`.
- Acquisitions peaked at180.3/180.6/180.4mmHg, captured2761/2889/2673 of3300
  samples with dropped0, and had exact25ms MCU intervals. Each complete `/2`
  export passed strict FNV/count/order decoding and bit-equal production-C
  replay for envelopes, features and validity. The frozen research screen
  returned `diagnostic_only` plus robustness `pass` on all three. Fitted
  height-curve peaks were118.26/119.26/119.88mmHg, range1.62mmHg, meeting
  the prespecified 3/3 and <=7.5mmHg repeatability condition for this one
  simulator setting. All strongest bins had only the minimum three beats.
- Firmware reported147/93/84,149/82/75,149/82/75 (SBP/DBP/BPM), all valid1.
  Raw MAP features were99.81/95.22/99.04mmHg, while label-free cadence was
  80BPM in each. This is internal waveform repeatability, not MAP truth,
  SBP/DBP accuracy or a firmware-ready parameter fit. No independent
  simultaneous pressure reference exists; no MAP bounds, ratios or offsets
  were changed. The three MAP-to-DBP times were1.150/3.450/3.625s; the old
  exploratory 0.75s diagnostic remains non-normative.
- Before the protocol freeze, the host 180mmHg mode's observed-pressure abort
  line was tightened from195 to190mmHg, matching the previously accepted
  operating limit; 20/20 fake-bridge tests and syntax checks passed. The
  sampled host line is not a hard peak guarantee. The optional `--firmware`
  export preflight failed once because current status omits `sw=`; it sent
  no export command, safely vented/sealed, and the same P1 RAM capture was
  exported after fresh post-seal zero and verified by its begin marker.
- After each natural run, the first seal rebounded near4mmHg, so export was
  held. Each second vent -> 100 fresh zero samples -> seal -> 100 fresh zero
  samples passed before export. Final read-only preflight found fresh0.0,
  sealed PC0/PC1 LOW, PC8 HIGH, pump OFF, cal VALID, ADS ONLINE and errors0.
  Existing wiring, supplies, ground, firmware C, Keil project/image and
  calibration were unchanged. No human test or target190 repeat occurred.
  Future hardware work follows the non-human wiring, power, safety and
  vent/seal gate recorded in the results file.
- Quality check after the three runs: the relevant host control/export suite
  passed25/25, the complete firmware host suite99/99, and Python syntax
  checks passed. The capture-export code-spec now records the190mmHg sampled
  host abort boundary and the optional `--firmware` status-field mismatch.
  After the P3 protocol-hash check, the batch-report CLI alone gained an
  archive cutoff; its `inspect()`/oscillogram calculations did not change.
  The pre-P1 hashes and prespecified outcomes remain documented in the
  locked protocol and results. The active task is still in progress; no
  Keil rebuild or download was needed for host-only changes.

## 2026-10-29 prospective 100/65 series prepared, awaiting panel confirmation

- Locked `prospective-low-waveform-protocol-20261029.md` before any L1 capture;
  SHA-256 `4ACBF5BFFB7466CC9AEAEF977FC2910C246F649BAE9AB684939543D8AFFDD05F`.
  It prespecifies three sequential User Defined100/65,80BPM,0.7cc External
  Cuff non-human captures at target150, the unchanged 40-sample/130mmHg
  beat-height screen, a 3/3 and <=7.5mmHg within-condition criterion, and
  a strict nonoverlap comparison against the already frozen 150/100 cohort.
  This comparison can test fixture-specific waveform discrimination only.
- Read-only five-second bridge snapshot contained101/101 fresh est0.0mmHg.
  Diagnostic preflight `tmp/capture_preflight_20261029-114850.ndjson` found
  sealed PC0/PC1 LOW, PC8 HIGH, pump OFF, cal VALID82.326/-19.887, ADS
  ONLINE errors/recoveries0/0 and93 fresh zero readings. Host control/export
  tests passed25/25. The BP Pump 2 panel has no machine-readable setting
  in this bridge; the operator has not yet explicitly confirmed that the
  requested100/65 condition is set. No `target`, `start`, valve or pump
  command was sent for this new series. The retained P3 buffer remains
  2673/3300 points, and the last observed state is sealed at0.0mmHg.

## 2026-10-29 prospective 100/65 non-human pilot outcome

- The operator replied "OK" to the explicit100/65,80BPM,0.7cc, External
  Cuff and non-human fixture confirmation. The panel state cannot be read
  electronically. The three locked slots L1/L2/L3 were acquired in order
  at target150 and peaked151.5/151.1/151.4mmHg. They retained2249/2193/2345
  points, dropped0, exact25ms MCU ticks. All three complete `/2` exports
  passed strict decoding and bit-equal production-C envelope/feature/validity
  replay. See `prospective-low-waveform-results-20261029.md` for paths,
  per-export hashes and full decision.
- Frozen beat-height screening returned `diagnostic_only` plus robustness
  `pass` for L1/L3, fitted peaks79.49/79.97mmHg. L2 returned
  `insufficient_bins`: 24 retained clean beats and six occupied bins, below
  the required eight. The study's label-free pulse estimate was80BPM in
  all three. Firmware produced119/60/70, invalid,121/70/56 respectively;
  L2 raw DBP86.64 exceeded MAP86.13mmHg by0.51 at0.575s.
- Prespecified lower-condition success was2/3, so the required 3/3
  repeatability claim failed and the conditional six-curve nonoverlap
  test against the 150/100 cohort was not run. The two passing fits
  cannot substitute for the failed slot. Six >=5mmHg pressure steps and
  only six bins in L2 explain the filter rejection; source attribution
  remains unresolved. No firmware BP accuracy or clinical inference follows.
- Each first seal showed residual3.0-3.9mmHg, so export was held. Second
  vent ->100 fresh0.0 samples -> seal ->100/101/100 fresh0.0 samples
  enabled the three exports. Final diagnostic preflight
  `tmp/capture_preflight_20261029-120704.ndjson` found sealed safe pins,
  pump OFF, cal VALID, ADS ONLINE/errors0/recoveries0 and92 fresh0.0mmHg
  readings. The existing wiring/power/ground, calibration, firmware C,
  Keil project/image and 150mmHg target-mode safety bounds were unchanged.
  No further inflation was performed after L3.
- Separate post hoc sensitivity (not part of the locked 2/3 verdict): L2
  step padding0/20/40/60 retained36/28/24/20 clean beats and13/6/6/6
  occupied bins. Only padding0 passed, with fitted peak77.39mmHg; changing
  padding after seeing L2 cannot rescue the prespecified result. All six
  >=5mmHg pressure falls occurred in phase bin0 of the200ms valve schedule.
  This narrows the software rejection mechanism to step-adjacent beat
  exclusion, while physical attribution remains unproven.

## 2026-10-29 read-only 100/65 step audit

- Re-ran `blood pressure monitor/tools/bp_step_audit.py` on the three
  strict-verified L1/L2/L3 exports. Script SHA-256
  `9DBFFA2395096711E19164983FC66E9D7B694E46CC36D910168A9120777C5220`;
  complete command, input hashes, step table and limits are in
  `low-waveform-step-audit-20261029.md`. Python syntax check passed.
- In the 50-130mmHg band, samples within +/-40 points of a >=5mmHg step
  were L1 0/1404, L2 405/1403 and L3 49/1533. L2's six falls occurred
  14.4/16.8/20.4/22.8/33.4/40.0s after capture start and each partially
  recovered at the next 25ms point. Four were in the 107-81mmHg region.
  At fixed padding40, L2 retained24 clean beats and only six bins;
  padding0/20/40/60 gave36/28/24/20 beats and13/6/6/6 bins.
- `p` and `v` in all three `raw_kind=2` exports obey the same saved affine
  pressure calibration (maximum residual 0.00001mmHg), so they are not two
  independent sensors. The software filter's rejection is explained by
  step-adjacent exclusion, but the physical source is unresolved without
  synchronized independent pressure or per-pulse valve timing. The locked
  2/3 failure and unperformed six-curve comparison remain unchanged.
  This audit sent no device command, made no firmware or Keil change, and
  did not reassess the board's current live pressure or valve state.

## 2026-10-29 bounded step-trace software gate

- `bp.capture/3` now exports the earliest 12 >=5mmHg step associations
  (sample index, phase since actual valve open, commanded on-time); the
  aggregate retains the full step count. If steps exceed 12, later timing
  is unavailable. Earlier `/1` and `/2` captures remain readable. This
  does not change actuation or BP result arithmetic.
- Real-C export/strict decoder tests 15/15 passed; the full firmware host
  suite 102/102 and capture-bridge tests 5/5 passed. Python syntax checks
  passed. Keil ARMCLANG rebuild produced 0 errors, 0 warnings. Static RAM
  63472/65536 B, headroom2064 B (only 16 B above the 2048 B gate),
  reserved stack4096 B, known callgraph peak1312 B plus1024 B reserve.
  `bp_algorithm.c` and `bp_capture_export.c` are present in the Keil project;
  no new compiled source was added. HEX SHA-256
  `C5698327B557882934BE19102CC9BD420D2AA825885D49346ADED0D231F7A1DB`.
- This is a software result only. No new image has been downloaded and no
  pressure, valve or pump action was performed for this increment yet.
  A non-human board check and current live state preflight remain open.

### Non-human wiring and board validation gate

1. Keep the established MPXV5050GP -> ADS1115 A0 path, ADS1115 on STM32
   I2C1 PB6/PB7, USART3 PB10/PB11 through the existing CH340 debug path,
   PC0/PC1 valve outputs, PC8 active-low pump relay and SWD PA13/PA14.
   Preserve the previously verified supply connections and common ground;
   introduce no new voltage or module connection. After any reconnection,
   check unpowered shorts/polarity first, then measured supply/logic levels.
2. Before a non-human cuff run, require sealed PC0/PC1 LOW, PC8 HIGH,
   pump OFF, fresh serial pressure near zero, ADS ONLINE, cal VALID with
   82.326/-19.887 readback and no new fault. Download the zero-warning
   Keil image through the established `UV4 -f` SWD path only after this
   safe-state gate. Full-chip erase may clear calibration: restore the
   documented current coefficients and read back before any inflation.
3. Keep the confirmed External Cuff non-human fixture, target and host
   overpressure/freshness aborts from the locked protocol. After the run,
   `vent` -> fresh near-zero samples -> `seal`, then verify new sealed-zero
   readings before `capture export`. Expect a `/3` begin, 25ms point rows,
   a valve summary with `trace_n`, ordered step rows and a valid FNV end.
   Review the phase/on-time for each step; if `steps>trace_n`, label the
   trace truncated. Do not make clinical or physical-cause claims from
   one instrumented capture.

## 2026-10-29 instrumented non-human 100/65 run

- Pre-download safe state: sealed PC0/PC1 LOW, PC8 HIGH, pump OFF,
  cal VALID82.326/-19.887, ADS ONLINE and93 fresh0.0mmHg samples. Keil
  `UV4 -f` caused `UNCAL` as expected after full erase; restored only the
  current 82.326/-19.887 calibration, then read back VALID and92 fresh0.0.
- One exploratory User Defined100/65,80BPM,0.7cc, External Cuff run used
  target150/host abort165 and peaked152.0mmHg. Natural capture n2201/3300,
  dropped0, duration55000ms, exact25ms ticks; board120/68,33BPM valid1.
  Its panel setting was previously operator-confirmed, not electronically
  read back. It is L4 exploratory and does not replace locked L2.
- First sealed closeout rebounded3.7-3.8mmHg; export was held. Second
  vent gave100 fresh0.0 samples, then seal gave92 fresh0.0 samples.
  Complete `/3` export n2201/FNV3839623589 contained276 real valve-open
  commands at200ms, on-time1-6ms, seven >=5mmHg steps and trace_n7.
  Six pressure falls occurred at phase23ms after PC1-open commands,
  on-time5-6ms; one next-point rebound was at phase48ms. Strict decode
  and production-C replay passed with bit-equal envelope/features/validity.
- Locked 40-point step exclusion left32 clean beats,11 bins and79.50mmHg
  diagnostic fit, but robustness rejected due to only two beats in the
  strongest bin. Label-free cadence80BPM versus firmware33BPM requires
  separate algorithm work. Phase alignment supports valve-synchronous
  disturbance but cannot separate pneumatic, electrical and sensing
  mechanisms from this one pressure channel. Full evidence and hashes:
  `step-trace-board-result-20261029.md`. Final read-only preflight found
  sealed safe pins, ADS ONLINE/errors0/recoveries0, cal VALID and93 fresh
  0.0mmHg samples; no further inflation followed.
- A read-only phase audit of the complete `/3` export reconstructed the
  200ms schedule and checked all seven recorded event phases. In the
  50-130mmHg band, 172 cycles had a sample 23ms after PC1-open: median
  adjacent change -0.937mmHg, with five falls >=5mmHg. The other seven
  25ms phases had no such fall. The following sample's median change was
  +0.248mmHg; the two-sample median net was -0.760mmHg, with no >=5mmHg
  net fall. This strengthens evidence for a valve-synchronous notch,
  while its physical origin remains unresolved. The command and script
  hash are in `step-trace-board-result-20261029.md`.
- The same phase audit on archived strict-verified `/2` L2/L3 exports
  matched all aggregate >=5mmHg phase bins. In-band first-phase changes
  were L2 n176/median -0.845mmHg/five >=5mmHg falls and L3
  n192/median -1.079mmHg/one >=5mmHg fall, versus exploratory L4
  n172/median -0.937mmHg/five >=5mmHg falls. `/2` anchors come only
  from each run's aggregate maximum fall, without per-event on-time;
  L1 has no such event and cannot be phase-anchored from its export.
  No new hardware action was taken for this cross-run analysis.

## 2026-10-29 sealed-zero pulse check

The user-confirmed non-human fixed setup passed the live zero-pressure,
calibration, ADS and safe-pin gate. The `ZERO_PULSE_DIAG_20261029` image was
built with zero Keil errors/warnings and 2064 B static RAM headroom, then
downloaded by Keil. Full erase cleared calibration, so only the current
82.326/-19.887 coefficients were restored and read back. One bounded
zero-pressure 5ms/200ms run completed 25 pulses and 200 samples with no
drops. Strict `/3` export and a phase audit of unclipped sensor voltage
found only 0.0426 mmHg equivalent peak-to-peak variation; no high-pressure
5-9 mmHg notch reproduced. Vent/fresh-zero/seal closeout and the later
runtime stack/safe-pin preflight passed. This weakens a fixed pressure-
independent electrical-coupling explanation but does not establish a
pneumatic root cause. Full method, hashes, wiring and limitations are in
`zero-pulse-board-result-20261029.md`.
