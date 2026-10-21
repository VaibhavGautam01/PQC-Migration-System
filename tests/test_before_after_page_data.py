import ast
import unittest
from pathlib import Path

from src import before_after_page_data as D

ROOT = Path(__file__).resolve().parent.parent


class BeforeAfterPageDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = D.load()

    def test_committed_file_loads_with_both_sizes(self):
        self.assertIsNotNone(self.data)
        self.assertEqual(D.size_options(self.data), [256, 512])

    def test_after_is_below_before_for_every_size(self):
        for bits in D.size_options(self.data):
            s = D.summary(D.row_for(self.data, bits))
            self.assertLess(s["after"], s["before"])
            self.assertAlmostEqual(s["drop"], s["before"] - s["after"], places=6)

    def test_reference_values_after_migration(self):
        s = D.summary(D.row_for(self.data, 512))
        self.assertEqual((round(s["before"], 1), round(s["after"], 1)), (90.4, 4.7))
        self.assertEqual(s["after_band"], "Low")

    def test_factor_and_part_rows(self):
        row = D.row_for(self.data, 256)
        self.assertEqual(len(D.factor_rows(row)), 6)
        self.assertEqual([p["part"] for p in D.parts_rows(row)], ["Quantum", "Classical", "Overall"])

    def test_scenarios_cover_every_z(self):
        self.assertEqual([r["z"] for r in D.scenario_rows(D.row_for(self.data, 256))], [5, 10, 20])

    def test_sensitivity_says_after_always_lower(self):
        for r in D.sensitivity_rows(D.row_for(self.data, 256)):
            self.assertEqual(r["after_below_before"], 1.0)

    def test_floor_is_listed_and_not_zero(self):
        rows = D.floor_rows(self.data)
        self.assertTrue(rows)
        self.assertTrue(all(r["value"] > 0 for r in rows))

    def test_missing_file_returns_none(self):
        self.assertIsNone(D.load(ROOT / "outputs" / "does_not_exist.json"))


class DashboardWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / "src" / "live_dashboard.py").read_text(encoding="utf-8-sig")

    def test_page_function_exists_and_is_registered(self):
        names = {n.name for n in ast.walk(ast.parse(self.src)) if isinstance(n, ast.FunctionDef)}
        self.assertIn("page_before_after", names)
        self.assertIn('"\U0001f501 Before and after": page_before_after', self.src)

    def test_page_states_it_is_not_a_probability(self):
        self.assertIn("not a probability", self.src)


if __name__ == "__main__":
    unittest.main()
