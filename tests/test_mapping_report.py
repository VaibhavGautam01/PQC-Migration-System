"""Tests for the draft mapping report and the sample findings fixture (Issue #6).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import quantum_mapper as qm  # noqa: E402

SAMPLE = os.path.join(HERE, "data", "sample_findings.json")


class TestSampleFindings(unittest.TestCase):
    def setUp(self):
        self.mapped = qm.map_findings(qm.load_findings(SAMPLE))

    def test_sample_covers_every_primitive_family(self):
        found = {m["canonical_primitive"] for m in self.mapped}
        self.assertTrue({"RSA", "ECC", "DSA", "DH", "AES", "SHA"} <= found)

    def test_exactly_one_unknown_primitive(self):
        self.assertEqual(sum(1 for m in self.mapped if m["canonical_primitive"] is None), 1)

    def test_size_warning_only_for_rsa_with_prime_size(self):
        warned = [m for m in self.mapped if m["size_warning"]]
        self.assertEqual(len(warned), 1)
        self.assertEqual(warned[0]["canonical_primitive"], "RSA")

    def test_ecc_key_size_does_not_trigger_prime_size_warning(self):
        r = qm.map_finding({"primitive": "ECDSA", "key_size": 256})
        self.assertIsNone(r["size_warning"])


class TestDraftReport(unittest.TestCase):
    def _report(self, draft):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.md")
            qm.generate_mapping_report(qm.map_findings(qm.load_findings(SAMPLE)), path, draft=draft)
            with open(path, encoding="utf-8") as fh:
                return fh.read()

    def test_draft_report_has_banner(self):
        self.assertIn("DRAFT", self._report(draft=True))

    def test_final_report_has_no_banner(self):
        self.assertNotIn("DRAFT", self._report(draft=False))

    def test_report_lists_all_primitive_types(self):
        text = self._report(draft=True)
        for label in ("RSA", "ECC", "DSA", "DH", "AES", "SHA"):
            self.assertIn(f"| {label} |", text)


if __name__ == "__main__":
    unittest.main()
