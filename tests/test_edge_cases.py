"""Unit tests for src/edge_cases.py (run: python tests\\test_edge_cases.py)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from edge_cases import check_padding, find_crypto_imports, find_indirect_usage


def write(folder, name, text):
    path = Path(folder) / name
    path.write_text(text)
    return path


class TestCheckPadding(unittest.TestCase):
    def test_raw_pow_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "a.py", "def enc(m, e, n):\n    return pow(m, e, n)\n")
            flag = check_padding(f, 2)
            self.assertIsNotNone(flag)
            self.assertEqual(flag["flag"], "NO_PADDING")

    def test_oaep_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            f = write(d, "b.py",
                      "cipher = PKCS1_OAEP.new(key)\nct = cipher.encrypt(data)\n")
            self.assertIsNone(check_padding(f, 2))


class TestCryptoImports(unittest.TestCase):
    def test_real_import_is_found(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "c.py", "import hashlib\n")
            self.assertEqual(len(find_crypto_imports(d)), 1)

    def test_rsa_utils_is_not_a_false_positive(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "d.py", "import rsa_utils\n")
            self.assertEqual(find_crypto_imports(d), {})


class TestIndirectUsage(unittest.TestCase):
    def test_importing_a_crypto_module_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "provider.py", "def enc(m, e, n):\n    return pow(m, e, n)\n")
            write(d, "user.py", "from provider import enc\n")
            files = [f["file"] for f in find_indirect_usage(d)]
            self.assertIn("user.py", files)
            self.assertNotIn("provider.py", files)

    def test_no_crypto_means_no_flags(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "plain.py", "x = 1\n")
            write(d, "other.py", "import plain\n")
            self.assertEqual(find_indirect_usage(d), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)