"""Compile/run real firmware C against a bounded host HAL, with no device I/O."""
import importlib.util
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import sys

PROJECT = Path(__file__).resolve().parents[1]
HOST = PROJECT / "test" / "host"
sys.path.insert(0, str(PROJECT / "tools"))
from host_build import compiler_environment


class HostFirmwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            compiler, env = compiler_environment()
        except FileNotFoundError as exc:
            raise unittest.SkipTest(str(exc)) from exc
        cls.temp = tempfile.TemporaryDirectory(prefix="bp-host-regression-")
        cls.addClassCleanup(cls.temp.cleanup)
        work = Path(cls.temp.name)
        for file in HOST.iterdir():
            if file.is_file():
                shutil.copy2(file, work / file.name)
        for name in ("bp_algorithm", "bp_control", "ads1115"):
            shutil.copy2(PROJECT / "Core/Inc" / f"{name}.h", work)
            shutil.copy2(PROJECT / "Core/Src" / f"{name}.c", work)
        main_source = (PROJECT / "Core/Src/main.c").read_text(encoding="utf-8")
        cancel_signature = "static void BP_CalculationCancel("
        task_signature = "static void BP_CalculationTask("
        calculation = cancel_signature + main_source.split(cancel_signature, 1)[1].split(
            "\nstatic void DeflateControl_Cancel(", 1
        )[0]
        calculation += task_signature + main_source.split(task_signature, 1)[1].split(
            "\n#if BP_BRINGUP_ENABLE_BUTTONS", 1
        )[0]
        (work / "main_calculation_under_test.h").write_text(calculation, encoding="utf-8")
        cls.exe = work / "regression.exe"
        command = [compiler, "/nologo", "/std:c11", "/utf-8", "/W3", "/D_CRT_SECURE_NO_WARNINGS",
                   "firmware_regression.c", "ads1115.c", "bp_control.c", f"/Fe:{cls.exe}"]
        built = subprocess.run(command, cwd=work, env=env, text=True, errors="replace",
                               capture_output=True, timeout=60)
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

        # Extract complete production definitions (skip any forward declarations).
        def definition(source, name):
            match = re.search(rf"(?:static )?(?:void|uint8_t|HAL_StatusTypeDef|DebugCommand_t) {name}\([^;{{]*\)\s*\{{", source)
            if match is None:
                raise AssertionError(f"Missing production function: {name}")
            start = match.start()
            depth = 1
            end = match.end()
            while depth:
                depth += (source[end] == "{") - (source[end] == "}")
                end += 1
            return source[start:end] + "\n"

        vendor = (PROJECT / "Drivers/STM32F1xx_HAL_Driver/Src/stm32f1xx_hal_uart.c").read_text(encoding="utf-8")
        uart = "".join(definition(vendor, name) for name in (
            "UART_Start_Receive_IT", "HAL_UART_Receive_IT", "UART_EndRxTransfer", "UART_Receive_IT"))
        # Compile the unchanged vendor normal-RX and error branches. TX, DMA-IDLE
        # dispatch beyond this marker is outside this interrupt-RX regression.
        uart += definition(vendor, "HAL_UART_IRQHandler").split(
            "  /* Check current reception Mode :", 1)[0] + "}\n"
        (work / "uart_vendor_under_test.h").write_text(uart, encoding="utf-8")
        uart = "#define DEBUG_CMD_BUFFER_LEN 48U\ntypedef enum {" + main_source.split("typedef enum {", 1)[1].split(
            "static uint8_t s_manual_pump_active", 1)[0]
        for name in ("Debug_CommandRejectLine", "Debug_CommandTake", "Debug_UART_RxTask",
                     "Debug_CommandAcceptByte", "Debug_UART_StartRxInterrupt",
                     "HAL_UART_RxCpltCallback", "HAL_UART_ErrorCallback"):
            uart += definition(main_source, name)
        (work / "uart_main_under_test.h").write_text(uart, encoding="utf-8")
        cls.uart_exe = work / "uart_rx.exe"
        built = subprocess.run(
            [compiler, "/nologo", "/std:c11", "/utf-8", "/W3", "/D_CRT_SECURE_NO_WARNINGS",
             "uart_rx_regression.c", f"/Fe:{cls.uart_exe}"], cwd=work, env=env,
            text=True, errors="replace", capture_output=True, timeout=60,
        )
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

        (work / "i2c_scan_under_test.h").write_text(
            definition(main_source, "Debug_I2CScan"), encoding="utf-8")
        cls.scan_exe = work / "i2c_scan.exe"
        built = subprocess.run(
            [compiler, "/nologo", "/std:c11", "/utf-8", "/W3", "/D_CRT_SECURE_NO_WARNINGS",
             "i2c_scan_regression.c", f"/Fe:{cls.scan_exe}"], cwd=work, env=env,
            text=True, errors="replace", capture_output=True, timeout=60,
        )
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

        control_source = (PROJECT / "Core/Src/bp_control.c").read_text(encoding="utf-8")
        hold = "".join(definition(control_source, name) for name in (
            "BP_Control_RecordFault", "BP_Control_EmergencyStop"))
        hold += "".join(definition(main_source, name) for name in (
            "DeflatePulse_Cancel", "BP_CalculationCancel", "DeflateControl_Cancel",
            "ManualPump_Disarm", "ManualPump_EmergencyStop", "Debug_PrintPressureSample",
            "ManualPump_TimeoutTask", "PressureStream_Task"))
        # Execute the actual main-loop hold-to-PWM branch as well as the safety task.
        loop = main_source.split("    while (1)", 1)[1]
        transition = loop.split("        if (s_deflate_hold_until_ms != 0U)", 1)[1].split(
            "        else if (s_deflate_pwm_enabled)", 1)[0]
        hold += "static void hold_transition(void) {\nif (s_deflate_hold_until_ms != 0U)" + transition + "}\n"
        (work / "hold_safety_under_test.h").write_text(hold, encoding="utf-8")
        cls.hold_exe = work / "hold_safety.exe"
        built = subprocess.run(
            [compiler, "/nologo", "/std:c11", "/utf-8", "/W3", "/D_CRT_SECURE_NO_WARNINGS",
             "hold_safety_regression.c", f"/Fe:{cls.hold_exe}"],
            cwd=work, env=env, text=True, errors="replace", capture_output=True, timeout=60,
        )
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

        # Run the production ADS driver and actual inflate/hold/readtest functions
        # in one executable; HAL device bytes and clock are the only sensor fake.
        read_path = "".join(definition(control_source, name) for name in (
            "BP_Control_RecordFault", "BP_Control_EmergencyStop"))
        read_path += "".join(definition(main_source, name) for name in (
            "CaptureAcquisition_IsActive", "DeflatePulse_Cancel", "BP_CalculationCancel",
            "DeflateControl_Cancel", "ManualPump_Disarm", "ManualPump_EmergencyStop",
            "ManualPump_TimeoutTask", "ReadTest_PinsSafe", "ReadTest_Finish",
            "ReadTest_Start", "ReadTest_Task"))
        (work / "read_path_under_test.h").write_text(read_path, encoding="utf-8")
        cls.read_path_exe = work / "read_path.exe"
        built = subprocess.run(
            [compiler, "/nologo", "/std:c11", "/utf-8", "/W3", "/D_CRT_SECURE_NO_WARNINGS",
             "read_path_regression.c", "ads1115.c", f"/Fe:{cls.read_path_exe}"],
            cwd=work, env=env, text=True, errors="replace", capture_output=True, timeout=60,
        )
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

        # A separate include directory keeps the production pin macros intact.
        gpio_work = work / "gpio_contract"
        gpio_work.mkdir()
        for name in ("main.h", "gpio.h"):
            shutil.copy2(PROJECT / "Core/Inc" / name, gpio_work)
        shutil.copy2(PROJECT / "Core/Src/gpio.c", gpio_work)
        shutil.copy2(HOST / "gpio_regression.c", gpio_work)
        shutil.copy2(HOST / "gpio_hal_stub.h", gpio_work / "stm32f1xx_hal.h")
        cls.gpio_exe = gpio_work / "gpio_regression.exe"
        built = subprocess.run(
            [compiler, "/nologo", "/std:c11", "/utf-8", "/W3", "gpio_regression.c",
             "gpio.c", f"/Fe:{cls.gpio_exe}"], cwd=gpio_work, env=env,
            text=True, errors="replace", capture_output=True, timeout=60,
        )
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

        # Compile both production export predicates with host pin/clock inputs.
        gate = ""
        for name in ("CaptureExport_IsSafe", "CaptureAcquisition_IsActive", "LoadedPulse_IsSafe", "DeflateProfile_Set"):
            signature = f"static uint8_t {name}("
            gate += signature + main_source.split(signature, 1)[1].split("\nstatic ", 1)[0]
        (work / "capture_gate_under_test.h").write_text(gate, encoding="utf-8")
        cls.gate_exe = work / "capture_gate.exe"
        built = subprocess.run(
            [compiler, "/nologo", "/std:c11", "/utf-8", "/W3", "/D_CRT_SECURE_NO_WARNINGS",
             "capture_gate_regression.c", f"/Fe:{cls.gate_exe}"],
            cwd=work, env=env, text=True, errors="replace", capture_output=True, timeout=60,
        )
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)
        # Compile the production formatter, not a Python reimplementation of it.
        main_source = (PROJECT / "Core/Src/main.c").read_text(encoding="utf-8")
        signature = "static void Debug_PrintPressureRecord("
        formatter = signature + main_source.split(signature, 1)[1].split(
            "\nstatic uint8_t Debug_PrintPressureSample(", 1
        )[0]
        (work / "pressure_record_under_test.h").write_text(formatter, encoding="utf-8")
        cls.pressure_exe = work / "pressure_format.exe"
        built = subprocess.run(
            [compiler, "/nologo", "/std:c11", "/utf-8", "/W3", "/D_CRT_SECURE_NO_WARNINGS",
             "pressure_format_regression.c", f"/Fe:{cls.pressure_exe}"],
            cwd=work, env=env, text=True, errors="replace", capture_output=True, timeout=60,
        )
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

    def run_scenario(self, scenario):
        result = subprocess.run([str(self.exe), str(scenario)], capture_output=True,
                                text=True, errors="replace", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_actual_hold_safety_faults_stream_and_deadline(self):
        result = subprocess.run([str(self.hold_exe)], capture_output=True,
                                text=True, errors="replace", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_actual_read_path_ramp_hold_faults_and_static_diagnostic(self):
        result = subprocess.run([str(self.read_path_exe)], capture_output=True,
                                text=True, errors="replace", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_actual_uart_error_recovery_and_command_integrity(self):
        result = subprocess.run([str(self.uart_exe)], capture_output=True,
                                text=True, errors="replace", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_actual_i2c_scan_address_and_safety_gate(self):
        result = subprocess.run([str(self.scan_exe)], capture_output=True,
                                text=True, errors="replace", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_capacity_reset_timestamp_wrap_and_invalid_result(self):
        self.run_scenario(0)

    def test_signal_gate_equivalent_to_sorted_percentile_all_capacities(self):
        self.run_scenario(1)

    def test_conversion_start_timeout(self):
        self.run_scenario(2)

    def test_register_pointer_busy(self):
        self.run_scenario(3)

    def test_register_receive_timeout(self):
        self.run_scenario(4)

    def test_conversion_ready_timeout(self):
        self.run_scenario(5)

    def test_raw_receive_timeout_no_partial_sample(self):
        self.run_scenario(6)

    def test_probe_and_recovery_failure_remain_offline(self):
        self.run_scenario(7)

    def test_control_inflate_failure_vents_before_recovery(self):
        self.run_scenario(8)

    def test_control_pressure_tick_overflow_vents(self):
        self.run_scenario(9)

    def test_control_deflate_overflow_vents(self):
        self.run_scenario(10)

    def test_control_nonrepresentable_tick_gap_vents(self):
        self.run_scenario(16)

    def test_control_deflate_failure_vents_before_recovery(self):
        self.run_scenario(11)

    def test_pressure_text_usb_packet_boundaries(self):
        result = subprocess.run([str(self.pressure_exe)], capture_output=True,
                                text=True, errors="replace", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_actual_main_export_safety_gate(self):
        result = subprocess.run([str(self.gate_exe)], capture_output=True,
                                text=True, errors="replace", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_actual_gpio_init_and_active_low_valve_macros(self):
        result = subprocess.run([str(self.gpio_exe)], capture_output=True,
                                text=True, errors="replace", timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS", result.stdout)

    def test_cooperative_arithmetic_bit_equivalence(self):
        self.run_scenario(12)

    def test_cooperative_cancellation_yield_and_tick_wrap(self):
        self.run_scenario(13)

    def test_control_pending_calculation_cancellation(self):
        self.run_scenario(14)

    def test_main_calculation_publish_once_and_cancel(self):
        self.run_scenario(15)

    def test_pressure_parser_accepts_optional_padding(self):
        spec = importlib.util.spec_from_file_location(
            "omniprobe_analyze", PROJECT / "tools/omniprobe_analyze.py"
        )
        analyzer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analyzer)
        for flag in ("VALID", "UNCAL"):
            line = f"[Pressure] raw=7992 ads=999mV sensor=1379mV est=93.6mmHg {flag}"
            for suffix in ("\r\n", " \r\n"):
                with self.subTest(flag=flag, suffix=suffix):
                    self.assertEqual(
                        analyzer.LINE_RE.search(line + suffix).groups(),
                        ("7992", "999", "1379", "93.6", flag),
                    )


if __name__ == "__main__":
    unittest.main()
