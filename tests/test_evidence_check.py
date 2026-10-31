"""Tests for extras/evidence_check_weeks1to4.py."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_script():
    spec = importlib.util.spec_from_file_location(
        "evidence_check", str(ROOT / "extras/evidence_check_weeks1to4.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EvidenceCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_script()

    def test_backed_values_reads_n_p_and_period_from_runs(self):
        runs = [{"inputs": {"N": 15, "a": 7}, "result": {"period": 4}},
               {"inputs": {"p": 23, "g": 5}, "result": {"order_r": 22}}]
        backed = self.m.backed_values(runs)
        self.assertEqual(backed["N"], [15])
        self.assertEqual(backed["p"], [23])
        self.assertEqual(backed["period"], [4, 22])

    def test_claimed_values_reads_prose_not_code_blocks(self):
        text = "We ran N=15 and N=21.\n```\npython -m src.q1_run --N 999\n```\nAlso N=35."
        claimed = self.m.claimed_values(text)
        self.assertEqual(claimed["N"], [15, 21, 35])   # 999 inside the code block is excluded

    def test_check_doc_finds_an_orphaned_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text("Ran N=15 and N=999. qiskit 2.5.2, commit abc.")
            backed = {"N": [15], "p": [], "period": []}
            r = self.m.check_doc(doc, backed)
            self.assertEqual(r["orphaned_claims"], {"N": [999]})

    def test_check_doc_reports_no_orphans_when_everything_is_backed(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text("Ran N=15 only. qiskit 2.5.2, commit abc.")
            backed = {"N": [15], "p": [], "period": []}
            r = self.m.check_doc(doc, backed)
            self.assertEqual(r["orphaned_claims"], {})

    def test_check_doc_flags_remaining_fill_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = Path(tmp) / "doc.md"
            doc.write_text("Result: **[FILL]**")
            r = self.m.check_doc(doc, {"N": [], "p": [], "period": []})
            self.assertTrue(r["has_fill_markers_remaining"])

    def test_load_runs_handles_missing_file(self):
        self.assertEqual(self.m.load_runs(Path("/nonexistent/file.json")), [])

    def test_load_runs_handles_dict_and_list_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            p1 = Path(tmp) / "a.json"
            p1.write_text(json.dumps({"runs": [{"inputs": {}}]}))
            self.assertEqual(len(self.m.load_runs(p1)), 1)
            p2 = Path(tmp) / "b.json"
            p2.write_text(json.dumps([{"inputs": {}}, {"inputs": {}}]))
            self.assertEqual(len(self.m.load_runs(p2)), 2)


if __name__ == "__main__":
    unittest.main()
