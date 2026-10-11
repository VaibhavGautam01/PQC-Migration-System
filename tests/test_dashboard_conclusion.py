"""Tests for the dashboard Conclusion section (Issue #10).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import contextlib
import io
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

import build_dashboard as bd  # noqa: E402

SAMPLE = os.path.join(HERE, "data", "sample_findings.json")
CONCLUSION = os.path.join(ROOT, "docs", "conclusion.md")


class TestConclusionContent(unittest.TestCase):
    def setUp(self):
        with open(CONCLUSION, encoding="utf-8") as fh:
            self.text = fh.read()

    def test_has_impact_limitations_and_future_work(self):
        for heading in ("### Impact", "### Limitations", "### Future work"):
            with self.subTest(heading=heading):
                self.assertIn(heading, self.text)

    def test_limitations_are_honest_about_simulator_and_estimates(self):
        lowered = self.text.lower()
        self.assertIn("simulator at toy sizes", lowered)
        self.assertIn("logical-qubit estimates", lowered)
        self.assertIn("error-correction", lowered)
        self.assertIn("quadratic speed-up, not a break", lowered)

    def test_separates_padding_and_classical_risk_from_quantum(self):
        self.assertIn("deterministic", self.text)
        self.assertIn("separately from the quantum score", self.text)

    def test_contains_no_unfilled_placeholders(self):
        for marker in ("TODO", "TBD", "XXX", "<fill"):
            self.assertNotIn(marker, self.text)


class TestConclusionRendering(unittest.TestCase):
    def test_renders_file_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "c.md")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n### Impact\n\nHello.\n\n")
            ctx = bd.build_context(SAMPLE, None, None, path)
            self.assertEqual(bd.render_conclusion(ctx), "### Impact\n\nHello.")

    def test_missing_file_is_reported_not_crashed(self):
        ctx = bd.build_context(SAMPLE, None, None, "/no/such/conclusion.md")
        self.assertIn("Conclusion file not found", bd.render_conclusion(ctx))

    def test_default_path_is_docs_conclusion(self):
        self.assertEqual(bd.build_context(SAMPLE)["conclusion_path"], os.path.join("docs", "conclusion.md"))

    def test_all_six_sections_are_filled_in_the_full_dashboard(self):
        ctx = bd.build_context(SAMPLE, None, None, CONCLUSION)
        text = bd.build_dashboard(ctx)
        self.assertNotIn(bd.PENDING, text)
        self.assertEqual(re.findall(r"^## (.+)$", text, flags=re.MULTILINE), list(bd.SECTIONS))

    def test_cli_accepts_conclusion_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "d.md")
            with contextlib.redirect_stdout(io.StringIO()):
                code = bd.main([SAMPLE, "--conclusion", CONCLUSION, "--out", out])
            self.assertEqual(code, 0)
            with open(out, encoding="utf-8") as fh:
                self.assertIn("### Future work", fh.read())


if __name__ == "__main__":
    unittest.main()
