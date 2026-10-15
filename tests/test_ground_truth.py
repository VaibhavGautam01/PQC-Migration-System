"""Scanner accuracy on the two target repos (see src/validate_ground_truth.py)."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from validate_ground_truth import evaluate  # noqa: E402

P = "proj"


def truth(*lines):
    return {"core": [{"project": P, "file": "a.py", "line": n, "what": "x"} for n in lines],
            "borderline": [{"project": P, "file": "a.py", "line": 99, "what": "ctl"}]}


def finding(n):
    return {"project": P, "file": "a.py", "line": n}


class TestEvaluate(unittest.TestCase):
    def test_perfect_run(self):
        r = evaluate([finding(1), finding(2)], truth(1, 2))
        self.assertEqual((r["precision"], r["recall_findings"]), (1.0, 1.0))

    def test_extra_finding_lowers_precision(self):
        r = evaluate([finding(1), finding(5)], truth(1))
        self.assertEqual(r["precision"], 0.5)
        self.assertEqual(r["extra"], [(P, "a.py", 5)])

    def test_missed_line_lowers_recall(self):
        r = evaluate([finding(1)], truth(1, 2))
        self.assertEqual(r["recall_findings"], 0.5)
        self.assertEqual(r["missed"][0][0], (P, "a.py", 2))

    def test_rng_flag_counts_for_recall_with_flags_only(self):
        report = {"findings": [finding(1)],
                  "edge_cases": {P: {"insecure_rng": [{"file": "a.py", "line": 2}]}}}
        r = evaluate(report, truth(1, 2))
        self.assertEqual(r["recall_findings"], 0.5)
        self.assertEqual(r["recall_with_flags"], 1.0)

    def test_borderline_finding_is_not_an_error(self):
        r = evaluate([finding(1), finding(99)], truth(1))
        self.assertEqual(r["extra"], [])
        self.assertEqual(r["borderline_hit"], [(P, "a.py", 99)])


class TestRealRepos(unittest.TestCase):
    """Fails if a scanner change loses a labelled line or adds an unlabelled one."""

    def setUp(self):
        report = json.loads((ROOT / "outputs" / "findings.json").read_text(encoding="utf-8"))
        gt = json.loads((ROOT / "data" / "ground_truth.json").read_text(encoding="utf-8"))
        self.result = evaluate(report, gt)

    def test_no_unlabelled_findings(self):
        self.assertEqual(self.result["extra"], [])
        self.assertEqual(self.result["precision"], 1.0)

    def test_every_labelled_line_is_covered_by_a_finding_or_flag(self):
        self.assertEqual(self.result["missed_after_flags"], [])


if __name__ == "__main__":
    unittest.main()
