"""Tests that the CBOM JSON, Markdown and source findings agree (Issue #8).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import cbom  # noqa: E402

SAMPLE = os.path.join(HERE, "data", "sample_findings.json")


class TestCheckConsistency(unittest.TestCase):
    def setUp(self):
        self.doc, self.mapped = cbom.build_cbom_from_files(SAMPLE)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.js = os.path.join(self.tmp.name, "c.json")
        self.md = os.path.join(self.tmp.name, "c.md")
        cbom.write_cbom_json(self.doc, self.js)
        cbom.write_cbom_markdown(self.doc, self.md)

    def test_untouched_outputs_are_consistent(self):
        self.assertEqual(cbom.check_consistency(self.doc, self.mapped, self.js, self.md), [])

    def test_consistent_without_files(self):
        self.assertEqual(cbom.check_consistency(self.doc, self.mapped), [])

    def test_detects_dropped_entry(self):
        bad = copy.deepcopy(self.doc)
        bad["entries"].pop()
        bad["entry_count"] -= 1
        problems = cbom.check_consistency(bad, self.mapped)
        self.assertTrue(any("source groups" in p for p in problems))

    def test_detects_wrong_finding_count(self):
        bad = copy.deepcopy(self.doc)
        bad["finding_count"] = 99
        self.assertTrue(any("finding_count" in p for p in cbom.check_consistency(bad, self.mapped)))

    def test_detects_wrong_quantum_algorithm(self):
        bad = copy.deepcopy(self.doc)
        bad["entries"][0]["quantum_risk"]["algorithm"] = "Grover's algorithm"
        self.assertTrue(any("quantum algorithm differs" in p for p in cbom.check_consistency(bad, self.mapped)))

    def test_detects_changed_file_references(self):
        bad = copy.deepcopy(self.doc)
        bad["entries"][0]["files"] = ["somewhere/else.py:1"]
        self.assertTrue(any("file references differ" in p for p in cbom.check_consistency(bad, self.mapped)))

    def test_detects_entry_with_no_source_findings(self):
        bad = copy.deepcopy(self.doc)
        bad["entries"][0]["key_size_bits"] = 7
        self.assertTrue(any("no source findings" in p for p in cbom.check_consistency(bad, self.mapped)))

    def test_detects_json_file_tampering(self):
        with open(self.js, encoding="utf-8") as fh:
            data = json.load(fh)
        data["entries"][0]["key_size_bits"] = 4096
        with open(self.js, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        self.assertTrue(any("does not match the CBOM" in p
                            for p in cbom.check_consistency(self.doc, self.mapped, self.js, None)))

    def test_detects_markdown_out_of_sync(self):
        with open(self.md, "a", encoding="utf-8") as fh:
            fh.write("\nextra line\n")
        self.assertTrue(any("does not match the CBOM" in p
                            for p in cbom.check_consistency(self.doc, self.mapped, None, self.md)))

    def test_schema_problems_are_included(self):
        bad = copy.deepcopy(self.doc)
        bad["entries"][0]["primitive"] = "Blowfish"
        self.assertTrue(cbom.check_consistency(bad, self.mapped))


class TestCliCheck(unittest.TestCase):
    def run_cli(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cbom.main(list(args))
        return code, buf.getvalue()

    def test_check_passes_on_fresh_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            js, md = os.path.join(tmp, "c.json"), os.path.join(tmp, "c.md")
            code, text = self.run_cli(SAMPLE, "--json", js, "--md", md, "--check")
        self.assertEqual(code, 0)
        self.assertIn("CONSISTENCY: OK", text)

    def test_check_without_output_files_still_runs(self):
        code, text = self.run_cli(SAMPLE, "--check")
        self.assertEqual(code, 0)
        self.assertIn("CONSISTENCY: OK", text)

    def test_usage_error_for_unknown_value_flag_without_value(self):
        code, _ = self.run_cli(SAMPLE, "--md")
        self.assertEqual(code, 2)


class TestDeterminism(unittest.TestCase):
    def test_two_runs_give_byte_identical_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            outs = []
            for run in ("a", "b"):
                js, md = os.path.join(tmp, run + ".json"), os.path.join(tmp, run + ".md")
                with contextlib.redirect_stdout(io.StringIO()):
                    cbom.main([SAMPLE, "--json", js, "--md", md])
                with open(js, "rb") as f1, open(md, "rb") as f2:
                    outs.append((f1.read(), f2.read()))
        self.assertEqual(outs[0], outs[1])


if __name__ == "__main__":
    unittest.main()
