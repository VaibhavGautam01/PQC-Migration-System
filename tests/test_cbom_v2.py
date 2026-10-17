import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_cbom_v2

REQUIRED_FIELDS = {"component", "project", "layer", "risk_percent", "band",
                   "recommendation", "post_migration_risk_percent"}


class TestCbomV2(unittest.TestCase):
    def test_entries_have_required_fields(self):
        doc = build_cbom_v2.build()
        self.assertTrue(doc["entries"])
        for e in doc["entries"]:
            self.assertTrue(REQUIRED_FIELDS <= e.keys())

    def test_recommendation_comes_from_advisor(self):
        e = build_cbom_v2.build()["entries"][0]
        self.assertIn("ML-KEM-768", e["recommendation"])

    def test_no_invented_numbers(self):
        e = build_cbom_v2.build()["entries"][0]
        self.assertIsNone(e["risk_percent"])
        self.assertIsNone(e["post_migration_risk_percent"])


if __name__ == "__main__":
    unittest.main()