# Directory Structure

## Project Layout

- `blood pressure monitor/blood pressure monitor.ioc` is the CubeMX source of truth for generated peripheral setup.
- `blood pressure monitor/Core/Inc/` contains headers for STM32 HAL init files and custom application modules.
- `blood pressure monitor/Core/Src/` contains generated peripheral init files and custom application modules.
- `blood pressure monitor/Drivers/` contains STM32 HAL and CMSIS vendor code. Do not edit vendor driver files for application behavior.
- `blood pressure monitor/MDK-ARM/` contains Keil project files and build output.
- `血压仪完整接线方案.md` documents the hardware wiring and electrical assumptions.

## Custom Application Modules

Current custom modules:

- `ads1115.[ch]` - ADS1115 I2C ADC access and pressure conversion.
- `bp_control.[ch]` - blood pressure measurement state machine, pump, and valve control.
- `bp_algorithm.[ch]` - oscillometric sample processing and result calculation.
- `esp8266.[ch]` - ESP8266 AT command driver over USART1.

## Editing Rules

- Prefer editing custom modules in `Core/Inc` and `Core/Src`.
- In generated files such as `main.c`, `gpio.c`, `i2c.c`, `tim.c`, and `usart.c`, place custom code only inside `USER CODE BEGIN/END` blocks.
- Keep hardware labels and macros centralized in `main.h` unless CubeMX regeneration requires another location.
- Do not edit `Drivers/STM32F1xx_HAL_Driver` or `Drivers/CMSIS` unless fixing a vendor integration issue with a clear note.
- After every firmware code change, confirm the touched source file is represented in `MDK-ARM/blood pressure monitor.uvprojx`.
- When adding or moving compiled sources such as `.c` or `.s`, update the Keil MDK project file in the same change so the IDE build includes them. For new headers, confirm include paths and project visibility are still correct.
