import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import signed_variant as sv  # type: ignore # noqa: E402


class TestSignatureTable(unittest.TestCase):
    def test_options_and_order(self):
        rows = sv.signature_table("keyless")
        self.assertEqual([r["option"] for r in rows],
                         ["none", "rsa_signature_pss*", "ml_dsa_65*", "slh_dsa*"])
        self.assertIsNone(rows[0]["overall"])           # no signature is not a score
        self.assertEqual(round(rows[1]["overall"], 1), 50.8)
        self.assertEqual(rows[1]["band"], "High")
        self.assertEqual(round(rows[2]["overall"], 1), 4.7)
        self.assertEqual(rows[2]["band"], "Low")


class TestProjectVariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = sv.project_variants(256, 2048)

    def test_image_values(self):
        img = self.res["image"]
        self.assertEqual(round(img["before"]["project"], 1), 91.9)
        self.assertEqual(round(img["unsigned"]["project"], 1), 4.7)
        self.assertEqual(round(img["signed"]["project"], 1), 4.7)

    def test_video_values(self):
        vid = self.res["video"]
        self.assertEqual(round(vid["before"]["project"], 1), 64.1)
        self.assertEqual(round(vid["unsigned"]["project"], 1), 6.9)
        self.assertEqual(round(vid["signed"]["project"], 1), 6.8)

    def test_layers_without_crypto_are_not_listed(self):
        for project in self.res.values():
            for state in project.values():
                self.assertFalse([k for k in state["layers"] if "none" in k.lower()])

    def test_migration_lowers_every_project(self):
        for project in self.res.values():
            self.assertLess(project["unsigned"]["project"], project["before"]["project"])
            self.assertLess(project["signed"]["project"], project["before"]["project"])

    def test_signature_only_lowers_the_score_by_averaging(self):
        for project in self.res.values():
            d = project["unsigned"]["project"] - project["signed"]["project"]
            self.assertGreaterEqual(d, 0)
            self.assertLess(d, 0.5)

    def test_bigger_old_key_never_lowers_before_score(self):
        low = sv.project_variants(256, 1024)["video"]["before"]["project"]
        high = sv.project_variants(256, 3072)["video"]["before"]["project"]
        self.assertGreaterEqual(low, high)


if __name__ == "__main__":
    unittest.main()