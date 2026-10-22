"""Tests for the sensitivity script (small draw counts keep them fast)."""
import copy
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import sensitivity as sv  # type: ignore # noqa: E402
from risk_score import load_weights  # type: ignore # noqa: E402


class TestPerturbation(unittest.TestCase):
    def setUp(self):
        self.base = load_weights()

    def assert_groups_sum_to_one(self, w):
        for g in sv.GROUPS:
            self.assertAlmostEqual(sum(w[g].values()), 1.0, msg=g)

    def test_one_at_a_time_rescales_group(self):
        w = sv.one_at_a_time(self.base, "quantum_weights", "f1", 1.2)
        self.assert_groups_sum_to_one(w)
        self.assertGreater(w["quantum_weights"]["f1"], self.base["quantum_weights"]["f1"])

    def test_base_weights_not_modified(self):
        before = copy.deepcopy(self.base)
        sv.one_at_a_time(self.base, "classical_weights", "f3", 0.8)
        sv.narrow_draw(self.base, random.Random(1))
        sv.wide_draw(self.base, random.Random(1))
        self.assertEqual(before, self.base)

    def test_narrow_draw_stays_close_and_sums_to_one(self):
        w = sv.narrow_draw(self.base, random.Random(7))
        self.assert_groups_sum_to_one(w)
        for g in sv.GROUPS:
            for k, v in w[g].items():
                self.assertLess(abs(v - self.base[g][k]), 0.2)

    def test_wide_draw_sums_to_one_and_is_positive(self):
        w = sv.wide_draw(self.base, random.Random(7))
        self.assert_groups_sum_to_one(w)
        self.assertTrue(all(v > 0 for g in sv.GROUPS for v in w[g].values()))


class TestRun(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = sv.run(n_draws=60)

    def test_baseline_matches_worked_values(self):
        b = self.result["baseline"]
        self.assertEqual([round(b[n], 1) for n in sv.CASES], [90.4, 80.9, 50.8, 4.7])

    def test_one_at_a_time_covers_every_weight_twice(self):
        self.assertEqual(len(self.result["one_at_a_time"]), 2 * 10)

    def test_same_seed_same_result(self):
        again = sv.run(n_draws=60)
        self.assertEqual(self.result["narrow_random"], again["narrow_random"])
        self.assertEqual(self.result["wide_random"], again["wide_random"])

    def test_different_seed_changes_draws(self):
        other = sv.run(n_draws=60, seed=7)
        self.assertNotEqual(self.result["narrow_random"]["cases"], other["narrow_random"]["cases"])

    def test_ranges_are_consistent(self):
        for part in ("narrow_random", "wide_random"):
            for c in self.result[part]["cases"].values():
                self.assertLessEqual(c["min"], c["p05"])
                self.assertLessEqual(c["p05"], c["p95"])
                self.assertLessEqual(c["p95"], c["max"])
                self.assertLessEqual(c["min"], c["mean"])
                self.assertLessEqual(c["mean"], c["max"])

    def test_assumption_grid_has_nine_combinations(self):
        self.assertEqual(len(self.result["assumption_grid"]), 9)

    def test_result_names_version_and_seed(self):
        self.assertEqual(self.result["weights_version"], "v1.0")
        self.assertEqual(len(self.result["weights_sha256"]), 64)
        self.assertEqual(self.result["seed"], 42)

    def test_order_helper(self):
        self.assertTrue(sv.order_holds({"RSA-512 no padding": 4, "RSA-1024 no padding": 3,
                                        "RSA-2048 OAEP": 2, "ML-KEM-768 + AES-256-GCM": 1}))
        self.assertFalse(sv.order_holds({"RSA-512 no padding": 3, "RSA-1024 no padding": 4,
                                         "RSA-2048 OAEP": 2, "ML-KEM-768 + AES-256-GCM": 1}))

    def test_percentile(self):
        self.assertEqual(sv.percentile([1, 2, 3, 4, 5], 0.5), 3)
        self.assertEqual(sv.percentile([1, 2, 3, 4, 5], 0), 1)
        self.assertEqual(sv.percentile([1, 2, 3, 4, 5], 1), 5)


if __name__ == "__main__":
    unittest.main()