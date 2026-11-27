"""Offline, real production-C export/replay and strict decoder regressions."""
import copy
import csv
import json
from pathlib import Path
import subprocess
import struct
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
import bp_capture
from host_build import build_replay, compiler_environment
from test_safety_contract import function_body


class CaptureExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="bp-export-test-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.work = Path(cls.temp.name)
        cls.exe = build_replay(cls.work)
        cls.raw = cls.fixture(2000)
        main = (PROJECT / 'Core/Src/main.c').read_text(encoding='utf-8')
        functions = ''
        for signature, name in (
                ('static void DeflatePulse_Cancel(void)', 'DeflatePulse_Cancel'),
                ('static void DeflatePulse_Start(uint32_t on_ms)', 'DeflatePulse_Start'),
                ('void HAL_SYSTICK_Callback(void)', 'HAL_SYSTICK_Callback')):
            functions += signature + function_body(main, name) + '\n'
        (cls.work / 'valve_pulse_under_test.h').write_text(functions, encoding='utf-8')
        import shutil
        shutil.copy2(PROJECT / 'test/host/valve_timing_regression.c', cls.work)
        compiler, env = compiler_environment()
        cls.timing_exe = cls.work / 'valve_timing.exe'
        built = subprocess.run(
            [compiler, '/nologo', '/std:c11', '/utf-8', '/W3', '/D_CRT_SECURE_NO_WARNINGS',
             'valve_timing_regression.c', 'bp_algorithm.c', 'bp_capture_export.c', f'/Fe:{cls.timing_exe}'],
            cwd=cls.work, env=env, capture_output=True, text=True, timeout=60)
        if built.returncode:
            raise AssertionError(built.stdout + built.stderr)

    @classmethod
    def fixture(cls, count, pattern=0):
        run = subprocess.run([str(cls.exe), "--fixture", str(count), str(pattern)],
                             capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise AssertionError(run.stdout + run.stderr)
        return run.stdout.splitlines()

    @staticmethod
    def rehash(records):
        lines = [json.dumps(row, separators=(",", ":")) for row in records]
        checksum = 2166136261
        for line in lines[:-1]:
            checksum = bp_capture.fnv(line.encode(), checksum)
        records[-1]["hash"] = checksum
        lines[-1] = json.dumps(records[-1], separators=(",", ":"))
        return lines

    @classmethod
    def as_v1(cls, lines):
        records = [json.loads(line) for line in lines]
        records = [row for row in records if row["type"] not in ("valve", "step", "timing", "pulse")]
        for row in records:
            row["schema"] = "bp.capture/1"
        return cls.rehash(records)

    @classmethod
    def as_v2(cls, lines):
        records = [json.loads(line) for line in lines]
        records = [row for row in records if row["type"] not in ("step", "timing", "pulse")]
        for row in records:
            row["schema"] = "bp.capture/2"
            if row["type"] == "valve":
                del row["trace_n"]
        return cls.rehash(records)

    def test_real_c_lifecycle_bounded_output_cancel_mutation_failure(self):
        run = subprocess.run([str(self.exe), "--self-test"], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("PASS", run.stdout)

    def test_actual_main_pulse_close_cancel_wrap_and_trace_failures(self):
        run = subprocess.run([str(self.timing_exe)], capture_output=True, text=True, timeout=30)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn('PASS', run.stdout)

    def test_v3_compatibility_without_full_timing(self):
        records = [json.loads(line) for line in self.raw]
        records = [row for row in records if row['type'] not in ('timing', 'pulse')]
        for row in records:
            row['schema'] = 'bp.capture/3'
        capture = bp_capture.decode(self.rehash(records))
        self.assertIsNone(capture['timing'])
        self.assertEqual(capture['pulses'], [])

    def test_full_timing_exact_wrap_and_525_pulses(self):
        capture = bp_capture.decode(self.fixture(4200))
        self.assertEqual(capture['timing']['complete'], 1)
        self.assertEqual(len(capture['pulses']), 525)
        for i, pulse in enumerate(capture['pulses']):
            self.assertEqual(pulse['open'], (0xFFFFFFFF - 400 + i * 200) & 0xFFFFFFFF)
            self.assertEqual((pulse['close'] - pulse['open']) & 0xFFFFFFFF, 1 + i % 3)
        irregular = bp_capture.decode(self.fixture(200, 4))
        self.assertEqual(irregular['timing']['complete'], 0)
        self.assertEqual(irregular['timing']['errors'], 2)
        self.assertEqual(irregular['timing']['n'], 2)

    def test_phase_audit_uses_edges_and_refuses_incomplete_trace(self):
        from bp_valve_phase_audit import audit_timing
        from bp_peak_instability import valve_observability
        capture = bp_capture.decode(self.raw)
        report = audit_timing(capture, 20, 151)
        self.assertTrue(report['complete_command_trace'])
        self.assertFalse(report['independent_pressure_reference'])
        # Absolute MCU clock starts at UINT32_MAX-400, not a multiple of 200.
        self.assertEqual(report['aligned_samples'][0]['since_open_ms'], 25)
        self.assertEqual(report['aligned_samples'][0]['since_close_ms'], 24)
        self.assertTrue(valve_observability(capture)['phase_alignment_possible'])
        capture['timing']['complete'] = 0
        self.assertFalse(valve_observability(capture)['phase_alignment_possible'])
        with self.assertRaises(ValueError):
            audit_timing(capture, 20, 151)

    def test_timing_loss_duplicates_order_forgery_rejected_even_rehashed(self):
        base = [json.loads(line) for line in self.raw]
        timing_i = next(i for i, row in enumerate(base) if row['type'] == 'timing')
        pulse_i = timing_i + 1
        variants = []
        for index in (timing_i, pulse_i, pulse_i + 5):
            rows = copy.deepcopy(base)
            del rows[index]
            variants.append(rows)
            rows = copy.deepcopy(base)
            rows.insert(index, copy.deepcopy(rows[index]))
            variants.append(rows)
        rows = copy.deepcopy(base)
        rows[pulse_i], rows[pulse_i + 1] = rows[pulse_i + 1], rows[pulse_i]
        variants.append(rows)
        for field, value in (('close', 50000), ('open', 50000), ('i', True)):
            rows = copy.deepcopy(base)
            rows[pulse_i][field] = value
            variants.append(rows)
        for field, value in (('n', 0), ('complete', 0), ('errors', 1)):
            rows = copy.deepcopy(base)
            rows[timing_i][field] = value
            variants.append(rows)
        rows = copy.deepcopy(base)
        rows[timing_i], rows[pulse_i] = rows[pulse_i], rows[timing_i]
        variants.append(rows)
        for i, rows in enumerate(variants):
            with self.subTest(i=i), self.assertRaises(ValueError):
                bp_capture.decode(self.rehash(rows))

    def test_same_source_roundtrip_success_and_capacity(self):
        for count in (2000, 2800, 3300, 4200):
            with self.subTest(count=count):
                capture = bp_capture.decode(self.raw if count == 2000 else self.fixture(count))
                report = bp_capture.replay(capture, self.exe)
                self.assertEqual(report["n"], count)
                self.assertEqual(report["duration_ms"], (count - 1) * 25)
                self.assertEqual(report["interval_min_ms"], 25)
                self.assertEqual(report["interval_max_ms"], 25)
                self.assertEqual(report["result"]["valid"], 1)
                self.assertGreater(capture["valve"]["pulses"], 1)
                self.assertEqual(sum(capture["valve"]["phase"]), capture["valve"]["steps"])
                self.assertEqual(report["valve"], capture["valve"])
                self.assertEqual(report["steps"], capture["steps"])
                self.assertTrue(report["comparison"]["validity_equal"])
                self.assertTrue(report["comparison"]["feature_bits_equal"])
                self.assertTrue(report["comparison"]["envelope_bits_equal"])

    def test_failed_calculation_retains_complete_envelopes(self):
        capture = bp_capture.decode(self.fixture(20, 1))
        self.assertEqual(capture["header"]["calc"], 3)
        self.assertIsNotNone(capture["points"][0]["e"])
        report = bp_capture.replay(capture, self.exe)
        self.assertEqual(report["result"]["valid"], 0)
        self.assertTrue(report["comparison"]["feature_bits_equal"])

    def test_irregular_ticks_survive_export_and_replay(self):
        capture = bp_capture.decode(self.fixture(200, 4))
        report = bp_capture.replay(capture, self.exe)
        self.assertEqual(report["interval_min_ms"], 1)
        self.assertEqual(report["interval_max_ms"], 255)
        self.assertEqual((capture["points"][10]["t"] - capture["points"][9]["t"]) & 0xFFFFFFFF, 255)
        self.assertEqual((capture["points"][11]["t"] - capture["points"][10]["t"]) & 0xFFFFFFFF, 1)
        self.assertTrue(report["comparison"]["envelope_bits_equal"])

    def test_count_above_capacity_is_rejected(self):
        records = [json.loads(line) for line in self.raw]
        records[0]["n"] = 4201
        with self.assertRaises(ValueError):
            bp_capture.decode([json.dumps(row) for row in records])

    def test_uncomputed_and_cancelled_envelopes_are_null(self):
        for pattern, state in ((2, 0), (3, 4)):
            capture = bp_capture.decode(self.fixture(200, pattern))
            self.assertEqual(capture["header"]["calc"], state)
            self.assertTrue(all(row["e"] is None and row["s"] is None for row in capture["points"]))
            self.assertIsNone(bp_capture.replay(capture, self.exe)["comparison"])

    def test_bp_capture_v1_remains_decodable(self):
        capture = bp_capture.decode(self.as_v1(self.raw))
        self.assertEqual(capture["header"]["schema"], "bp.capture/1")
        self.assertIsNone(capture["valve"])
        self.assertEqual(len(capture["points"]), 2000)

    def test_bp_capture_v2_remains_decodable(self):
        capture = bp_capture.decode(self.as_v2(self.raw))
        self.assertEqual(capture["header"]["schema"], "bp.capture/2")
        self.assertIsNotNone(capture["valve"])
        self.assertEqual(capture["steps"], [])

    def test_step_trace_matches_real_c_samples_and_caps_explicitly(self):
        capture = bp_capture.decode(self.fixture(200, 5))
        self.assertEqual(capture["header"]["schema"], "bp.capture/4")
        self.assertEqual(capture["valve"]["trace_n"], 6)
        self.assertEqual([row["i"] for row in capture["steps"]], [17, 18, 33, 34, 49, 50])
        self.assertEqual(capture["steps"][0]["phase"], 25)
        self.assertEqual(capture["steps"][0]["on"], 3)
        self.assertTrue(bp_capture.replay(capture, self.exe)["comparison"]["envelope_bits_equal"])
        capped = bp_capture.decode(self.fixture(200, 6))
        self.assertGreater(capped["valve"]["steps"], 12)
        self.assertEqual(capped["valve"]["trace_n"], 12)
        self.assertEqual(len(capped["steps"]), 12)

    def test_step_trace_loss_reorder_and_forgery_rejected(self):
        records = [json.loads(line) for line in self.fixture(200, 5)]
        index = next(i for i, row in enumerate(records) if row["type"] == "step")
        mutations = [
            records[:index] + records[index + 1:],
            records[:index] + [copy.deepcopy(records[index])] + records[index:],
        ]
        bad_sample = copy.deepcopy(records)
        bad_sample[index]["i"] = 20
        mutations.append(bad_sample)
        bad_phase = copy.deepcopy(records)
        bad_phase[index]["phase"] = 200
        mutations.append(bad_phase)
        bad_on = copy.deepcopy(records)
        bad_on[index]["on"] = 100
        mutations.append(bad_on)
        bad_count = copy.deepcopy(records)
        valve = next(row for row in bad_count if row["type"] == "valve")
        valve["trace_n"] -= 1
        mutations.append(bad_count)
        for mutation in mutations:
            with self.assertRaises(ValueError):
                bp_capture.decode(self.rehash(mutation))

    def test_valve_missing_duplicate_reordered_and_tampered_rejected(self):
        records = [json.loads(line) for line in self.raw]
        valve_index = next(i for i, row in enumerate(records) if row["type"] == "valve")
        features_index = next(i for i, row in enumerate(records) if row["type"] == "features")
        mutations = [
            records[:valve_index] + records[valve_index + 1:],
            records[:valve_index] + [copy.deepcopy(records[valve_index]),
                                     copy.deepcopy(records[valve_index])] + records[valve_index + 1:],
            records[:valve_index] + [copy.deepcopy(records[features_index]),
                                     copy.deepcopy(records[valve_index])] + records[features_index + 1:],
        ]
        bad_sum = copy.deepcopy(records)
        bad_sum[valve_index]["steps"] += 1
        mutations.append(bad_sum)
        bad_delta = copy.deepcopy(records)
        bad_delta[valve_index]["rise_found"] = 1
        bad_delta[valve_index]["rise_i"] = 1
        bad_delta[valve_index]["rise_d"] = struct.unpack("<I", struct.pack("<f", -6.0))[0]
        bad_delta[valve_index]["rise_phase"] = 25
        bad_delta[valve_index]["rise_on"] = 1
        mutations.append(bad_delta)
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ValueError):
                bp_capture.decode(self.rehash(mutation))

    def test_bridge_rx_only_and_csv_exact_bits(self):
        wrapped = [json.dumps({"type": "text", "lines": [
            {"direction": "tx", "text": line},
            {"direction": "rx", "text": line, "truncated": False}]}) for line in self.raw]
        capture = bp_capture.decode(["[Pressure] unrelated"] + wrapped)
        self.assertEqual(capture["raw_lines"], self.raw)
        output = self.work / "roundtrip.csv"
        bp_capture.write_csv(capture, output)
        with output.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 2000)
        self.assertEqual(int(rows[-1]["elapsed_ms"]), 49975)
        self.assertEqual(int(rows[0]["v_bits"]), capture["points"][0]["v"])
        self.assertLess(int(rows[-1]["mcu_tick_ms"]), int(rows[0]["mcu_tick_ms"]))

    def test_loss_duplicate_reorder_truncation_and_tampering_rejected(self):
        mutations = []
        for index in (0, 1, 999, len(self.raw) - 2, len(self.raw) - 1):
            mutations.append(self.raw[:index] + self.raw[index + 1:])
        mutations += [self.raw[:10] + [self.raw[9]] + self.raw[10:],
                      self.raw[:10] + [self.raw[11], self.raw[10]] + self.raw[12:],
                      self.raw + [self.raw[-1]], self.raw[:20] + self.raw,
                      [self.raw[0].replace('"raw_kind":2', '"raw_kind":1')] + self.raw[1:]]
        for record_index, field in ((1, "p"), (-2, "dbp_p")):
            rows = self.raw.copy()
            record = json.loads(rows[record_index])
            record[field] += 1
            rows[record_index] = json.dumps(record, separators=(",", ":"))
            mutations.append(rows)
        for index, rows in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ValueError):
                bp_capture.decode(rows)

    def test_schema_nonfinite_overflow_ticks_null_and_duplicate_keys_rejected(self):
        for index, key, value in ((0, "dropped", 1), (0, "calc", 1), (0, "n", 3301),
                                  (0, "cal_valid", True), (1, "p", 0x7FC00000),
                                  (1, "e", None), (1, "i", 1), (2, "t", json.loads(self.raw[1])["t"]),
                                  (1, "v", -1), (0, "raw_kind", 0)):
            with self.subTest(index=index, key=key, value=value):
                rows = [json.loads(row) for row in self.raw]
                rows[index][key] = value
                with self.assertRaises(ValueError):
                    bp_capture.decode(self.rehash(rows))
        duplicate = self.raw.copy()
        duplicate[0] = duplicate[0].replace('"n":2000', '"n":2000,"n":2000')
        with self.assertRaises(ValueError):
            bp_capture.decode(duplicate)
        with self.assertRaises(ValueError):
            bp_capture.decode([json.dumps({"type": "text", "lines": [
                {"direction": "rx", "truncated": True, "text": self.raw[0]}]})])

    def test_replay_firmware_mismatch_rejected(self):
        capture = copy.deepcopy(bp_capture.decode(self.raw))
        capture["header"]["firmware"] = "OLD"
        with self.assertRaises(ValueError):
            bp_capture.replay(capture, self.exe)

    def test_cli_end_to_end_and_no_overwrite(self):
        source, output = self.work / "capture.ndjson", self.work / "capture_out.ndjson"
        source.write_text("\n".join(self.raw) + "\n", encoding="utf-8")
        decoded = subprocess.run([sys.executable, str(PROJECT / "tools/bp_capture.py"),
                                  str(source), "--decode-only"],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(decoded.returncode, 0, decoded.stdout + decoded.stderr)
        self.assertEqual(json.loads(decoded.stdout)["valve"], bp_capture.decode(self.raw)["valve"])
        report = self.work / "replay.json"
        command = [sys.executable, str(PROJECT / "tools/bp_capture.py"), str(source),
                   "--ndjson", str(output), "--report", str(report)]
        run = subprocess.run(command, capture_output=True, text=True, timeout=60)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertTrue(json.loads(report.read_text(encoding="utf-8"))["comparison"]["envelope_bits_equal"])
        self.assertEqual(bp_capture.decode(output.read_text().splitlines())["points"], bp_capture.decode(self.raw)["points"])
        run = subprocess.run(command, capture_output=True, text=True, timeout=30)
        self.assertNotEqual(run.returncode, 0)


if __name__ == "__main__":
    unittest.main()
