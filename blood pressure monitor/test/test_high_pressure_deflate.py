"""Host checks for the production high-target deflation speed selector."""

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from test_safety_contract import function_body


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = (PROJECT / "Core/Src/main.c").read_text(encoding="utf-8")


class HighPressureDeflateTests(unittest.TestCase):
    def test_production_speed_selector_boundaries(self):
        import sys
        sys.path.insert(0, str(PROJECT / "tools"))
        from host_build import compiler_environment

        try:
            compiler, env = compiler_environment()
        except FileNotFoundError as exc:
            raise unittest.SkipTest(str(exc)) from exc
        constants = "\n".join(re.search(rf"^#define {name} .*$", SOURCE, re.MULTILINE).group(0)
                              for name in ("DEFLATE_HIGH_TARGET_MMHG",
                                           "DEFLATE_NORMAL_SPEED_MMHG_S",
                                           "DEFLATE_HIGH_SPEED_MMHG_S",
                                           "DEFLATE_PEAK_LOW_MMHG",
                                           "DEFLATE_PEAK_HIGH_MMHG",
                                           "DEFLATE_PEAK_SPEED_MMHG_S"))
        selector = "static float DeflateTargetSpeed(void) " + function_body(
            SOURCE, "DeflateTargetSpeed")
        code = ("#include <assert.h>\n#include <stdint.h>\n" + constants +
                "\nstatic uint8_t s_deflate_test_active;\n"
                "static uint8_t s_peak_profile_enabled;\n"
                "static float s_inflate_target_mmhg, g_last_pressure_mmhg;\n" + selector +
                "\nint main(void) {\n"
                "s_inflate_target_mmhg=170.0f; assert(DeflateTargetSpeed()==2.0f);\n"
                "s_inflate_target_mmhg=199.9f; assert(DeflateTargetSpeed()==2.0f);\n"
                "s_inflate_target_mmhg=200.0f; assert(DeflateTargetSpeed()==3.0f);\n"
                "s_inflate_target_mmhg=220.0f; assert(DeflateTargetSpeed()==3.0f);\n"
                "s_peak_profile_enabled=1U;\n"
                "g_last_pressure_mmhg=245.01f; assert(DeflateTargetSpeed()==3.0f);\n"
                "g_last_pressure_mmhg=245.0f; assert(DeflateTargetSpeed()==1.8f);\n"
                "g_last_pressure_mmhg=220.0f; assert(DeflateTargetSpeed()==1.8f);\n"
                "g_last_pressure_mmhg=200.0f; assert(DeflateTargetSpeed()==1.8f);\n"
                "g_last_pressure_mmhg=199.99f; assert(DeflateTargetSpeed()==3.0f);\n"
                "s_inflate_target_mmhg=199.99f; g_last_pressure_mmhg=220.0f; assert(DeflateTargetSpeed()==2.0f);\n"
                "s_inflate_target_mmhg=275.0f;\n"
                "s_deflate_test_active=1U; assert(DeflateTargetSpeed()==2.0f);\n"
                "return 0; }\n")
        with tempfile.TemporaryDirectory(prefix="bp-high-deflate-") as folder:
            work = Path(folder)
            (work / "test.c").write_text(code, encoding="utf-8")
            exe = work / "test.exe"
            built = subprocess.run([compiler, "/nologo", "/std:c11", "/utf-8",
                                    "test.c", f"/Fe:{exe}"], cwd=work, env=env,
                                   capture_output=True, text=True, errors="replace", timeout=60)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            run = subprocess.run([str(exe)], cwd=work, capture_output=True,
                                 text=True, errors="replace", timeout=10)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)

    def test_active_target_change_is_rejected_before_assignment(self):
        body = function_body(SOURCE, "Process_DebugCommand")
        branch = body.split("else if (command == DEBUG_CMD_TARGET)", 1)[1].split(
            "else if (command == DEBUG_CMD_MOTOR)", 1)[0]
        self.assertLess(branch.index("CaptureAcquisition_IsActive()"),
                        branch.index("s_inflate_target_mmhg = target"))
        self.assertIn("[Target] rejected: acquisition active", branch)
        loop = SOURCE.split("else if (s_deflate_pwm_enabled)", 1)[1]
        self.assertIn("float target_speed = DeflateTargetSpeed();", loop)
        self.assertIn("BP_FAULT_SAMPLE_OVERFLOW", loop)

    def test_firmware_identity_is_queryable_before_high_target_start(self):
        parser = SOURCE.split('strcmp(s_debug_cmd_buffer, "version")', 1)[1]
        self.assertIn("DEBUG_CMD_VERSION", parser)
        command = function_body(SOURCE, "Process_DebugCommand")
        self.assertIn("command == DEBUG_CMD_VERSION", command)
        self.assertIn("Debug_PrintFirmwareVersion();", command)
        runner = (PROJECT.parent / "tmp/bp_standard200_150_capture_20261101.py").read_text(encoding="utf-8")
        self.assertLess(runner.index("b.command('version'"), runner.index("b.command('target 220'"))


if __name__ == "__main__":
    unittest.main()
