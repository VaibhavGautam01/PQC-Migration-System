import copy
import json
import tempfile
import unittest
from pathlib import Path

from src import assumptions as A


def good():
    return {
        "secret_years": {"value": 5, "scenarios": [2, 5, 10]},
        "migration_years": {"value": 2, "scenarios": [2]},
        "quantum_years": {"value": 10, "scenarios": [5, 10, 20]},
        "exposure": "public", "attacker": "stego file and public key",
        "agreed_with_sir": False, "agreed_date": None, "project_overrides": {},
    }


class AssumptionTests(unittest.TestCase):
    def test_real_file_loads_with_working_values(self):
        a = A.load_assumptions()
        self.assertEqual(
            (a["secret_years"]["value"], a["migration_years"]["value"], a["quantum_years"]["value"]),
            (5, 2, 10))
        self.assertEqual(a["exposure"], "public")
        self.assertEqual(A.z_scenarios(a), [10, 5, 20])

    def test_agreement_state_is_consistent(self):
        a = A.load_assumptions()
        if a["agreed_with_sir"]:
            self.assertIsNotNone(a["agreed_date"])

    def test_deadline_is_six_weeks_and_dated(self):
        d = A.load_deadline()
        self.assertEqual(d["weeks"], 6)
        self.assertEqual(d["agreed_date"], "2026-10-22")

    def test_deadline_must_be_a_positive_whole_number_with_a_date(self):
        for bad in ({"weeks": 0, "agreed_date": "2026-10-22"},
                    {"weeks": 6.5, "agreed_date": "2026-10-22"},
                    {"weeks": 6, "agreed_date": "soon"}):
            g = good(); g["deadline"] = bad
            with self.assertRaises(A.AssumptionError):
                A.validate(g)

    def test_analyzer_flow_and_scope_confirmation_are_recorded_with_dates(self):
        from datetime import date
        an = A.load_analyzer()
        self.assertEqual(an["flow_agreed_date"], "2026-10-22")
        date.fromisoformat(an["flow_agreed_date"])
        # the scope may be unconfirmed (false) or confirmed (true with a date); never confirmed without a date
        self.assertIsInstance(an["scope_confirmed_with_sir"], bool)
        if an["scope_confirmed_with_sir"]:
            date.fromisoformat(an["scope_confirmed_date"])

    def test_analyzer_scope_confirmed_needs_a_date(self):
        g = good()
        g["analyzer"] = {"flow": "f", "flow_agreed_date": "2026-10-22", "scope": "s",
                         "scope_confirmed_with_sir": True}
        with self.assertRaises(A.AssumptionError):
            A.validate(g)
        g["analyzer"]["scope_confirmed_date"] = "2026-10-25"
        A.validate(g)

    def test_good_block_is_valid(self):
        self.assertEqual(A.validate(good()), good())

    def test_central_value_must_be_a_scenario(self):
        g = good(); g["quantum_years"]["value"] = 7
        with self.assertRaises(A.AssumptionError):
            A.validate(g)

    def test_negative_or_bool_values_rejected(self):
        for bad in (-1, 0, True, "5"):
            g = good(); g["secret_years"]["value"] = bad; g["secret_years"]["scenarios"] = [bad]
            with self.assertRaises(A.AssumptionError):
                A.validate(g)

    def test_agreed_needs_a_date(self):
        g = good(); g["agreed_with_sir"] = True
        with self.assertRaises(A.AssumptionError):
            A.validate(g)
        g["agreed_date"] = "2026-10-20"
        A.validate(g)

    def test_date_without_agreement_rejected(self):
        g = good(); g["agreed_date"] = "2026-10-20"
        with self.assertRaises(A.AssumptionError):
            A.validate(g)

    def test_bad_exposure_rejected(self):
        g = good(); g["exposure"] = "secret"
        with self.assertRaises(A.AssumptionError):
            A.validate(g)

    def test_project_override_applies_only_to_that_project(self):
        g = good(); g["project_overrides"] = {"video": {"secret_years": {"value": 10, "scenarios": [10]}}}
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "facts.json"
            p.write_text(json.dumps({"assumptions": g}))
            self.assertEqual(A.load_assumptions("video", p)["secret_years"]["value"], 10)
            self.assertEqual(A.load_assumptions("image", p)["secret_years"]["value"], 5)

    def test_unknown_project_rejected(self):
        with self.assertRaises(A.AssumptionError):
            A.load_assumptions("audio")

    def test_missing_block_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "facts.json"
            p.write_text("{}")
            with self.assertRaises(A.AssumptionError):
                A.load_assumptions(path=p)


if __name__ == "__main__":
    unittest.main()
