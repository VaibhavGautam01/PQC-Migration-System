import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import qubit_cost_page_data as q  # type: ignore # noqa: E402


class TestSizeRows(unittest.TestCase):
    def test_formula_is_2n_plus_3_and_matches_the_engine(self):
        for r in q.size_rows():
            self.assertEqual(r["F2 logical qubits (2n+3)"], 2 * r["RSA bits"] + 3)
        by = {r["RSA bits"]: r for r in q.size_rows()}
        self.assertEqual(by[2048]["F2 score (0 to 100)"], 46.2)

    def test_bigger_key_never_has_a_higher_f2_score(self):
        scores = [r["F2 score (0 to 100)"] for r in q.size_rows()]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_published_figure_only_for_2048_and_labelled_as_estimate(self):
        by = {r["RSA bits"]: r for r in q.size_rows()}
        self.assertEqual(by[2048]["Published physical qubits (estimate)"], "20,000,000")
        for b in (512, 1024, 3072):
            self.assertEqual(by[b]["Published physical qubits (estimate)"], "no figure published here")
        for r in q.size_rows():
            self.assertTrue(any("estimate" in k.lower() for k in r if "Gidney" in k))

    def test_gidney_ekera_logical_count_is_not_mixed_with_2n_plus_3(self):
        r = {x["RSA bits"]: x for x in q.size_rows()}[2048]
        self.assertNotEqual(r["Gidney-Ekera abstract circuit, logical (estimate)"], r["F2 logical qubits (2n+3)"])


class TestMeasuredRows(unittest.TestCase):
    def test_five_toy_sizes_from_the_real_file(self):
        rows = q.measured_rows()
        self.assertEqual([r["n (bits)"] for r in rows], [4, 5, 6, 7, 8])
        self.assertEqual([r["N"] for r in rows], [15, 21, 35, 77, 221])

    def test_measured_qubits_equal_the_formula(self):
        self.assertTrue(q.qubits_match_formula())
        for r in q.measured_rows():
            self.assertEqual(r["qubits measured"], 2 * r["n (bits)"] + 3)

    def test_n7_and_n8_full_circuit_is_marked_not_transpiled(self):
        rows = {r["n (bits)"]: r for r in q.measured_rows()}
        self.assertEqual(rows[7]["full circuit: two-qubit gates"], "not transpiled")
        self.assertEqual(rows[8]["iteration checked by simulation"], "-")
        self.assertEqual(rows[4]["iteration checked by simulation"], "yes")

    def test_mismatch_is_reported(self):
        data = json.loads(Path(q.Q4_PATH).read_text(encoding="utf-8"))
        data["rows"][0]["iteration"]["qubits"] += 1
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "q4.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            self.assertFalse(q.qubits_match_formula(p))
            self.assertIn("does not use 2n+3", q.summary_text(p))

    def test_missing_file_gives_empty_and_an_honest_message(self):
        self.assertEqual(q.measured_rows("no_such_file.json"), [])
        self.assertIsNone(q.qubits_match_formula("no_such_file.json"))
        self.assertIn("No Q4 metrics", q.summary_text("no_such_file.json"))


class TestExtrapolation(unittest.TestCase):
    def test_empty_until_a_fit_file_exists(self):
        self.assertEqual(q.extrapolation_rows("no_such_file.json"), [])

    def test_rows_from_a_fit_file_are_labelled_estimate(self):
        fit = {"label": "fit", "rows": [{"bits": 1024, "depth": 10, "two_qubit_gates": 20}]}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "fit.json"
            p.write_text(json.dumps(fit), encoding="utf-8")
            rows = q.extrapolation_rows(p)
        self.assertEqual(rows[0]["RSA bits"], 1024)
        self.assertEqual(rows[0]["kind"], q.LABEL_ESTIMATE)


if __name__ == "__main__":
    unittest.main()
