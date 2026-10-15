"""Tests for the dashboard builder: Summary, Detection and Mapping (Issue #10).

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
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import build_dashboard as bd  # noqa: E402

SAMPLE = os.path.join(HERE, "data", "sample_findings.json")


class TestSections(unittest.TestCase):
    def setUp(self):
        self.ctx = bd.build_context(SAMPLE)

    def test_summary_counts_come_from_the_data(self):
        text = bd.render_summary(self.ctx)
        self.assertIn("**Findings:** 10 across 1 project(s): SAMPLE-DUMMY-DATA", text)
        self.assertIn("Broken by Shor's algorithm", text)
        self.assertIn("quadratic speed-up, not a full break", text)
        self.assertIn("**Unrecognised primitives:** 1", text)

    def test_summary_shor_and_grover_counts_add_up(self):
        mapped = self.ctx["mapped"]
        shor = sum(1 for m in mapped if m["quantum_algorithm"] == "Shor's algorithm")
        grover = sum(1 for m in mapped if m["quantum_algorithm"] == "Grover's algorithm")
        text = bd.render_summary(self.ctx)
        self.assertIn(f"(RSA, ECC, DSA, DH): {shor} finding(s)", text)
        self.assertIn(f"(AES, SHA, legacy ciphers): {grover} finding(s)", text)

    def test_detection_table_has_one_row_per_project(self):
        text = bd.render_detection(self.ctx)
        rows = [ln for ln in text.splitlines() if ln.startswith("| SAMPLE-DUMMY-DATA")]
        self.assertEqual(len(rows), 1)
        self.assertIn("| 10 |", rows[0])
        self.assertIn("(unrecognised)", rows[0])
        self.assertIn("high 8", rows[0])

    def test_detection_states_what_the_scanner_cannot_see(self):
        self.assertIn("pattern-based", bd.render_detection(self.ctx))

    def test_mapping_table_lists_each_primitive_once_with_its_algorithm(self):
        text = bd.render_mapping(self.ctx)
        for prim in ("RSA", "ECC", "DSA", "DH", "AES", "SHA"):
            self.assertEqual(len([ln for ln in text.splitlines() if ln.startswith(f"| {prim} |")]), 1, prim)
        self.assertIn("| (unrecognised) |", text)

    def test_mapping_lists_data_caveats(self):
        text = bd.render_mapping(self.ctx)
        self.assertIn("**Data caveats**", text)
        self.assertIn("prime size", text)

    def test_mapping_says_none_when_there_are_no_caveats(self):
        ctx = dict(self.ctx, caveats=[])
        self.assertIn("- None.", bd.render_mapping(ctx))

    def test_pipe_characters_are_escaped(self):
        self.assertEqual(bd.cb_md("a|b"), "a\\|b")
        self.assertEqual(bd.cb_md(None), "-")


class TestAssembly(unittest.TestCase):
    def setUp(self):
        self.text = bd.build_dashboard(bd.build_context(SAMPLE))

    def test_all_six_headers_in_order(self):
        self.assertEqual(re.findall(r"^## (.+)$", self.text, flags=re.MULTILINE), list(bd.SECTIONS))

    def test_implemented_sections_are_not_placeholders(self):
        body = re.split(r"^## .+$", self.text, flags=re.MULTILINE)[1:4]
        for part in body:
            self.assertNotIn(bd.PENDING, part)

    def test_output_is_deterministic(self):
        self.assertEqual(self.text, bd.build_dashboard(bd.build_context(SAMPLE)))


class TestCli(unittest.TestCase):
    def test_cli_writes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "d.md")
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                code = bd.main([SAMPLE, "--out", out])
            self.assertEqual(code, 0)
            self.assertIn("10 findings", buf.getvalue())
            with open(out, encoding="utf-8") as fh:
                self.assertTrue(fh.read().startswith("# Final Dashboard"))

    def test_cli_usage_errors(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bd.main([]), 2)
            self.assertEqual(bd.main([SAMPLE, "--out"]), 2)

    def test_facts_file_is_used_for_override_status(self):
        facts = os.path.join(HERE, "..", "data", "manual_facts.json")
        if not os.path.exists(facts):
            self.skipTest("data/manual_facts.json not present")
        text = bd.render_detection(bd.build_context(SAMPLE, facts))
        self.assertIn("5 confirmed and applied, 0 unconfirmed (not applied)", text)


if __name__ == "__main__":
    unittest.main()
