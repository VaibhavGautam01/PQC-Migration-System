import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import before_after_video as bav  # type: ignore # noqa: E402


class TestCompareVideo(unittest.TestCase):
    def test_before_matches_the_risk_run_value_for_the_ui_default(self):
        # outputs/risk_scores.json scores the video project at the UI default 2048 bits
        r = bav.compare(2048)
        self.assertEqual(round(r["layers"]["L1"]["before"]["overall"], 1), 71.8)
        self.assertEqual(round(r["layers"]["L2"]["before"]["overall"], 1), 35.8)
        self.assertEqual(round(r["layers"]["L3"]["before"]["overall"], 1), 30.4)
        self.assertEqual(round(r["project_before"], 1), 64.1)

    def test_migrated_layers_score_lower_after(self):
        for bits in (1024, 2048, 3072):
            r = bav.compare(bits)
            for layer in ("L1", "L3"):
                v = r["layers"][layer]
                self.assertLess(v["after"]["overall"], v["before"]["overall"], (bits, layer))
            self.assertEqual(r["layers"]["L1"]["after"]["band"], "Low")
            self.assertGreater(r["project_drop"], 0)

    def test_l2_is_not_credited_and_keeps_its_before_value(self):
        r = bav.compare(2048)
        self.assertIsNone(r["layers"]["L2"]["after"])
        # weakest link: after the migration L2 is the worst layer, so it sets the project score
        worst = r["layers"]["L2"]["before"]["overall"]
        self.assertGreater(r["project_after"], 0.7 * worst)

    def test_bigger_rsa_key_never_raises_the_before_score(self):
        scores = [bav.compare(b)["project_before"] for b in (1024, 2048, 3072)]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_after_does_not_depend_on_the_rsa_size(self):
        afters = {round(bav.compare(b)["project_after"], 6) for b in (1024, 2048, 3072)}
        self.assertEqual(len(afters), 1)

    def test_aes_gcm_tag_has_grover_exposure_that_crc32_lacks(self):
        # honest detail: quantum % rises from 0 to 9 for L3, overall still falls
        r = bav.compare(2048)["layers"]["L3"]
        self.assertEqual(r["before"]["quantum"], 0.0)
        self.assertGreater(r["after"]["quantum"], 0.0)
        self.assertLess(r["after"]["overall"], r["before"]["overall"])


class TestRunVideo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.res = bav.run((2048,), n_draws=30)

    def test_records_version_label_and_open_question(self):
        self.assertEqual(self.res["weights_version"], "v1.0")
        self.assertIn("not a probability", self.res["label"])
        self.assertIn("L2", self.res["not_credited"])
        self.assertEqual(self.res["project"], "video")

    def test_after_below_before_in_every_random_draw(self):
        for name, v in self.res["rows"][0]["sensitivity"].items():
            self.assertEqual(v["after_below_before_fraction"], 1.0, name)

    def test_z_scenarios_present_and_after_below_before(self):
        z = self.res["rows"][0]["z_scenarios"]
        self.assertEqual(sorted(z), [5, 10, 20] if isinstance(next(iter(z)), int) else ["10", "20", "5"])
        for v in z.values():
            self.assertLess(v["after"], v["before"])


if __name__ == "__main__":
    unittest.main()
