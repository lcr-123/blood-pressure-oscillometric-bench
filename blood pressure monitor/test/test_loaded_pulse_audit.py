import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


TOOL = Path(__file__).resolve().parents[1] / "tools" / "bp_loaded_pulse_audit.py"
sys.path.insert(0, str(TOOL.parent))
spec = importlib.util.spec_from_file_location("bp_loaded_pulse_audit", TOOL)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


def bits(value):
    return struct.unpack("<I", struct.pack("<f", value))[0]


class LoadedPulseAuditTests(unittest.TestCase):
    def test_separates_sealed_leak_from_pulse_phase_notch(self):
        points = []
        for tick in range(0, 4000, 25):
            pressure = 60 - 11 * tick / 60000
            if tick == 1025:
                pressure -= 5
            points.append({"t": tick, "p": bits(pressure),
                           "v": bits((pressure + 19.887) / 82.326)})
        capture = {
            "header": {"calc": 0, "raw_kind": 2, "slope": bits(82.326),
                       "firmware": "TEST"},
            "valve": {"pulses": 15, "period_min": 200, "period_max": 200,
                      "on_min": 5, "on_max": 5},
            "points": points, "duration_ms": 3975,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "capture.ndjson"
            path.write_text("synthetic", encoding="utf-8")
            with patch.object(audit_module.bp_capture, "decode", return_value=capture):
                for width in range(1, 6):
                    capture["valve"]["on_min"] = width
                    capture["valve"]["on_max"] = width
                    result = audit_module.audit(path, 3800)
                    self.assertEqual(result["on_ms"], width)
                capture["valve"]["on_min"] = 1
                with self.assertRaisesRegex(ValueError, "expected complete"):
                    audit_module.audit(path, 3800)
        self.assertEqual(result["baseline"]["n"], 40)
        self.assertEqual(result["pulse_interval"]["n"], 120)
        self.assertAlmostEqual(result["baseline"]["fitted_rate_mmhg_min"], -11, delta=0.1)
        self.assertLess(result["phase_delta_mmhg"][1]["pressure_min"], -4.9)


if __name__ == "__main__":
    unittest.main()
