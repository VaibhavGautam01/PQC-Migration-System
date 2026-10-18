import json
import tempfile
import unittest
from pathlib import Path

from src import risk_run as RR


class RiskRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as d:
            cls.out = RR.run(out_path=Path(d) / "risk_scores.json")
        cls.image = cls.out["projects"]["image"]
        cls.video = cls.out["projects"]["video"]

    def test_both_projects_scored_in_range(self):
        for p in (self.image, self.video):
            self.assertTrue(0 <= p["project_score"] <= 100)
            self.assertIn(p["band"], ("Low", "Moderate", "High", "Critical"))

    def test_scenarios_follow_z(self):
        # a sooner quantum computer (smaller Z) never lowers the score
        for p in (self.image, self.video):
            s = p["L1"]["z_scenarios"]
            self.assertGreaterEqual(s["5"]["overall"], s["10"]["overall"])
            self.assertGreaterEqual(s["10"]["overall"], s["20"]["overall"])
            self.assertEqual(p["z_range"]["max"], s["5"]["overall"])
            self.assertEqual(p["z_range"]["min"], s["20"]["overall"])

    def test_central_value_matches_central_scenario(self):
        for p in (self.image, self.video):
            self.assertEqual(p["L1"]["score"]["overall"], p["L1"]["z_scenarios"]["10"]["overall"])

    def test_image_scores_above_video(self):
        # 256-bit key, keyless embedding vs 2048-bit key, bypassable header
        self.assertGreater(self.image["project_score"], self.video["project_score"])

    def test_smaller_key_never_scores_lower(self):
        v = self.video["L1"]
        self.assertGreaterEqual(v["variants"][0]["overall"], v["score"]["overall"])  # 1024 vs 2048

    def test_only_l1_is_scored_for_now(self):
        for p in (self.image, self.video):
            self.assertEqual(p["layers_scored"], ["L1"])
            self.assertEqual(p["layers_not_scored_yet"], ["L2", "L3", "L5"])

    def test_assumptions_and_weights_version_recorded(self):
        self.assertEqual(self.out["weights_version"], "v0.1")
        self.assertEqual(self.out["assumptions"]["X_secret_years"], 5)
        self.assertEqual(sorted(self.out["assumptions"]["Z_scenarios"]), [5, 10, 20])

    def test_single_project_option_and_file_written(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            out = RR.run(("video",), out_path=p)
            self.assertEqual(list(out["projects"]), ["video"])
            self.assertEqual(list(json.loads(p.read_text())["projects"]), ["video"])

    def test_unknown_project_rejected(self):
        with self.assertRaises(ValueError):
            RR.score_project("audio")


if __name__ == "__main__":
    unittest.main()
