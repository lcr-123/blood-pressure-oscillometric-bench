import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
STARTUP = PROJECT / "MDK-ARM" / "startup_stm32f103xe.s"
SOURCE = PROJECT / "Core" / "Src" / "stack_watermark.c"
HEADER = PROJECT / "Core" / "Inc" / "stack_watermark.h"
sys.path.insert(0, str(PROJECT / "tools"))
from host_build import compiler_environment


class StackWatermarkContractTests(unittest.TestCase):
    def test_startup_exports_exact_stack_and_main_initializes_first(self):
        startup = STARTUP.read_text(encoding="utf-8")
        main = (PROJECT / "Core" / "Src" / "main.c").read_text(encoding="utf-8")
        self.assertIn("EXPORT  __stack_base", startup)
        self.assertIn("EXPORT  __initial_sp", startup)
        self.assertNotIn("Stack_Fill_Loop", startup)
        main_body = main.split("int main(void)", 1)[1].split("HAL_Init();", 1)[0]
        self.assertIn("StackWatermark_Init();", main_body)

    def test_configuration_and_keil_project_keep_4k_stack_and_sources(self):
        ioc = (PROJECT / "blood pressure monitor.ioc").read_text(encoding="utf-8")
        project = (PROJECT / "MDK-ARM" / "blood pressure monitor.uvprojx").read_text(
            encoding="utf-8"
        )
        self.assertIn("ProjectManager.StackSize=0x1000", ioc)
        self.assertIn("Stack_Size      EQU     0x00001000", STARTUP.read_text(encoding="utf-8"))
        self.assertIn("../Core/Src/stack_watermark.c", project)
        self.assertIn("../Core/Inc/stack_watermark.h", project)

    def test_command_is_read_only_and_reports_all_budget_fields(self):
        main = (PROJECT / "Core" / "Src" / "main.c").read_text(encoding="utf-8")
        self.assertIn('strcmp(s_debug_cmd_buffer, "stack")', main)
        branch = main.split("else if (command == DEBUG_CMD_STACK)", 1)[1].split(
            "else if", 1
        )[0]
        self.assertIn("Debug_PrintStackWatermark();", branch)
        for actuator in ("PUMP_", "VALVE1_", "VALVE2_", "ADS1115_", "BP_Cal_"):
            self.assertNotIn(actuator, branch)
        for field in ("used=", "free=", "reserved=", "saturated=", "pattern="):
            self.assertIn(field, main)


class StackWatermarkScanTests(unittest.TestCase):
    def test_scan_boundaries_and_invalid_arguments_in_production_c(self):
        harness = textwrap.dedent(
            r"""
            #include <stdint.h>
            #include "stack_watermark.h"

            uint32_t __stack_base;
            uint32_t __initial_sp;

            static int check(uint32_t changed_words, uint32_t expected_used)
            {
                uint32_t words[16];
                StackWatermark_Result_t result;
                uint32_t i;
                for (i = 0U; i < 16U; i++) words[i] = STACK_WATERMARK_PATTERN;
                for (i = 0U; i < changed_words; i++) words[15U - i] = i;
                if (StackWatermark_ScanRange(words, words + 16, &result) == 0U) return 1;
                if (result.reserved_bytes != 64U) return 2;
                if (result.used_bytes != expected_used) return 3;
                if (result.free_bytes != (64U - expected_used)) return 4;
                if (result.saturated != (expected_used == 64U)) return 5;
                return 0;
            }

            static int check_init(void)
            {
                uint32_t words[1024];
                uint32_t i;
                uintptr_t base = (uintptr_t)words;
                uintptr_t top = (uintptr_t)(words + 1024);
                uintptr_t current_sp = top - 64U;
                uintptr_t fill_end = (current_sp - STACK_WATERMARK_GUARD_BYTES) &
                                     ~((uintptr_t)sizeof(uint32_t) - 1U);
                for (i = 0U; i < 1024U; i++) words[i] = 0U;
                if (StackWatermark_InitRange(words, words + 1024, current_sp) == 0U) return 20;
                for (i = 0U; i < 1024U; i++)
                {
                    uintptr_t address = (uintptr_t)&words[i];
                    uint32_t expected = (address < fill_end) ? STACK_WATERMARK_PATTERN : 0U;
                    if (words[i] != expected) return 21;
                }
                if (StackWatermark_InitRange(words, words + 1024, base + 64U) != 0U) return 22;
                if (StackWatermark_InitRange(words, words + 1024, top + 4U) != 0U) return 23;
                return 0;
            }

            int main(void)
            {
                uint32_t words[4] = {0U};
                StackWatermark_Result_t result;
                if (check(0U, 0U) != 0) return 10;
                if (check(1U, 4U) != 0) return 11;
                if (check(8U, 32U) != 0) return 12;
                if (check(16U, 64U) != 0) return 13;
                if (StackWatermark_ScanRange(words, words, &result) != 0U) return 14;
                if (StackWatermark_ScanRange(words + 1, words, &result) != 0U) return 15;
                if (StackWatermark_ScanRange(words, words + 4, 0) != 0U) return 16;
                if (check_init() != 0) return 17;
                return 0;
            }
            """
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                compiler, env = compiler_environment()
            except FileNotFoundError as exc:
                self.skipTest(str(exc))
            temp = Path(temp_dir)
            harness_path = temp / "stack_watermark_test.c"
            executable = temp / "stack_watermark_test.exe"
            harness_path.write_text(harness, encoding="utf-8")
            compile_result = subprocess.run(
                [
                    compiler,
                    "/nologo",
                    "/W4",
                    "/WX",
                    f"/I{HEADER.parent}",
                    str(harness_path),
                    str(SOURCE),
                    f"/Fe:{executable}",
                ],
                cwd=temp,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)
            run_result = subprocess.run([str(executable)], check=False)
            self.assertEqual(run_result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
