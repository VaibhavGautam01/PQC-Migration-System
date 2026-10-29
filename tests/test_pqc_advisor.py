import json
import tempfile
import unittest
from pathlib import Path

from src.pqc_advisor import load_recommendations, recommend, REQUIRED


class AdvisorTests(unittest.TestCase):
    def test_all_layers_present_with_all_fields(self):
        recs = load_recommendations()
        for layer in ("L1", "L2", "L3", "L5", "HIDE"):
            self.assertIn(layer, recs)
        for r in recs.values():
            for f in REQUIRED:
                self.assertIsNotNone(getattr(r, f))
                self.assertTrue(getattr(r, f) != "")

    def test_l1_is_ml_kem_768(self):
        r = recommend("L1")
        self.assertEqual(r.parameter_set, "ML-KEM-768")
        self.assertEqual(r.sizes_bytes["ciphertext"], 1088)

    def test_l5_sizes(self):
        r = recommend("L5")
        self.assertEqual(r.sizes_bytes["signature"], 3309)
        self.assertEqual(r.sizes_bytes["public_key"], 1952)

    def test_unknown_layer(self):
        with self.assertRaises(KeyError):
            recommend("L99")

    def test_missing_field_rejected(self):
        bad = {"recommendations": [{"layer": "L1"}]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_recommendations(p)


if __name__ == "__main__":
    unittest.main()
