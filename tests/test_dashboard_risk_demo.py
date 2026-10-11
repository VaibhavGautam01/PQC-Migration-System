"""Tests for the dashboard Risk and Demo sections (Issue #10).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import build_dashboard as bd  # noqa: E402

SAMPLE = os.path.join(HERE, "data", "sample_findings.json")


def demo_file(tmp, data):
    path = os.path.join(tmp, "demo.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


GOOD_DEMO = {"environment": "test simulator",
             "cases": [{"N": 15, "expected_factors": [3, 5], "runs": 10, "successes": 9,
                        "backend": "sim", "notes": "n|1"},
                       {"N": 21, "expected_factors": [3, 7], "runs": 4, "successes": 4, "backend": "sim"}],
             "recordings": ["docs/demo_backup.md"]}


class TestRisk(unittest.TestCase):
    def setUp(self):
        self.ctx = bd.build_context(SAMPLE)
        self.text = bd.render_risk(self.ctx)

    def test_one_row_per_cbom_entry(self):
        rows = [ln for ln in self.text.splitlines() if ln.startswith("| CBOM-")]
        self.assertEqual(len(rows), self.ctx["cbom"]["entry_count"])

    def test_rsa_row_shows_logical_qubits_from_2n_plus_3(self):
        self.assertIn("| 2051 |", self.text)

    def test_states_padding_is_separate_and_qubits_are_logical(self):
        self.assertIn("not because of Shor's algorithm", self.text)
        self.assertIn("logical-qubit estimates", self.text)

    def test_summary_now_includes_cbom_lines(self):
        text = bd.render_summary(self.ctx)
        self.assertIn("**CBOM entries:** 9", text)
        self.assertIn("unverified key size", text)


class TestDemo(unittest.TestCase):
    def test_missing_file_gives_an_honest_placeholder(self):
        ctx = bd.build_context(SAMPLE, None, "/no/such/file.json")
        text = bd.render_demo(ctx)
        self.assertIn("No demo results provided yet", text)
        self.assertNotIn("%", text)

    def test_empty_cases_gives_placeholder(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = bd.build_context(SAMPLE, None, demo_file(tmp, {"cases": []}))
        self.assertIn("No demo results provided yet", bd.render_demo(ctx))

    def test_cases_render_with_computed_success_rate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = bd.build_context(SAMPLE, None, demo_file(tmp, GOOD_DEMO))
        text = bd.render_demo(ctx)
        self.assertIn("**Environment:** test simulator", text)
        self.assertIn("| 15 | 3 x 5 | 10 | 9 | 90% |", text)
        self.assertIn("| 21 | 3 x 7 | 4 | 4 | 100% |", text)
        self.assertIn("n\\|1", text)
        self.assertIn("docs/demo_backup.md", text)

    def test_toy_size_disclaimer_is_always_present_with_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            ctx = bd.build_context(SAMPLE, None, demo_file(tmp, GOOD_DEMO))
        self.assertIn("not evidence that RSA-1024 or RSA-2048 can be broken today", bd.render_demo(ctx))

    def test_bad_counts_are_rejected(self):
        bad_cases = [
            {"N": 15, "runs": 0, "successes": 0},
            {"N": 15, "runs": 5, "successes": 6},
            {"N": 15, "runs": 5, "successes": -1},
            {"N": 15, "runs": None, "successes": None},
            {"N": 15, "runs": "5", "successes": 5},
        ]
        for case in bad_cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as tmp:
                    with self.assertRaises(ValueError):
                        bd.load_demo(demo_file(tmp, {"cases": [case]}))

    def test_cases_must_be_a_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                bd.load_demo(demo_file(tmp, {"cases": "nope"}))

    def test_template_file_has_no_numbers_filled_in(self):
        path = os.path.join(HERE, "..", "data", "demo_results.template.json")
        if not os.path.exists(path):
            self.skipTest("template not present")
        with open(path, encoding="utf-8") as fh:
            template = json.load(fh)
        for case in template["cases"]:
            self.assertIsNone(case["runs"])
            self.assertIsNone(case["successes"])


class TestAssemblyAndCli(unittest.TestCase):
    def test_risk_and_demo_sections_are_no_longer_placeholders(self):
        text = bd.build_dashboard(bd.build_context(SAMPLE))
        sections = re.split(r"^## .+$", text, flags=re.MULTILINE)[1:]
        names = list(bd.SECTIONS)
        for name in ("Summary", "Detection", "Mapping", "Risk", "Demo"):
            with self.subTest(section=name):
                self.assertNotIn(bd.PENDING, sections[names.index(name)])

    def test_cli_accepts_demo_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "d.md")
            demo = demo_file(tmp, GOOD_DEMO)
            with contextlib.redirect_stdout(io.StringIO()):
                code = bd.main([SAMPLE, "--demo", demo, "--out", out])
            self.assertEqual(code, 0)
            with open(out, encoding="utf-8") as fh:
                self.assertIn("90%", fh.read())


if __name__ == "__main__":
    unittest.main()
