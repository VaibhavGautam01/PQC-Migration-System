import ast
import json
import tempfile
import unittest
from pathlib import Path

from src import advisor_page_data as A

FIELDS = {"layer": "L1", "layer_name": "Message encryption", "today": "RSA",
          "technique": "ML-KEM-768 + HKDF + AES-256-GCM", "parameter_set": "ML-KEM-768",
          "standard": "FIPS 203", "quantum_status": "classical, quantum-resistant",
          "sizes_bytes": {"public_key": 1184, "ciphertext": 1088}, "rationale": "r",
          "trade_offs": "t", "where_to_use": "w"}


def write(d, records):
    p = Path(d) / "rec.json"
    p.write_text(json.dumps({"version": "0.1", "records": records}), encoding="utf-8")
    return p


class AdvisorPageDataTests(unittest.TestCase):
    def test_valid_file_loads_in_order(self):
        with tempfile.TemporaryDirectory() as d:
            second = dict(FIELDS, layer="L3", layer_name="Integrity", sizes_bytes={})
            recs = A.load_records(write(d, [FIELDS, second]))
            self.assertEqual([r["layer"] for r in recs], ["L1", "L3"])

    def test_missing_broken_or_incomplete_file_gives_none(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(A.load_records(Path(d) / "nope.json"))
            bad = Path(d) / "bad.json"
            bad.write_text("{oops")
            self.assertIsNone(A.load_records(bad))
            incomplete = {k: v for k, v in FIELDS.items() if k != "rationale"}
            self.assertIsNone(A.load_records(write(d, [incomplete])))
            self.assertIsNone(A.load_records(write(d, [])))

    def test_sizes_text_and_total(self):
        self.assertEqual(A.sizes_text(FIELDS), "public_key: 1,184 B, ciphertext: 1,088 B")
        self.assertEqual(A.total_bytes(FIELDS), 2272)
        none = dict(FIELDS, sizes_bytes={})
        self.assertEqual(A.sizes_text(none), "n/a")
        self.assertEqual(A.total_bytes(none), 0)

    def test_status_colours(self):
        self.assertEqual(A.status_color(FIELDS), "#00E676")
        self.assertEqual(A.status_color(dict(FIELDS, quantum_status="symmetric; Grover halves")), "#00B0FF")
        self.assertEqual(A.status_color(dict(FIELDS, quantum_status="not part of it")), "#90A4AE")

    def test_overview_and_chart_rows(self):
        none = dict(FIELDS, layer="HIDING", sizes_bytes={})
        rows = A.overview_rows([FIELDS, none])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Parameter set"], "ML-KEM-768")
        chart = A.size_chart_rows([FIELDS, none])
        self.assertEqual([c["bytes"] for c in chart], [2272])

    @unittest.skipUnless(A.RECOMMENDATIONS_PATH.is_file(), "data/pqc_recommendations.json not in this checkout yet")
    def test_real_file_covers_the_layers_and_matches_fips_sizes(self):
        recs = {r["layer"]: r for r in A.load_records()}
        for layer in ("L1", "L2", "L3", "L5"):
            self.assertIn(layer, recs)
        self.assertEqual(recs["L1"]["sizes_bytes"], {"public_key": 1184, "ciphertext": 1088})  # FIPS 203
        self.assertEqual(recs["L5"]["sizes_bytes"], {"public_key": 1952, "signature": 3309})   # FIPS 204


class DashboardWiringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = (A.ROOT / "src" / "live_dashboard.py").read_text(encoding="utf-8-sig")

    def test_page_function_exists(self):
        names = {n.name for n in ast.walk(ast.parse(self.src)) if isinstance(n, ast.FunctionDef)}
        self.assertIn("page_advisor", names)

    def test_page_is_in_the_menu_and_the_dispatch(self):
        self.assertIn('"🧭 PQC advisor", "📈 Qubit calculator"', self.src)
        self.assertIn('"🧭 PQC advisor": page_advisor', self.src)

    def test_page_says_pqc_is_classical_and_not_production(self):
        self.assertIn("not quantum circuits", self.src)
        self.assertIn("not production crypto", self.src)


if __name__ == "__main__":
    unittest.main()
