# Hardware Map

## MCU And Power

- MCU: STM32F103ZET6.
- System clock: HSE 8 MHz, PLL x9, SYSCLK 72 MHz.
- 12 V powers the pump and valve drive path.
- LM2596S-ADJ converts 12 V to 5 V.
- AMS1117 converts 5 V to 3.3 V for STM32, ESP8266, ADS1115, and logic devices.

## Pressure Chain

- Current sensor: MPXV5050GP gauge pressure sensor, 0-50 kPa (about
  0-375 mmHg), with P2 open to ambient. The old MPXV7007DP +/-7 kPa path
  was replaced and its 40 mmHg bench restriction no longer applies.
- Current measured hardware calibration is `82.326 mmHg/V` and
  `-19.887 mmHg` from `calibration_data/manual_static_2026-10-25.json`.
  Full-chip erase clears the Flash record; restore and read back the same
  values before pressure operation. This record is specific to the current
  MPXV5050GP/divider/supply assembly.
- Sensor output is divided before ADS1115 A0 because ADS1115 is powered at 3.3 V.
- ADS1115 address is `0x48` with ADDR tied to GND.
- ADS1115 uses I2C1: PB6 = SCL, PB7 = SDA.
- ADS1115 ALRT/DRDY is mapped to PB5 / EXTI5.
- Current pressure conversion logic lives in `Core/Inc/ads1115.h` and `Core/Src/ads1115.c`.
- Standalone diagnostics use one AIN0 single-shot conversion at a time and poll the
  ADS1115 OS-ready bit with a bounded timeout; they do not depend on PB5/ALRT.
- The fitted divider measured 6.823 kohm from sensor OUT to A0 and 17.96 kohm
  from A0 to GND on 2026-08-25. Firmware uses the resulting 1.37990 reconstruction
  scale. Raw, ADS voltage, and reconstructed sensor voltage are acquisition-valid;
  pressure uses the verified Flash calibration above when the firmware reports
  `VALID`. This calibration alone is not clinical accuracy validation.

## Actuators

- Inflation-path valve control: PB8, represented by `VALVE1_CTRL_Pin`.
  Open-drain, no internal pull, active LOW: LOW energizes the relay/open path;
  SET releases the pin and the relay input pulls it HIGH/closed. Preload SET
  before GPIO initialization. PC0 is no longer an actuator output.
- Deflation-valve control: PC1, represented by `VALVE2_CTRL_Pin`.
  PC1 high means open; PC1 low means closed.
- Current bring-up pump control: PC8 is a low-level trigger relay output (`PUMP_RELAY_Pin`).
  PC8 high means pump off; PC8 low means relay active and pump on. This is a
  temporary relay-safe mode and does not provide PWM speed control.
- `VALVE1_OPEN/CLOSE` and `VALVE2_OPEN/CLOSE` each own only their valve GPIO.
  Pump state is controlled exclusively through `PUMP_START/STOP`.
- ESP8266 reset: PC3, active low via `ESP_RESET()`.

Safe actuator states:

| State | PB8 (open-drain) | PC1 | PC8 |
| --- | --- | --- | --- |
| Sealed idle | HIGH (released) | LOW | HIGH |
| Inflate | LOW | LOW | LOW |
| Vent / emergency stop | HIGH (released) | HIGH | HIGH |

### PB8 relay electrical contract (2026-10-31)

- Source: ST STM32F103xC/xD/xE, DocID14611 Rev12, table 5 p36 lists
  PB8 as FT (LQFP144 pin 139); table 46 p90 allows at most 5.5 V input
  when VDD >2 V and requires no internal pull above VDD+0.3 V. Local copy:
  `tmp/pdfs/stm32f103xcde_datasheet_keil.pdf`, from Keil.STM32F1xx_DFP.2.4.1.
- RM0008 GPIO section 8.1.8: open-drain SET is high impedance, RESET sinks.
  This does not make PB8 a 5 V push-pull output or permit 5 V on PC0/PC1.
- The user-confirmed low-trigger relay uses its rated 5.0 V supply from the
  regulator, common GND, IN connected only to PB8. Do not use the observed
  5.5 V as a supply setpoint; it is the FT limit, not operating headroom.
- Power MCU first, relay second; turn relay power off before MCU power.
  Do not allow powered IN to drive an unpowered MCU. HIGH pin readback requires
  the powered external relay pull-up; an unconnected released PB8 can float.
- Rebuild and run the actual GPIO/macro and eight-state port-aware gate host
  regressions. Check `pins`: idle PB8 HIGH/PC1 LOW/PC8 HIGH; open PB8 LOW;
  stop/vent PB8 HIGH/PC1 HIGH/PC8 HIGH. First validate without pump/valve load
  and without a human. Exact procedure lives in `血压仪完整接线方案.md`.
- Wrong: configure PB8 push-pull HIGH against a 5 V relay pull-up, or include
  PB8's bit 8 in the GPIOC valve mask. Correct: PB8 OD/NOPULL, preloaded SET;
  PC8 remains a separate pump pin. Export/pulse gates read both ports separately.

## Serial Interfaces

- USART1 is assigned to ESP8266 AT commands.
- USART2 is reserved for MAX3232 / RS232.
- USART3 is used for CH340 debug output and `printf` retargeting.

## Source Of Truth

If code, comments, and hardware notes disagree, stop and reconcile with:

- `血压仪完整接线方案.md`
- `blood pressure monitor/blood pressure monitor.ioc`
- `Core/Inc/main.h`
