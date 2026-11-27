"""Catalog keeps transfer validity distinct from experimental metadata."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tools"))
import bp_capture_catalog
from host_build import build_replay


class CaptureCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="bp-catalog-test-")
        cls.addClassCleanup(cls.temp.cleanup)
        exe = build_replay(Path(cls.temp.name))
        run = subprocess.run([str(exe), "--fixture", "20", "1"],
                             capture_output=True, text=True, timeout=30)
        if run.returncode:
            raise AssertionError(run.stdout + run.stderr)
        cls.lines = run.stdout.splitlines()

    def test_dedup_bridge_and_partial_export(self):
        with tempfile.TemporaryDirectory(prefix="bp-catalog-files-") as directory:
            root = Path(directory)
            raw = root / "raw"
            raw.mkdir()
            (raw / "a.ndjson").write_text("\n".join(self.lines) + "\n", encoding="utf-8")
            wrapped = [json.dumps({"type": "text", "lines": [
                {"direction": "rx", "text": line, "truncated": False}]})
                       for line in self.lines]
            (raw / "b.ndjson").write_text("\n".join(wrapped) + "\n", encoding="utf-8")
            (raw / "partial.ndjson").write_text("\n".join(self.lines[:-1]) + "\n",
                                                encoding="utf-8")
            result = bp_capture_catalog.catalog(raw, root)
            self.assertEqual(result["summary"], {
                "files": 3, "decode_valid_files": 2, "decode_failed_files": 1,
                "unique_captures": 1, "duplicate_files": 1,
                "release_ready_captures": 0})
            first, second, failed = result["files"]
            self.assertEqual(second["duplicate_of"], first["path"])
            self.assertNotEqual(second["file_sha256"], first["file_sha256"])
            self.assertEqual(first["calc_state"], 3)
            self.assertFalse(first["release_ready"])
            self.assertTrue(all(value is None for value in first["metadata"].values()))
            self.assertEqual(first["replay_status"], "not_run")
            self.assertEqual(failed["status"], "decode_failed")
            self.assertIn("end", failed["error"])


if __name__ == "__main__":
    unittest.main()
