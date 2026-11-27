import re
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
CORE_INC = PROJECT / "Core" / "Inc"
CORE_SRC = PROJECT / "Core" / "Src"


def read_text(path):
    return path.read_text(encoding="utf-8")


def function_body(source, function_name, prefix=""):
    match = re.search(
        r"\b" + prefix + re.escape(function_name) + r"\s*\([^;]*?\)\s*\{",
        source,
    )
    if match is None:
        raise AssertionError(f"function not found: {function_name}")

    start = source.find("{", match.start())
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError(f"unterminated function: {function_name}")


class SafetyContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = read_text(CORE_SRC / "main.c")
        cls.control = read_text(CORE_SRC / "bp_control.c")
        cls.control_h = read_text(CORE_INC / "bp_control.h")
        cls.ads1115 = read_text(CORE_SRC / "ads1115.c")
        cls.ads1115_h = read_text(CORE_INC / "ads1115.h")
        cls.bp_cal = read_text(CORE_SRC / "bp_cal.c")
        cls.iwdg = read_text(CORE_SRC / "iwdg.c")
        cls.interrupts = read_text(CORE_SRC / "stm32f1xx_it.c")
        cls.ioc = read_text(PROJECT / "blood pressure monitor.ioc")
        cls.keil = read_text(PROJECT / "MDK-ARM" / "blood pressure monitor.uvprojx")

    def test_relay_only_and_serial_button_substitution_remain_enabled(self):
        self.assertRegex(self.main, r"#define\s+BP_BRINGUP_RELAY_ONLY\s+1U")
        self.assertRegex(self.main, r"#define\s+BP_BRINGUP_ENABLE_BUTTONS\s+0U")
        self.assertRegex(self.control_h, r"#define\s+BP_SENSOR_CALIBRATION_VALID\s+0U")

    def test_legacy_serial_commands_are_preserved(self):
        for command in ("start", "stop", "open", "close", "vent", "seal", "pressure", "p"):
            self.assertIn(f'"{command}"', self.main)
        self.assertIn("UNCAL", self.main)

    def test_new_diagnostics_are_available(self):
        for command in ("help", "status", "pins", "fault", "stream start", "stream stop"):
            self.assertIn(f'"{command}"', self.main)

    def test_emergency_stop_is_nonblocking_and_ordered(self):
        body = function_body(self.control, "BP_Control_EmergencyStop")
        self.assertNotIn("HAL_Delay", body)
        pump = body.index("PUMP_STOP()")
        inflate = body.index("VALVE1_CLOSE()")
        vent = body.index("VALVE2_OPEN()")
        self.assertLess(pump, inflate)
        self.assertLess(inflate, vent)

    def test_control_init_does_not_write_startup_transport(self):
        body = function_body(self.control, "BP_Control_Init")
        self.assertNotIn("printf", body)
        self.assertIn("[BP_Control] Init OK calibration=", self.main)

    def test_full_measurement_start_is_calibration_locked(self):
        body = function_body(self.control, "BP_Control_Start")
        calibration = body.index("BP_Control_IsCalibrationValid()")
        pump = body.index("PUMP_START()")
        self.assertLess(calibration, pump)
        self.assertIn("BP_FAULT_UNCALIBRATED", body)

    def test_measurement_sensor_failures_vent(self):
        body = function_body(self.control, "BP_Control_Task")
        self.assertIn("BP_FAULT_SENSOR_READ", body)
        self.assertIn("BP_FAULT_INFLATE_TIMEOUT", body)
        self.assertIn("BP_FAULT_OVERPRESSURE", body)

    def test_manual_pump_has_bounded_timeout(self):
        timeout = re.search(r"#define\s+MANUAL_PUMP_TIMEOUT_MS\s+(\d+)U", self.main)
        self.assertIsNotNone(timeout)
        self.assertLessEqual(int(timeout.group(1)), 60000)
        body = function_body(self.main, "ManualPump_TimeoutTask")
        self.assertIn("BP_FAULT_MANUAL_TIMEOUT", body)
        self.assertIn("ManualPump_EmergencyStop", body)

    def test_holdopen_diagnostic_is_nonhuman_and_bounded(self):
        timeout = re.search(r"#define\s+HOLD_OPEN_TIMEOUT_MS\s+(\d+)U", self.main)
        self.assertIsNotNone(timeout)
        self.assertLessEqual(int(timeout.group(1)), 15000)
        task = function_body(self.main, "HoldOpen_TimeoutTask")
        self.assertIn("BP_Control_EmergencyStop", task)
        self.assertIn("BP_FAULT_MANUAL_TIMEOUT", task)

        command_body = function_body(self.main, "Process_DebugCommand")
        branch = command_body.split("DEBUG_CMD_HOLD_OPEN", 1)[1].split(
            "DEBUG_CMD_DEFLATE_PWM", 1
        )[0]
        pump = branch.index("PUMP_STOP()")
        seal = branch.index("VALVE2_CLOSE()")
        inflate_path = branch.index("VALVE1_OPEN()")
        self.assertLess(pump, inflate_path)
        self.assertLess(seal, inflate_path)
        self.assertIn("NONHUMAN", branch)
        self.assertIn('"holdopen"', self.main)

    def test_zero_pulse_is_bounded_and_preserves_emergency_exit(self):
        self.assertIn('"zero pulse"', self.main)
        self.assertRegex(self.main, r"#define\s+ZERO_PULSE_ON_MS\s+5U")
        self.assertRegex(self.main, r"#define\s+ZERO_PULSE_DURATION_MS\s+5000U")
        command = function_body(self.main, "Process_DebugCommand")
        guard = command.split("if (((s_hold_open_active == ZERO_PULSE_ACTIVE)", 1)[1].split(
            "if (command == DEBUG_CMD_STOP)", 1
        )[0]
        for allowed in ("DEBUG_CMD_STOP", "DEBUG_CMD_VALVE2_OPEN", "DEBUG_CMD_VALVE2_CLOSE"):
            self.assertIn(allowed, guard)
        self.assertIn("return;", guard)
        start = command.split("command == DEBUG_CMD_ZERO_PULSE", 1)[1].split(
            "else if", 1
        )[0]
        for gate in ("CaptureExport_IsSafe()", "ADS1115_ReadSample(&sample)",
                     "BP_Algorithm_Reset()", "ZERO_PULSE_ACTIVE"):
            self.assertIn(gate, start)
        task = function_body(self.main, "PulseDiagnostic_Task")
        for safety in ("ZERO_PULSE_DURATION_MS", "DeflateControl_Cancel()",
                       "VALVE2_CLOSE()", "BP_FAULT_SENSOR_READ",
                       "BP_FAULT_OVERPRESSURE", "BP_FAULT_SAMPLE_OVERFLOW"):
            self.assertIn(safety, task)
        self.assertIn("BP_Algorithm_AddSample(sample.pressure_mmhg,", task)
        self.assertIn("sample.sensor_voltage_v", task)
        self.assertLess(task.index("BP_Algorithm_AddSample"),
                        task.index("DeflatePulse_Start((loaded != 0U) ?"))
        self.assertIn("s_loaded_pulse_on_ms : ZERO_PULSE_ON_MS", task)

    def test_loaded_pulse_has_baseline_pressure_gate_and_automatic_vent(self):
        self.assertIn('"loaded pulse"', self.main)
        for width in range(1, 5):
            self.assertIn(f'"loaded pulse {width}"', self.main)
            self.assertIn(f"DEBUG_CMD_LOADED_PULSE_{width}", self.main)
        self.assertRegex(self.main, r"#define\s+LOADED_PULSE_BASELINE_MS\s+1000U")
        self.assertRegex(self.main, r"#define\s+LOADED_PULSE_DURATION_MS\s+4000U")
        gate = function_body(self.main, "LoadedPulse_IsSafe")
        for condition in ("CaptureAcquisition_IsActive()", "BP_STATE_IDLE",
                          "BP_Cal_IsValid()", "s_ads1115_ready", "s_pressure_stream_enabled",
                          "LOADED_PULSE_START_MIN_MMHG", "LOADED_PULSE_START_MAX_MMHG",
                          "VALVE1_CTRL_Port, VALVE1_CTRL_Pin", "GPIO_PIN_SET",
                          "VALVE2_CTRL_Port, VALVE2_CTRL_Pin", "PUMP_RELAY_Port, PUMP_RELAY_Pin"):
            self.assertIn(condition, gate)
        self.assertIn("BP_STATE_EMERGENCY", gate)
        self.assertIn("BP_Control_GetFault() == BP_FAULT_USER_STOP", gate)
        command = function_body(self.main, "Process_DebugCommand")
        self.assertIn("seal blocked until vent reaches zero", command)
        start = command.split("command == DEBUG_CMD_LOADED_PULSE", 1)[1].split(
            "command == DEBUG_CMD_STACK", 1
        )[0]
        self.assertIn("LoadedPulse_IsSafe()", start)
        self.assertIn("ADS1115_ReadSample(&sample)", start)
        self.assertIn("LOADED_PULSE_ACTIVE", start)
        self.assertIn("s_loaded_pulse_on_ms = on_ms", start)
        self.assertIn("command - DEBUG_CMD_LOADED_PULSE_1 + 1U", start)
        self.assertLess(start.index("BP_Control_Reset()"), start.index("BP_Algorithm_Reset()"))
        task = function_body(self.main, "PulseDiagnostic_Task")
        self.assertIn("elapsed >= LOADED_PULSE_BASELINE_MS", task)
        self.assertIn("LOADED_PULSE_ABORT_MIN_MMHG", task)
        self.assertIn("LOADED_PULSE_ABORT_MAX_MMHG", task)
        self.assertIn("BP_FAULT_PRESSURE_RANGE", task)
        self.assertIn("DeflatePulse_Start((loaded != 0U) ? s_loaded_pulse_on_ms : ZERO_PULSE_ON_MS)", task)
        self.assertLess(task.index("DeflateControl_Cancel()"), task.index("VALVE2_OPEN()"))
        self.assertLess(task.index("PUMP_STOP()"), task.index("VALVE2_OPEN()"))
        self.assertLess(task.index("VALVE1_CLOSE()"), task.index("VALVE2_OPEN()"))
        self.assertIn('return "PRESSURE_RANGE"', self.control)

    def test_deflate_test_has_bounded_gate_duration_floor_and_width(self):
        """The closed-loop rate probe must remain a bounded non-human diagnostic."""
        self.assertIn('"deflate test"', self.main)
        self.assertRegex(self.main, r"#define\s+DEFLATE_TEST_DURATION_MS\s+10000U")
        self.assertRegex(self.main, r"#define\s+DEFLATE_TEST_STOP_MMHG\s+45\.0f")
        self.assertRegex(self.main, r"#define\s+DEFLATE_TEST_MAX_ON_MS\s+4U")

        command = function_body(self.main, "Process_DebugCommand")
        start = command.split("command == DEBUG_CMD_DEFLATE_TEST", 1)[1].split(
            "else if (command == DEBUG_CMD_VALVE2_CLOSE)", 1
        )[0]
        for gate in ("LoadedPulse_IsSafe()", "ADS1115_ReadSample(&sample)",
                     "LOADED_PULSE_START_MIN_MMHG", "LOADED_PULSE_START_MAX_MMHG",
                     "BP_Algorithm_Reset()", "s_deflate_test_active = 1U",
                     "s_deflate_pwm_enabled = 1U"):
            self.assertIn(gate, start)
        self.assertIn("max_on=4ms", start)

        loop = function_body(self.main, "main")
        deflate = loop.split("else if (s_deflate_pwm_enabled)", 1)[1]
        self.assertIn("DEFLATE_TEST_DURATION_MS", deflate)
        self.assertIn("DEFLATE_TEST_STOP_MMHG", deflate)
        self.assertIn("LOADED_PULSE_ABORT_MIN_MMHG", deflate)
        self.assertIn("LOADED_PULSE_ABORT_MAX_MMHG", deflate)
        self.assertIn("BP_FAULT_SENSOR_READ", deflate)
        self.assertIn("BP_FAULT_PRESSURE_RANGE", deflate)
        self.assertIn("BP_FAULT_SAMPLE_OVERFLOW", deflate)
        self.assertIn("DEFLATE_TEST_MAX_ON_MS", deflate)

    def test_deflate_test_finish_cancels_before_opening_vent_and_prevents_next_pwm(self):
        finish = function_body(self.main, "DeflateTest_Finish")
        self.assertLess(finish.index("DeflateControl_Cancel()"), finish.index("VALVE2_OPEN()"))
        self.assertIn('"[DeflateTest] done reason=%s', finish)
        loop = function_body(self.main, "main").split(
            "else if (s_deflate_pwm_enabled)", 1
        )[1]
        timeout = loop.split("DeflateTest_Finish(\"timeout\")", 1)[1]
        self.assertIn("continue;", timeout.split("/* Auto-stop", 1)[0])
        floor = loop.split('DeflateTest_Finish("floor")', 1)[1]
        self.assertIn("continue;", floor.split("}", 1)[0] + "}")

    def test_manual_inflate_samples_pressure_independently_and_vents_on_failure(self):
        body = function_body(self.main, "ManualPump_TimeoutTask")
        self.assertIn("ADS1115_ReadSample", body)
        self.assertIn("MANUAL_PRESSURE_SAMPLE_INTERVAL_MS", body)
        self.assertIn("BP_FAULT_SENSOR_READ", body)
        self.assertIn("BP_FAULT_OVERPRESSURE", body)
        self.assertIn("s_inflate_target_mmhg", body)

    def test_target_command_keeps_margin_below_hard_overpressure_limit(self):
        hard = re.search(r"#define\s+BP_MAX_PRESSURE_MMHG\s+(\d+)U", self.control_h)
        target = re.search(
            r"#define\s+BP_MAX_TARGET_MMHG\s+\(BP_MAX_PRESSURE_MMHG\s+-\s+(\d+)U\)",
            self.control_h,
        )
        self.assertIsNotNone(hard)
        self.assertIsNotNone(target)
        hard_limit = int(hard.group(1))
        margin = int(target.group(1))
        self.assertEqual(hard_limit, 280)
        self.assertEqual(margin, 5)
        self.assertEqual(hard_limit - margin, 275)

        command = function_body(self.main, "Process_DebugCommand")
        branch = command.split("DEBUG_CMD_TARGET", 1)[1].split(
            "DEBUG_CMD_MOTOR", 1
        )[0]
        self.assertIn("target > (float)BP_MAX_TARGET_MMHG", branch)
        self.assertIn("target <20-275 mmHg>", branch)
        self.assertNotIn("target > 250.0f", branch)

        # Boundary contract used by the host-side command tests/documentation:
        # 20 and 275 are legal targets; 19, 280 and 281 are rejected.
        def accepted(value):
            return 20.0 <= value <= (hard_limit - margin)

        for value in (20.0, 275.0):
            self.assertTrue(accepted(value))
        for value in (19.0, 280.0, 281.0):
            self.assertFalse(accepted(value))

    def test_manual_start_requires_calibration_and_sensor_preflight(self):
        body = function_body(self.main, "ManualPump_Start")
        calibration = body.index("BP_Control_IsCalibrationValid()")
        sensor = body.index("ADS1115_ReadSample")
        pump = body.index("PUMP_START()")
        self.assertLess(calibration, pump)
        self.assertLess(sensor, pump)
        self.assertIn("BP_FAULT_SENSOR_READ", body)

    def test_continuous_pump_command_cannot_bypass_pressure_safety(self):
        command_body = function_body(self.main, "Process_DebugCommand")
        branch = command_body.split("DEBUG_CMD_PUMP_ON", 1)[1].split("DEBUG_CMD_VALVE1_CLOSE", 1)[0]
        self.assertNotIn("ManualPump_Start", branch)
        self.assertNotIn("PUMP_START", branch)

    def test_boot_vents_residual_pressure_after_reset(self):
        body = function_body(self.main, "Boot_PressureSafetyCheck")
        self.assertIn("ADS1115_ReadSample", body)
        self.assertIn("BOOT_RESIDUAL_PRESSURE_MMHG", body)
        self.assertIn("BP_Control_EmergencyStop", body)
        self.assertIn("BP_FAULT_RESIDUAL_PRESSURE", body)
        self.assertIn("Boot_PressureSafetyCheck();", self.main)
        self.assertIn("BP_FAULT_RESIDUAL_PRESSURE", self.control_h)
        self.assertIn('return "RESIDUAL_PRESSURE"', self.control)

    def test_relay_only_deflate_updates_pressure_without_stream(self):
        loop = self.main.split("else if (s_deflate_pwm_enabled)", 1)[1]
        sample_block = loop.split("ADS1115_ReadSample(&sample)", 1)[1]
        self.assertIn("g_last_pressure_mmhg = sample.pressure_mmhg", sample_block)
        self.assertIn("s_last_pressure_sample = sample", sample_block)
        self.assertIn("BP_FAULT_SENSOR_READ", sample_block)
        stream_body = function_body(self.main, "PressureStream_Task")
        self.assertIn("s_deflate_pwm_enabled", stream_body)

    def test_deflate_pulse_period_matches_reported_configuration(self):
        self.assertIn("#define DEFLATE_PWM_PERIOD_MS       200U", self.main)
        self.assertIn("#define DEFLATE_CONTROL_INTERVAL_MS 400U", self.main)
        version = function_body(self.main, "Debug_PrintFirmwareVersion")
        self.assertIn("DEFLATE_PWM_PERIOD_MS", version)
        self.assertIn("DEFLATE_PWM_BASE_ON_MS", version)

    def test_systick_ends_deflate_pulse_independently_of_main_loop(self):
        systick = function_body(self.interrupts, "SysTick_Handler")
        self.assertIn("HAL_IncTick()", systick)
        self.assertIn("HAL_SYSTICK_IRQHandler()", systick)
        callback = function_body(self.main, "HAL_SYSTICK_Callback")
        self.assertIn("s_deflate_pulse_remaining_ms--", callback)
        self.assertIn("VALVE2_CLOSE()", callback)
        loop = self.main.split("else if (s_deflate_pwm_enabled)", 1)[1]
        self.assertIn("DeflatePulse_Start(s_deflate_pwm_on_ms)", loop)
        self.assertNotIn("% DEFLATE_PWM_PERIOD_MS", loop)

    def test_manual_emergency_cancels_pulse_before_opening_vent(self):
        body = function_body(self.main, "ManualPump_EmergencyStop")
        cancel = body.index("DeflateControl_Cancel()")
        emergency = body.index("BP_Control_EmergencyStop")
        self.assertLess(cancel, emergency)

        command_body = function_body(self.main, "Process_DebugCommand")
        vent = command_body.split("DEBUG_CMD_VALVE2_OPEN", 1)[1].split(
            "DEBUG_CMD_DEFLATE_PWM", 1
        )[0]
        self.assertLess(vent.index("DeflateControl_Cancel()"), vent.index("VALVE2_OPEN()"))

        seal = command_body.split("DEBUG_CMD_VALVE2_CLOSE", 1)[1].split(
            "DEBUG_CMD_PRESSURE", 1
        )[0]
        self.assertLess(seal.index("DeflateControl_Cancel()"), seal.index("VALVE2_CLOSE()"))

    def test_deflate_terminal_states_are_not_overwritten_by_pwm(self):
        loop = self.main.split("else if (s_deflate_pwm_enabled)", 1)[1]
        completed = loop.split('Debug_UART_Write("[Deflate] done; valve2 closed', 1)[1]
        completed = completed.split("/* Sample for algorithm", 1)[0]
        self.assertIn("continue;", completed)
        self.assertIn("DeflateControl_Cancel();", loop.split(
            'Debug_UART_Write("[Deflate] done; valve2 closed', 1
        )[0])
        failed = loop.split('Debug_UART_Write("[Safety] Pressure read failed during deflate', 1)[1]
        failed = failed.split("uint32_t phase", 1)[0]
        self.assertIn("continue;", failed)

    def test_pressure_command_does_not_own_actuators(self):
        body = function_body(self.main, "Debug_PrintPressureSample")
        for actuator_call in ("PUMP_START", "PUMP_STOP", "VALVE1_OPEN", "VALVE2_OPEN"):
            self.assertNotIn(actuator_call, body)

    def test_watchdog_is_nominal_four_seconds_and_debug_frozen(self):
        self.assertIn("IWDG_PRESCALER_64", self.iwdg)
        self.assertIn("hiwdg.Init.Reload = 2499U", self.iwdg)
        self.assertIn("__HAL_DBGMCU_FREEZE_IWDG()", self.iwdg)
        self.assertIn("HAL_IWDG_Refresh(&hiwdg)", self.main)

    def test_cubemx_and_keil_include_watchdog(self):
        self.assertIn("Mcu.IP1=IWDG", self.ioc)
        self.assertIn("IWDG.Prescaler=IWDG_PRESCALER_64", self.ioc)
        self.assertIn("IWDG.Reload=2499", self.ioc)
        self.assertIn("../Core/Src/iwdg.c", self.keil)
        self.assertIn("stm32f1xx_hal_iwdg.c", self.keil)

    def test_cubemx_valve1_is_released_open_drain_pb8(self):
        for setting in ("Mcu.Pin0=PB8", "PB8.GPIO_Label=VALVE1_CTRL",
                        "PB8.GPIO_ModeDefaultOutputPP=GPIO_MODE_OUTPUT_OD",
                        "PB8.GPIO_PuPd=GPIO_NOPULL", "PB8.PinState=GPIO_PIN_SET"):
            self.assertIn(setting, self.ioc)
        self.assertNotIn("PC0.Signal=GPIO_Output", self.ioc)

    def test_keil_still_contains_all_custom_sources(self):
        for source in ("ads1115.c", "bp_algorithm.c", "bp_cal.c", "bp_control.c", "esp8266.c", "iwdg.c"):
            self.assertIn(f"<FileName>{source}</FileName>", self.keil)

    def test_mpxv5050_sensitivity_constant_matches_datasheet(self):
        # Datasheet: Vout = VS*(0.018*P + 0.04), VS=5.0V -> 90 mV/kPa.
        self.assertIn("MPXV5050_SENSITIVITY_V_PER_KPA      0.09f", self.ads1115_h)

    def test_calibration_validity_is_runtime_flash_state(self):
        body = function_body(self.control, "BP_Control_IsCalibrationValid", prefix=r"uint8_t\s+")
        self.assertIn("BP_Cal_IsValid", body)
        self.assertIn("BP_SENSOR_CALIBRATION_VALID", body)

    def test_pressure_conversion_routes_through_calibration_store(self):
        body = function_body(self.ads1115, "ADS1115_ReadSample")
        self.assertIn("BP_Cal_GetPressure_mmHg", body)
        self.assertNotIn("VOLTAGE_TO_KPA", body)

    def test_cal_storage_has_flash_crc_and_verify_contract(self):
        self.assertIn("BP_CAL_FLASH_ADDR", self.bp_cal)
        self.assertIn("BP_CAL_MAGIC", self.bp_cal)
        self.assertIn("BP_Cal_Crc16", self.bp_cal)
        self.assertIn("HAL_FLASHEx_Erase", self.bp_cal)
        self.assertIn("HAL_FLASH_Program", self.bp_cal)
        self.assertIn("stm32f1xx_hal_flash.c", self.keil)

    def test_serial_cal_commands_are_available(self):
        for command in ("cal", "cal clear"):
            self.assertIn(f'"{command}"', self.main)
        # "cal write" is parsed with a trailing space via strncmp.
        self.assertIn('"cal write "', self.main)
        self.assertIn("BP_Cal_Load", self.main)
        self.assertIn("BP_Cal_Write", self.main)
        self.assertIn("BP_Cal_Clear", self.main)


if __name__ == "__main__":
    unittest.main()
