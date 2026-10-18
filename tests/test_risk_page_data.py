import ast
import json
import tempfile
import unittest
from pathlib import Path

from src import risk_page_data as D


class RiskPageDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scores = D.load_scores()

    def test_committed_scores_file_loads(self):
        self.assertIsNotNone(self.scores)
        self.assertEqual(set(self.scores["projects"]), {"image", "video"})

    def test_summary_has_one_row_per_project_with_valid_band(self):
        rows = D.summary_rows(self.scores)
        self.assertEqual({r["project"] for r in rows}, {"image", "video"})
        for r in rows:
            self.assertIn(r["band"], D.BAND_COLORS)
            self.assertLessEqual(r["z_min"], r["score"])
            self.assertGreaterEqual(r["z_max"], r["score"])

    def test_scenarios_cover_every_z(self):
        rows = D.scenario_rows(self.scores)
        for proj in ("image", "video"):
            self.assertEqual([r["z"] for r in rows if r["project"] == proj], [5, 10, 20])

    def test_factor_rows_cover_all_six_factors(self):
        rows = D.factor_rows(self.scores["projects"]["video"])
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(0 <= v <= 100 for _, v, _ in rows if v is not None))

    def test_variants_are_listed_separately(self):
        v = D.variant_rows(self.scores["projects"]["video"])
        self.assertEqual([x["modulus_bits"] for x in v], [1024])

    def test_missing_or_broken_file_gives_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(D.load_scores(Path(d) / "nope.json"))
            bad = Path(d) / "bad.json"
            bad.write_text("{not json")
            self.assertIsNone(D.load_scores(bad))

    def test_assumptions_note_says_agreed_only_when_it_is(self):
        text, agreed = D.assumptions_note({"assumptions": {"agreed_with_sir": True, "agreed_date": "2026-10-17",
                                                            "X_secret_years": 5, "Y_migration_years": 2,
                                                            "Z_scenarios": [10, 5, 20]}})
        self.assertTrue(agreed)
        self.assertIn("2026-10-17", text)
        text, agreed = D.assumptions_note({"assumptions": {"agreed_with_sir": False}})
        self.assertFalse(agreed)
        self.assertIn("NOT yet agreed", text)


class DashboardWiringTests(unittest.TestCase):
    """live_dashboard.py runs Streamlit code at import, so it is checked as source text."""

    @classmethod
    def setUpClass(cls):
        cls.src = (D.ROOT / "src" / "live_dashboard.py").read_text(encoding="utf-8-sig")

    def test_page_function_exists(self):
        names = {n.name for n in ast.walk(ast.parse(self.src)) if isinstance(n, ast.FunctionDef)}
        self.assertIn("page_risk", names)

    def test_page_is_in_the_menu_and_the_dispatch(self):
        self.assertIn("Risk score", self.src)
        self.assertIn('"🎯 Risk score": page_risk', self.src)

    def test_page_states_it_is_not_a_probability(self):
        self.assertIn("not a probability", self.src)


if __name__ == "__main__":
    unittest.main()
