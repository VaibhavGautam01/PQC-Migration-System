import ast
import unittest
from pathlib import Path

from src import quantum_lab_page_data as D

ROOT = Path(__file__).resolve().parent.parent


class QuantumLabPageDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runs = D.load_runs()

    def test_committed_runs_load(self):
        self.assertGreaterEqual(len(self.runs), 1)

    def test_evidence_rows_one_per_run_and_labelled(self):
        rows = D.evidence_rows(self.runs)
        self.assertEqual(len(rows), len(self.runs))
        for r in rows:
            self.assertTrue(r["label"])
            self.assertIn("Aer", r["backend"])

    def test_histogram_sums_to_at_most_shots(self):
        run = self.runs[0]
        rows = D.histogram_rows(run, top=100)
        self.assertEqual(sum(r["count"] for r in rows), sum(run["counts"].values()))
        self.assertEqual(rows, sorted(rows, key=lambda r: -r["count"]))

    def test_diagram_text_reads_saved_file(self):
        text, total, path = D.diagram_text(self.runs[0])
        self.assertIsNotNone(text)
        self.assertGreater(total, 0)
        self.assertTrue(path.endswith(".txt"))

    def test_missing_diagram_is_not_an_error(self):
        text, total, _ = D.diagram_text({"diagram_file": "docs/circuits/nope.txt"})
        self.assertIsNone(text)
        self.assertEqual(total, 0)

    def test_progress_lists_every_must_item(self):
        rows = D.progress_rows(self.runs)
        self.assertEqual([r["item"] for r in rows], ["Q1", "Q2", "Q3"])
        self.assertEqual(rows[0]["status"], "has evidence")

    def test_progress_is_honest_when_there_are_no_runs(self):
        self.assertTrue(all(r["status"] == "no evidence yet" for r in D.progress_rows([])))

    def test_verification_rows_follow_gate_and_guard(self):
        n, errors, warnings = D.gate_summary()
        rows = D.verification_rows(self.runs, errors, warnings, D.guard_problems())
        by = {r["check"]: r["result"] for r in rows}
        self.assertEqual(by["Static guard (rule 8)"], "PASS")
        self.assertEqual(by["Evidence gate (rule 4)"], "PASS")
        bad = D.verification_rows(self.runs, ["x"], [], ["y"])
        self.assertEqual({r["result"] for r in bad[:2]}, {"FAIL"})

    def test_cross_check_is_partial_when_some_runs_have_none(self):
        with_check = dict(self.runs[0], cross_check={"agree": True})
        without = {k: v for k, v in self.runs[0].items() if k != "cross_check"}
        rows = D.verification_rows([with_check, without], [], [], [])
        by = {r["check"]: r["result"] for r in rows}
        self.assertEqual(by["Second simulation method (rule 9)"], "PARTIAL")
        rows = D.verification_rows([with_check, with_check], [], [], [])
        by = {r["check"]: r["result"] for r in rows}
        self.assertEqual(by["Second simulation method (rule 9)"], "PASS")

    def test_question_groups_pass(self):
        for r in D.question_rows(self.runs):
            self.assertTrue(r["passes"], r)


class DashboardWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (ROOT / "src" / "live_dashboard.py").read_text(encoding="utf-8-sig")

    def test_page_function_exists_and_is_registered(self):
        names = {n.name for n in ast.walk(ast.parse(self.src)) if isinstance(n, ast.FunctionDef)}
        self.assertIn("page_quantum_lab", names)
        self.assertIn('"\U0001f52c Quantum Lab": page_quantum_lab', self.src)

    def test_page_carries_the_simulator_label(self):
        self.assertIn("Aer simulator, toy size", self.src)


if __name__ == "__main__":
    unittest.main()
