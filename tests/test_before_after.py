import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import before_after as ba  # type: ignore # noqa: E402


class TestCompare(unittest.TestCase):
    def test_512_matches_worked_values(self):
        r = ba.compare(512)
        self.assertEqual(round(r["before"]["overall"], 1), 90.4)
        self.assertEqual(round(r["after"]["overall"], 1), 4.7)

    def test_256_before(self):
        r = ba.compare(256)
        self.assertEqual(round(r["before"]["overall"], 1), 91.9)
        self.assertEqual(r["before"]["band"], "Critical")

    def test_after_is_low_and_lower_for_every_size(self):
        for bits in (32, 256, 512, 1024, 2048):
            with self.subTest(bits=bits):
                r = ba.compare(bits)
                self.assertEqual(r["after"]["band"], "Low")
                self.assertLess(r["after"]["overall"], r["before"]["overall"])
                self.assertGreater(r["drop"], 0)

    def test_after_does_not_depend_on_old_key_size(self):
        self.assertEqual(ba.compare(256)["after"]["overall"], ba.compare(2048)["after"]["overall"])

    def test_project_score_with_one_layer_equals_layer_score(self):
        r = ba.compare(512)
        self.assertAlmostEqual(r["project_before"], r["before"]["overall"])
        self.assertAlmostEqual(r["project_after"], r["after"]["overall"])

    def test_after_is_below_floor_cap(self):
        for z in (5, 10, 20):
            self.assertLessEqual(ba.compare(512, z_years=z)["after"]["overall"], 5.0)


class TestFloorAndSensitivity(unittest.TestCase):
    def test_floor_explains_every_remaining_factor(self):
        floor = {f["factor"].split()[0]: f["value"] for f in ba.remaining_floor(ba.compare(512)["after"])}
        self.assertEqual(floor["F1"], 5.0)
        self.assertEqual(floor["F4"], 5.0)
        self.assertEqual(floor["F5_eff"], 3.5)
        self.assertEqual(floor["F6_eff"], 5.0)

    def test_after_below_before_in_every_draw(self):
        s = ba.sensitivity(256, n_draws=60)
        for part in ("narrow_random", "wide_random"):
            self.assertEqual(s[part]["after_below_before_fraction"], 1.0)
            self.assertGreater(s[part]["smallest_drop"], 0)

    def test_run_names_version_and_label(self):
        res = ba.run((256,), n_draws=20)
        self.assertEqual(res["weights_version"], "v0.1")
        self.assertIn("not a probability", res["label"])
        self.assertEqual(len(res["rows"]), 1)


if __name__ == "__main__":
    unittest.main()