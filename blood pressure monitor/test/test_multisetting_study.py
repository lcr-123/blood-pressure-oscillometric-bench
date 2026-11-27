"""Regression checks for the development-only multi-setting inventory."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'blood pressure monitor' / 'tools'))
from bp_multisetting_study import GATE, MANIFEST, study


class MultisettingStudyTests(unittest.TestCase):
    def test_seen_runs_cannot_fit_a_three_setting_bp_model(self):
        result = study()
        self.assertFalse(result['bp_model_fitted'])
        self.assertIsNone(result['bp_coefficients'])
        self.assertEqual([row['envelope_candidates'] for row in result['settings']],
                         [4, 1, 0])
        self.assertEqual([row['comparable_known_volume_repeats']
                          for row in result['settings']], [2, 1, 0])
        self.assertTrue(all(not row['feature_repeatability_ready']
                            for row in result['settings']))
        self.assertIn('cross_run_zero_comparability_unresolved',
                      result['settings'][0]['fit_blockers'])
        self.assertIn('high_pressure_tail_or_bound_unresolved',
                      result['settings'][2]['fit_blockers'])
        self.assertTrue(all(row['height_peak_mmhg'] is None
                            for row in result['settings'][2]['runs']))

    def test_modified_gate_cannot_be_combined_with_manifest(self):
        gate = json.loads(GATE.read_text(encoding='utf-8-sig'))
        gate['manifest_sha256'] = '0' * 64
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'gate.json'
            path.write_text(json.dumps(gate), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'gate/manifest hash mismatch'):
                study(MANIFEST, path)


if __name__ == '__main__':
    unittest.main()
