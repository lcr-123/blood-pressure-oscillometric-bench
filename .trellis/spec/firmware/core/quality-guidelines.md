# Quality Guidelines

## Code Style

- Use STM32 HAL APIs consistently with the generated project.
- Keep custom code in custom modules or CubeMX `USER CODE` sections.
- Keep public interfaces in headers small and explicit.
- Prefer fixed-width integer types already used by the project, such as `uint8_t`, `uint16_t`, and `uint32_t`.
- Keep comments practical: explain hardware assumptions, timing, calibration, and safety behavior.

## Collaboration Style

- 尽量用中文与用户交涉；代码标识符、命令、文件路径、日志原文和必要英文技术名词可保留原文。

## Review Focus

For every firmware change, check:

- Peripheral handles are initialized before use.
- Interrupt callbacks route only to the intended driver.
- State transitions cannot leave the pump running unintentionally.
- ADS1115 voltage and pressure conversion still match the wiring.
- UART receive buffers cannot overflow.
- Debug output does not hide safety timing issues.
- Check the Keil map/callgraph against startup RAM/stack reservations, not only
  compiler success. Run `tools/check_firmware_budget.py` after rebuilding and
  follow [Capture Reliability](./capture-reliability.md) when changing buffers,
  acquisition errors, or algorithm local arrays.

## Verification

After completing firmware code, write the wiring and validation plan before reporting completion:

- List the MCU pins/peripherals and external modules touched by the change.
- State required power and ground connections.
- Include Keil build/download steps and the serial/debug output to watch.
- Describe measurable expected behavior for each step.
- For pump, valve, pressure sensor, or human-contact paths, include a non-human safety validation step first.

When hardware is available:

- Build in Keil MDK.
- Flash the STM32 and confirm debug output on USART3.
- Confirm ADS1115 I2C init prints success.
- Confirm pump and valves respond to control macros before connecting to a human.
- Compare pressure readings against a known reference before trusting algorithm results.

When hardware is not available:

- At minimum, review compile-time references, headers, and function prototypes for consistency.
- Keep changes small enough to inspect manually.
