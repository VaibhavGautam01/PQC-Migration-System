import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pqc_advisor


class TestAdvisor(unittest.TestCase):
    def test_all_layers_present(self):
        recs = pqc_advisor.load_recommendations()
        for layer in ("L1", "L2", "L3", "L5", "HIDING"):
            self.assertIn(layer, recs)

    def test_ml_kem_768_sizes(self):
        rec = pqc_advisor.advise("L1")
        self.assertEqual(rec["sizes_bytes"]["public_key"], 1184)
        self.assertEqual(rec["sizes_bytes"]["ciphertext"], 1088)

    def test_ml_dsa_65_sizes(self):
        rec = pqc_advisor.advise("L5")
        self.assertEqual(rec["sizes_bytes"]["public_key"], 1952)
        self.assertEqual(rec["sizes_bytes"]["signature"], 3309)

    def test_every_layer_has_where_to_use(self):
        for rec in pqc_advisor.load_recommendations().values():
            self.assertTrue(rec["where_to_use"].strip())

    def test_unknown_layer(self):
        with self.assertRaises(KeyError):
            pqc_advisor.advise("L9")

    def test_missing_field_rejected(self):
        bad = {"records": [{"layer": "L1"}]}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bad.json"
            p.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ValueError):
                pqc_advisor.load_recommendations(p)

    def test_duplicate_layer_rejected(self):
        rec = {k: "x" for k in pqc_advisor.REQUIRED}
        rec["sizes_bytes"] = {}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "dup.json"
            p.write_text(json.dumps({"records": [rec, rec]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                pqc_advisor.load_recommendations(p)


if __name__ == "__main__":
    unittest.main()