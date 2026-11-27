# Firmware Core Development Guidelines

This project is STM32F103ZET6 firmware for an oscillometric blood pressure monitor.

Read these files before changing code under `blood pressure monitor/Core/`:

| Guide | Purpose |
| --- | --- |
| [Directory Structure](./directory-structure.md) | Where firmware files live and what should be edited |
| [Hardware Map](./hardware-map.md) | Pin, peripheral, and external module mapping |
| [Control Flow](./control-flow.md) | Main loop, state machine, sampling, and upload flow |
| [Safety Rules](./safety-rules.md) | Pressure, pump, valve, and blocking-call constraints |
| [Quality Guidelines](./quality-guidelines.md) | Review and verification expectations |
| [Capture Reliability](./capture-reliability.md) | Sample overflow, RAM/stack budget, ADS1115 failure/recovery contracts |
| [Capture Export](./capture-export.md) | Complete waveform protocol, safe export lifecycle, strict offline production-C replay |

## Pre-Development Checklist

- Confirm whether a change belongs in `USER CODE` sections, custom modules, or CubeMX-generated files.
- Check `血压仪完整接线方案.md` before changing pin, voltage, ADS1115, valve, pump, or ESP8266 assumptions.
- Keep pump/valve fail-safe behavior explicit when touching measurement control.
- Preserve Keil MDK / STM32 HAL compatibility.

## Quality Check

- The firmware still initializes GPIO, I2C1, USART1/2/3, and TIM8 before application modules.
- Pump stop, valve close/open, and over-pressure paths remain reachable.
- No WiFi or debug operation can permanently block measurement safety handling.
