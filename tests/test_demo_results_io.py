"""
Tests for demo_results_io.py: the Q1 batch results must merge into data/demo_results.json
without breaking the dashboard (build_dashboard.load_demo). No qiskit needed.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))      # build_dashboard imports its siblings by name

import build_dashboard as bd  # noqa: E402
from src import demo_results_io as D  # noqa: E402


def fake_case(N, a, repeats=3, shots=1000, ok=750, factors="3x5"):
    """A batch case shaped like q1_demo_batch.run_case output (numbers only, no simulator)."""
    return {"N": N, "a": a, "repeats": repeats, "shots_per_repeat": shots,
            "factors_found_in_repeats": {factors: repeats},
            "runs": [{"seed": 12345 + i, "shots_with_factors": ok} for i in range(repeats)]}


def existing_file(tmp):
    """A file in the format the dashboard writes today, with an extra case and a recording."""
    path = Path(tmp) / "demo_results.json"
    path.write_text(json.dumps({
        "_readme": "keep me", "environment": "old env",
        "cases": [{"N": 15, "expected_factors": [3, 5], "runs": 1024, "successes": 509,
                   "backend": "simulator", "notes": "saved from live_dashboard.py"},
                  {"N": 33, "expected_factors": [3, 11], "runs": 100, "successes": 40,
                   "backend": "simulator", "notes": "other"}],
        "recordings": ["demo.mp4"]}), encoding="utf-8")
    return path


class MergeKeepsTheDashboardFormat(unittest.TestCase):
    def test_merged_file_passes_the_dashboard_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = existing_file(tmp)
            D.merge_into_demo_results(path, [fake_case(15, 7), fake_case(21, 2, factors="3x7")],
                                      12345, "Qiskit X")
            doc = bd.load_demo(str(path))              # raises ValueError if runs/successes are bad
            self.assertEqual([c["N"] for c in doc["cases"]], [15, 21, 33])

    def test_existing_keys_other_cases_and_recordings_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = existing_file(tmp)
            doc = D.merge_into_demo_results(path, [fake_case(21, 2, factors="3x7")], 12345, "Qiskit X")
            self.assertEqual(doc["_readme"], "keep me")
            self.assertEqual(doc["recordings"], ["demo.mp4"])
            case33 = next(c for c in doc["cases"] if c["N"] == 33)
            self.assertEqual((case33["runs"], case33["successes"]), (100, 40))

    def test_a_case_with_the_same_n_is_replaced_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = existing_file(tmp)
            doc = D.merge_into_demo_results(path, [fake_case(15, 7)], 12345, "Qiskit X")
            rows = [c for c in doc["cases"] if c["N"] == 15]
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]["runs"], rows[0]["successes"]), (3000, 2250))

    def test_runs_and_successes_are_whole_numbers(self):
        entry = D.build_entry(fake_case(35, 2, ok=741, factors="5x7"), 12345, "Qiskit X")
        self.assertIsInstance(entry["runs"], int)
        self.assertIsInstance(entry["successes"], int)
        self.assertLessEqual(entry["successes"], entry["runs"])
        self.assertEqual(entry["expected_factors"], [5, 7])
        self.assertIn("Aer simulator, toy size", entry["notes"])

    def test_one_row_per_n_when_two_bases_are_run(self):
        picked = D.pick_dashboard_cases([fake_case(15, 7), fake_case(15, 2), fake_case(21, 2)])
        self.assertEqual([(c["N"], c["a"]) for c in picked], [(15, 7), (21, 2)])

    def test_creates_a_valid_file_when_none_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "new" / "demo_results.json"
            D.merge_into_demo_results(path, [fake_case(15, 7)], 12345, "Qiskit X")
            self.assertEqual(bd.load_demo(str(path))["cases"][0]["N"], 15)

    def test_a_file_in_the_old_wrong_format_is_what_the_loader_rejects(self):
        # regression test: "runs" as a LIST (the format that broke the dashboard) must be rejected
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "demo_results.json"
            path.write_text(json.dumps({"cases": [{"N": 15, "runs": [{"seed": 1}], "successes": 1}]}),
                            encoding="utf-8")
            with self.assertRaises(ValueError):
                bd.load_demo(str(path))


if __name__ == "__main__":
    unittest.main()
