import importlib.util
import re
import unittest

from test_safety_contract import CORE_SRC, PROJECT, function_body, read_text


class CaptureContractTests(unittest.TestCase):
    def test_export_command_cancels_before_other_commands_and_runs_after_safety(self):
        main = read_text(CORE_SRC / "main.c")
        command = function_body(main, "Process_DebugCommand")
        self.assertLess(command.index("BP_CaptureExport_Cancel();"), command.index("command == DEBUG_CMD_STOP"))
        self.assertIn("command != DEBUG_CMD_CAPTURE_EXPORT", command)
        self.assertIn("CaptureExport_IsSafe()", command)
        loop = main.split("while (1)", 1)[1]
        self.assertLess(loop.index("BP_CalculationTask();"), loop.index("BP_CaptureExport_Task("))
        self.assertLess(loop.index("BP_CaptureExport_Task("), loop.index("HAL_IWDG_Refresh("))
        for branch in ("DEBUG_CMD_CAL_CLEAR", "DEBUG_CMD_CAL_WRITE"):
            body = command.split("command == " + branch, 1)[1].split("else if", 1)[0]
            self.assertIn("CaptureAcquisition_IsActive()", body)
        project = read_text(PROJECT / "MDK-ARM/blood pressure monitor.uvprojx")
        self.assertIn("../Core/Src/bp_capture_export.c", project)
        self.assertIn("../Core/Inc/bp_capture_export.h", project)
        self.assertNotIn("tools/host", project)

    def test_production_callers_yield_instead_of_synchronous_calculation(self):
        for name in ("main.c", "bp_control.c"):
            source = read_text(CORE_SRC / name)
            self.assertNotRegex(source, r"BP_Algorithm_Calculate\(")
            self.assertIn("BP_Algorithm_BeginCalculate()", source)
            self.assertIn("BP_Algorithm_CalculateStep(", source)
        main = read_text(CORE_SRC / "main.c")
        loop = main.split("while (1)", 1)[1]
        ordered = ["Process_DebugCommand();", "ManualPump_TimeoutTask();",
                   "PressureStream_Task();", "BP_CalculationTask();", "HAL_IWDG_Refresh("]
        positions = [loop.index(item) for item in ordered]
        self.assertEqual(positions, sorted(positions))

    def test_pending_calculation_cancel_does_not_change_actuators(self):
        main = read_text(CORE_SRC / "main.c")
        cancel = function_body(main, "BP_CalculationCancel")
        self.assertIn("BP_Algorithm_CancelCalculate();", cancel)
        self.assertIn("s_calculation_pending = 0U;", cancel)
        self.assertIn("memset(&g_bp_result", cancel)
        self.assertNotRegex(cancel, r"PUMP_|VALVE[12]_|Deflate")
        self.assertIn("BP_CalculationCancel();", function_body(main, "DeflateControl_Cancel"))
        self.assertEqual(function_body(main, "Debug_PrintPressureSample").count("BP_CalculationCancel();"), 2)
        command = function_body(main, "Process_DebugCommand")
        for branch in ("DEBUG_CMD_CAL_CLEAR", "DEBUG_CMD_CAL_WRITE", "DEBUG_CMD_VALVE1_CLOSE"):
            body = command.split("command == " + branch, 1)[1].split("else if", 1)[0]
            self.assertIn("BP_CalculationCancel();", body)
            self.assertNotIn("DeflateControl_Cancel();", body)

    def test_all_add_sample_callers_check_overflow(self):
        for name in ("main.c", "bp_control.c"):
            source = read_text(CORE_SRC / name)
            calls = list(re.finditer(r"BP_Algorithm_AddSample\([^;]*?\)", source))
            self.assertTrue(calls)
            for call in calls:
                self.assertIn("== 0U", source[call.start():].split(";", 1)[0])
                after = source[call.end():call.end() + 400]
                self.assertIn("EmergencyStop(BP_FAULT_SAMPLE_OVERFLOW)", after)
        loop = read_text(CORE_SRC / "main.c").split("else if (s_deflate_pwm_enabled)", 1)[1]
        overflow = loop.split("BP_FAULT_SAMPLE_OVERFLOW", 1)[1].split("else", 1)[0]
        self.assertIn("continue;", overflow)

    def test_valve_diagnostics_record_only_after_actual_open(self):
        main = read_text(CORE_SRC / "main.c")
        pulse = function_body(main, "DeflatePulse_Start")
        self.assertEqual(pulse.count("BP_Algorithm_RecordValvePulse("), 1)
        self.assertLess(pulse.index("VALVE2_OPEN();"),
                        pulse.index("BP_Algorithm_RecordValvePulse("))
        algorithm = read_text(CORE_SRC / "bp_algorithm.c")
        record = function_body(algorithm, "BP_Algorithm_RecordValvePulse")
        self.assertNotRegex(record, r"PUMP_|VALVE[12]_|printf|HAL_UART|HAL_Delay")
        self.assertIn("BP_VALVE_DIAG_STEP_THRESHOLD_MMHG",
                      function_body(algorithm, "BP_Algorithm_AddSample"))

    def test_driver_defers_recovery_and_has_no_logging(self):
        driver = read_text(CORE_SRC / "ads1115.c")
        failure = function_body(driver, "ADS1115_Fail")
        sample = function_body(driver, "ADS1115_ReadSample")
        self.assertNotIn("ADS1115_I2C_Recover", failure + sample)
        self.assertNotIn("printf", driver)
        self.assertEqual(driver.count("ADS1115_I2C_Recover();"), 1)
        self.assertIn("ADS1115_I2C_Recover();", function_body(driver, "ADS1115_Init"))

    def test_stream_offline_retry_is_bounded_and_sample_interval_shared(self):
        main = read_text(CORE_SRC / "main.c")
        stream = function_body(main, "PressureStream_Task")
        self.assertIn("ADS1115_OFFLINE_RETRY_MS", stream)
        self.assertIn("s_ads1115_last_attempt_ms", stream)
        self.assertRegex(main, r"#define\s+ADS1115_OFFLINE_RETRY_MS\s+1000U")
        self.assertIn("BP_SAMPLE_INTERVAL_MS", main.split("else if (s_deflate_pwm_enabled)", 1)[1])

    def test_diagnostics_follow_emergency_stop(self):
        main = read_text(CORE_SRC / "main.c")
        for name in ("ManualPump_TimeoutTask", "Boot_PressureSafetyCheck", "ManualPump_Start"):
            body = function_body(main, name)
            self.assertLess(body.index("EmergencyStop(BP_FAULT_SENSOR_READ)"),
                            body.index("Debug_PrintADS1115Diagnostics()"))


class MemoryBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = PROJECT / "tools/check_firmware_budget.py"
        spec = importlib.util.spec_from_file_location("firmware_budget", path)
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def check(self, used=63000, peak=1112, stack="0x00001000"):
        return self.module.check_budget(
            f"Execution Region RW_IRAM1 (Exec base: 0x20000000, Size: {used:#x}, Max: 0x10000)\n"
            "0x2000e000 - 0x00001000 Zero RW 1 STACK",
            f"Maximum Stack Usage = {peak} bytes + Unknown(Cycles)",
            f"Stack_Size EQU {stack}",
        )

    def test_accepts_budget_with_interrupt_margin(self):
        self.assertEqual(self.check()["stack_reserved"], 4096)

    def test_rejects_insufficient_ram(self):
        with self.assertRaises(ValueError):
            self.check(used=64000)

    def test_rejects_original_oversized_stack_usage(self):
        with self.assertRaises(ValueError):
            self.check(peak=8820, stack="0x00000400")

    def test_rejects_missing_linker_evidence(self):
        with self.assertRaises(ValueError):
            self.module.check_budget("", "", "")


if __name__ == "__main__":
    unittest.main()
