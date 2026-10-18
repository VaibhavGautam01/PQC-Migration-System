import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import physical_estimates as pe  # type: ignore # noqa: E402


class TestPublished(unittest.TestCase):
    def test_rsa_2048_figure(self):
        e = pe.published_estimate(2048)
        self.assertEqual(e["physical_qubits"], 20_000_000)
        self.assertEqual(e["runtime_hours"], 8)
        self.assertIn("ESTIMATE", e["kind"])
        self.assertIn("Gidney", e["citation"])

    def test_assumptions_are_carried_with_the_number(self):
        a = pe.published_estimate(2048)["assumptions"]
        self.assertEqual(a["physical_gate_error_rate"], 0.001)

    def test_no_figure_for_other_sizes(self):
        for bits in (512, 1024, 3072):
            self.assertIsNone(pe.published_estimate(bits))

    def test_unverified_flag_is_visible(self):
        self.assertFalse(pe.published_estimate(2048)["verified_against_paper"])

    def test_invalid(self):
        for bad in (0, -1, 1.5, "2048", True):
            with self.assertRaises(ValueError):
                pe.published_estimate(bad)


class TestFormulas(unittest.TestCase):
    def test_logical_formula(self):
        self.assertAlmostEqual(pe.gidney_ekera_logical(2048), 3 * 2048 + 0.002 * 2048 * 11)

    def test_illustrative_is_labelled_and_exact(self):
        r = pe.illustrative_physical(2051)
        self.assertEqual(r["physical_qubits"], 2_051_000)
        self.assertIn("ILLUSTRATIVE", r["kind"])

    def test_comparison_row_keeps_formulas_separate(self):
        row = pe.comparison_row(2048)
        self.assertEqual(row["logical_2n_plus_3"], 4099)
        self.assertNotEqual(row["logical_2n_plus_3"], row["gidney_ekera_logical_abstract"])
        self.assertIsNotNone(row["published"])
        self.assertIsNone(pe.comparison_row(1024)["published"])


class TestCustomFile(unittest.TestCase):
    def test_reads_other_file(self):
        data = json.loads(pe.DATA.read_text(encoding="utf-8"))
        data["sources"]["gidney_ekera_2021"]["estimates"].append(
            {"rsa_bits": 1024, "physical_qubits": 1, "runtime_hours": 1})
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(pe.published_estimate(1024, p)["physical_qubits"], 1)


if __name__ == "__main__":
    unittest.main()