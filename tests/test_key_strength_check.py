"""Unit tests for src/key_strength_check.py (run: python tests\\test_key_strength_check.py)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from key_strength_check import (check_finding, check_findings, classify,
                                render_markdown)


class TestClassify(unittest.TestCase):
    def test_512_is_critical(self):
        self.assertEqual(classify(512)[0], "CRITICAL")

    def test_just_above_512_is_high(self):
        self.assertEqual(classify(513)[0], "HIGH")

    def test_just_below_1024_is_high(self):
        self.assertEqual(classify(1023)[0], "HIGH")

    def test_1024_is_medium(self):
        self.assertEqual(classify(1024)[0], "MEDIUM")

    def test_just_below_2048_is_medium(self):
        self.assertEqual(classify(2047)[0], "MEDIUM")

    def test_2048_is_ok(self):
        self.assertEqual(classify(2048)[0], "OK")

    def test_small_toy_key_is_critical(self):
        self.assertEqual(classify(31)[0], "CRITICAL")

    def test_missing_size_is_unknown(self):
        self.assertEqual(classify(None)[0], "UNKNOWN_SIZE")


class TestCheckFinding(unittest.TestCase):
    def test_aes_is_ignored(self):
        self.assertIsNone(check_finding({"primitive": "AES", "key_size": 128}))

    def test_rsa_with_size_is_rated(self):
        flag = check_finding({"primitive": "RSA", "modulus_bits": 512})
        self.assertEqual(flag["level"], "CRITICAL")

    def test_dsa_and_dh_are_checked_too(self):
        self.assertEqual(check_finding({"primitive": "DSA", "modulus_bits": 1024})["level"], "MEDIUM")
        self.assertEqual(check_finding({"primitive": "DH", "modulus_bits": 2048})["level"], "OK")

    def test_prime_size_warning_when_modulus_missing(self):
        flag = check_finding({"primitive": "RSA", "key_size": 16})
        self.assertEqual(flag["level"], "UNKNOWN_SIZE")
        self.assertIn("prime size", flag["note"])


class TestCheckFindings(unittest.TestCase):
    def test_only_asymmetric_findings_are_returned(self):
        flags = check_findings([
            {"primitive": "RSA", "modulus_bits": 512},
            {"primitive": "AES", "key_size": 256},
            {"primitive": "SHA", "key_size": 256},
        ])
        self.assertEqual(len(flags), 1)


class TestRenderMarkdown(unittest.TestCase):
    def setUp(self):
        self.md = render_markdown(check_findings([
            {"project": "P", "file": "a.py", "line": 3,
             "primitive": "RSA", "modulus_bits": 512},
            {"project": "P", "file": "b.py", "line": 7,
             "primitive": "RSA", "key_size": 16},
        ]))

    def test_has_heading_and_rated_row(self):
        self.assertIn("## Classical key strength", self.md)
        self.assertIn("a.py:3", self.md)
        self.assertIn("CRITICAL", self.md)

    def test_unrated_finding_is_counted_not_listed(self):
        self.assertIn("1 further", self.md)
        self.assertNotIn("b.py:7", self.md)


class TestDefaultBasis(unittest.TestCase):
    def test_default_flag_is_carried(self):
        flag = check_finding({"primitive": "RSA", "modulus_bits": 512, "is_default": True})
        self.assertTrue(flag["is_default"])

    def test_rows_are_labelled_by_basis(self):
        md = render_markdown(check_findings([
            {"project": "P", "file": "a.py", "line": 1, "primitive": "RSA",
             "modulus_bits": 512, "is_default": True},
            {"project": "P", "file": "b.py", "line": 2, "primitive": "RSA",
             "modulus_bits": 256},
        ]))
        self.assertIn("| default only |", md)
        self.assertIn("| in use |", md)


if __name__ == "__main__":
    unittest.main(verbosity=2)