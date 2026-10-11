"""Tests for the Markdown rendering of the CBOM (Issue #8).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import contextlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import cbom  # noqa: E402
import quantum_mapper as qm  # noqa: E402

SAMPLE = os.path.join(HERE, "data", "sample_findings.json")


class TestRenderMarkdown(unittest.TestCase):
    def setUp(self):
        self.mapped = qm.map_findings(qm.load_findings(SAMPLE))
        self.doc = cbom.build_cbom(self.mapped, None)
        self.text = cbom.render_markdown(self.doc)
        self.rows = [ln for ln in self.text.splitlines() if ln.startswith("| CBOM-")]

    def test_has_title_and_counts(self):
        self.assertTrue(self.text.startswith("# Cryptographic Bill of Materials (CBOM)"))
        self.assertIn(f"Entries: {self.doc['entry_count']}", self.text)

    def test_one_table_row_per_entry(self):
        self.assertEqual(len(self.rows), self.doc["entry_count"])
        for entry in self.doc["entries"]:
            self.assertTrue(any(row.startswith(f"| {entry['id']} |") for row in self.rows))

    def test_every_row_has_the_same_number_of_columns(self):
        header_cols = [ln for ln in self.text.splitlines() if ln.startswith("| ID |")][0].count("|")
        for row in self.rows:
            self.assertEqual(row.count("|"), header_cols)

    def test_states_that_padding_is_separate_from_quantum_risk(self):
        self.assertIn("deterministic", self.text)
        self.assertIn("not because of Shor's algorithm", self.text)

    def test_evidence_section_lists_every_entry(self):
        for entry in self.doc["entries"]:
            self.assertIn(f"- {entry['id']}: ", self.text)

    def test_open_data_questions_lists_unverified_entries(self):
        self.assertIn("## Open data questions", self.text)
        unverified = [e for e in self.doc["entries"] if e["size_status"] == "unverified"]
        self.assertTrue(unverified)
        self.assertIn(unverified[0]["id"], self.text.split("## Open data questions")[1])

    def test_unmapped_section_lists_blowfish(self):
        self.assertIn("## Unmapped findings", self.text)
        self.assertIn("ROT13", self.text)

    def test_notes_and_references_are_included(self):
        self.assertIn("## Notes", self.text)
        self.assertIn("## References", self.text)
        self.assertIn("Beauregard", self.text)
        self.assertIn("Gidney", self.text)

    def test_output_is_deterministic_and_ends_with_newline(self):
        self.assertEqual(self.text, cbom.render_markdown(self.doc))
        self.assertTrue(self.text.endswith("\n"))


class TestMarkdownEdgeCases(unittest.TestCase):
    def test_pipes_in_values_are_escaped(self):
        self.assertEqual(cbom._md("a|b"), "a\\|b")
        self.assertEqual(cbom._md(None), "-")
        self.assertEqual(cbom._md(""), "-")
        self.assertEqual(cbom._md(0), "0")

    def test_no_open_questions_section_when_all_sizes_are_known(self):
        mapped = qm.map_findings([{"project": "P", "file": "a.py", "line": 1,
                                   "primitive": "RSA", "modulus_bits": 2048}])
        text = cbom.render_markdown(cbom.build_cbom(mapped, None))
        self.assertNotIn("## Open data questions", text)
        self.assertNotIn("## Unmapped findings", text)

    def test_rsa_row_shows_the_qubit_estimate(self):
        mapped = qm.map_findings([{"project": "P", "file": "a.py", "line": 1,
                                   "primitive": "RSA", "modulus_bits": 1024}])
        text = cbom.render_markdown(cbom.build_cbom(mapped, None))
        self.assertIn("| 2051 |", text)


class TestCliMarkdown(unittest.TestCase):
    def test_cli_writes_matching_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            js, md = os.path.join(tmp, "c.json"), os.path.join(tmp, "c.md")
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                code = cbom.main([SAMPLE, "--json", js, "--md", md])
            self.assertEqual(code, 0)
            self.assertIn("Markdown written", buf.getvalue())
            doc, _ = cbom.build_cbom_from_files(SAMPLE)
            with open(md, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), cbom.render_markdown(doc))

    def test_write_cbom_markdown(self):
        doc, _ = cbom.build_cbom_from_files(SAMPLE)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "c.md")
            cbom.write_cbom_markdown(doc, path)
            with open(path, encoding="utf-8") as fh:
                self.assertIn("# Cryptographic Bill of Materials", fh.read())


if __name__ == "__main__":
    unittest.main()
