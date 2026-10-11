"""test_scanner.py - unit tests for src/scanner.py (Week 2, Day 3).

Why these tests exist: the scanner is regex based, so a small edit to one
pattern can silently stop detection (or start over-matching). These tests pin
the behaviour we validated by hand against both target repos.

Run from the project root:
    python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))   # so "import scanner" works from tests/
import scanner  # noqa: E402

FIXTURES = os.path.join(ROOT, "tests", "fixtures")


def scan_code(code, name="x.py"):
    """Write `code` to a temp file, scan it, return the list of finding dicts."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        return scanner.scan_file(path, tmp)


def ids(code):
    """Just the pattern ids found in `code` (as a set)."""
    return {f["pattern_id"] for f in scan_code(code)}


class TestRealRepoPatterns(unittest.TestCase):
    """One line per pattern, copied from the two target repos' real code."""

    CASES = [
        # (source line, expected pattern id, where the real line lives)
        ("c = pow(m, e, n)", "RSA-MODEXP", "Secure-Video rsa_crypto.py:142 (encrypt)"),
        ("m = pow(c, d, n)", "RSA-MODEXP", "Secure-Video rsa_crypto.py:170 (decrypt)"),
        ("return pow(m, e, n)", "RSA-MODEXP", "part1 rsa_utils.py:45 (encrypt_int)"),
        ("return pow(c, d, n)", "RSA-MODEXP", "part1 rsa_utils.py:50 (decrypt_int)"),
        ("d = pow(e, -1, phi)", "RSA-MANUAL-MODINV", "part1 r_channel_stego.py:59"),
        ("phi = (p - 1) * (q - 1)", "RSA-MANUAL-PHI", "part1 rsa_utils.py:33"),
        ("d = number.inverse(e, phi)", "RSA-MANUAL-INVFUNC", "Secure-Video rsa_crypto.py:56"),
        ("e = 65537", "RSA-PUBLIC-EXP", "Secure-Video rsa_crypto.py:45"),
        ("p = getPrime(512)", "RSA-MANUAL-PRIME", "Secure-Video rsa_crypto.py:48"),
        ("pub, priv = generate_keypair(bits=128)", "RSA-WRAPPER-CALL", "part1 keypair wrapper call"),
        ("primes = [p for p in range(2, 40) if isprime(p)]", "RSA-MANUAL-PRIME-ISPRIME",
         "part1 r_channel_stego.py:42 (Week 2 fix)"),
        ("h = hashlib.sha256(data).hexdigest()", "HASH-SHA2-HASHLIB", "Secure-Video frame_selector.py:32"),
    ]

    def test_each_real_line_is_detected(self):
        for code, expected, origin in self.CASES:
            with self.subTest(origin=origin):
                self.assertIn(expected, ids(code))

    def test_modular_inverse_is_not_reported_as_plain_modexp(self):
        # pow(e, -1, phi) is a modular INVERSE; RSA-MODEXP must skip it
        # (negative look-ahead in the regex), otherwise it is double counted.
        found = ids("d = pow(e, -1, phi)")
        self.assertIn("RSA-MANUAL-MODINV", found)
        self.assertNotIn("RSA-MODEXP", found)


class TestNoFalsePositives(unittest.TestCase):
    """Lines that only look crypto-ish must NOT produce a finding."""

    def test_definitions_are_skipped(self):
        # (?<!def ) in the regex: only real CALLS count, not the definition line
        self.assertEqual(scan_code("def generate_keypair(bits):"), [])
        self.assertEqual(scan_code("def isprime(n):"), [])

    def test_bare_imports_are_not_flagged(self):
        self.assertEqual(scan_code("from sympy import isprime"), [])
        self.assertEqual(scan_code("import hashlib"), [])

    def test_ordinary_code_is_clean(self):
        self.assertEqual(scan_code("x = 1 + 2\nprint(x)\n"), [])

    def test_empty_file_gives_no_findings(self):
        self.assertEqual(scan_code(""), [])


class TestKeySizeExtraction(unittest.TestCase):
    """key_size is per-prime for hand-rolled RSA; modulus_bits is 2x that."""

    def one(self, code):
        findings = scan_code(code)
        self.assertEqual(len(findings), 1, findings)
        return findings[0]

    def test_literal_size_in_call(self):
        f = self.one("p = getPrime(512)")
        self.assertEqual((f["key_size"], f["modulus_bits"]), (512, 1024))

    def test_keyword_argument_size(self):
        # generate_keypair(bits=N) builds two N-bit primes (documented assumption)
        f = self.one("pub, priv = generate_keypair(bits=128)")
        self.assertEqual((f["key_size"], f["modulus_bits"]), (128, 256))

    def test_size_resolved_through_variables(self):
        # getPrime(half) -> half = key_size // 2 -> key_size = 1024
        f = self.one("key_size = 1024\nhalf = key_size // 2\np = getPrime(half)\n")
        self.assertEqual((f["key_size"], f["modulus_bits"]), (512, 1024))

    def test_non_keygen_patterns_have_no_size(self):
        f = self.one("c = pow(m, e, n)")
        self.assertIsNone(f["key_size"])
        self.assertIsNone(f["modulus_bits"])


class TestFindingShape(unittest.TestCase):
    """Every finding must carry the fields later stages (mapper, dashboard) read."""

    REQUIRED = {"file", "line", "primitive", "pattern_id", "description",
                "confidence", "key_size", "modulus_bits", "size_basis", "snippet"}

    def test_required_fields_and_line_numbers(self):
        findings = scan_code("import os\n\nc = pow(m, e, n)\n")
        self.assertEqual(len(findings), 1)
        self.assertTrue(self.REQUIRED <= set(findings[0]))
        self.assertEqual(findings[0]["line"], 3)           # 1-based line number
        self.assertEqual(findings[0]["snippet"], "c = pow(m, e, n)")
        self.assertEqual(findings[0]["file"], "x.py")      # path relative to scan root


class TestScanPath(unittest.TestCase):
    def test_skips_ignored_folders_and_non_source_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "venv"))
            for rel in ("a.py", os.path.join("venv", "b.py"), "notes.txt"):
                with open(os.path.join(tmp, rel), "w", encoding="utf-8") as fh:
                    fh.write("c = pow(m, e, n)\n")
            files = {f["file"] for f in scanner.scan_path(tmp)}
        self.assertEqual(files, {"a.py"})   # venv/ is in SKIP_DIRS, .txt is not scanned

    def test_single_file_path_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "only.py")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("c = pow(m, e, n)\n")
            self.assertEqual(len(scanner.scan_path(path)), 1)

    def test_oversized_file_is_skipped(self):
        with mock.patch.object(scanner, "MAX_FILE_BYTES", 5):
            self.assertEqual(scan_code("c = pow(m, e, n)\n"), [])


class TestBuildReport(unittest.TestCase):
    def test_summary_numbers_add_up(self):
        findings = scan_code("c = pow(m, e, n)\np = getPrime(512)\nh = hashlib.sha256(x)\n")
        report = scanner.build_report(".", findings)
        s = report["summary"]
        self.assertEqual(s["total_findings"], len(findings))
        self.assertEqual(sum(s["by_pattern"].values()), len(findings))
        self.assertEqual(sum(s["by_primitive"].values()), len(findings))
        self.assertEqual(s["by_primitive"], {"RSA": 2, "SHA": 1})
        self.assertEqual(report["scanner_version"], scanner.SCANNER_VERSION)


class TestPatternTable(unittest.TestCase):
    """Data-quality checks on the pattern list itself."""

    def test_pattern_ids_are_unique(self):
        pattern_ids = [p["id"] for p in scanner.ALL_PATTERNS]
        self.assertEqual(len(pattern_ids), len(set(pattern_ids)))

    def test_every_pattern_is_well_formed(self):
        for p in scanner.ALL_PATTERNS:
            with self.subTest(pattern=p["id"]):
                self.assertIn(p["primitive"], {"RSA", "ECC", "DSA", "DH", "AES", "SHA"})
                self.assertIn(p["confidence"], {"high", "medium", "low"})
                self.assertTrue(p["desc"])


class TestFixturesRegression(unittest.TestCase):
    """Golden numbers for tests/fixtures (the same totals the scanner prints)."""

    def test_fixture_totals_do_not_change_silently(self):
        findings = scanner.scan_path(FIXTURES)
        summary = scanner.build_report(FIXTURES, findings)["summary"]
        self.assertEqual(summary["total_findings"], 46)
        self.assertEqual(summary["files_with_findings"], 4)
        self.assertEqual(summary["by_primitive"],
                         {"AES": 8, "DH": 1, "DSA": 1, "ECC": 5, "RSA": 27, "SHA": 4})


if __name__ == "__main__":
    unittest.main()
