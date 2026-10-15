"""Unit tests for find_insecure_rng in src/edge_cases.py."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from edge_cases import find_insecure_rng


def write(folder, name, *lines):
    path = Path(folder) / name
    path.write_text("\n".join(lines) + "\n")
    return path


class TestFindInsecureRng(unittest.TestCase):
    def test_random_choice_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "k.py", "import random", "n = random.choice([3, 5])")
            flags = find_insecure_rng(d)
            self.assertEqual([f["flag"] for f in flags], ["INSECURE_RNG"])
            self.assertEqual(flags[0]["line"], 2)

    def test_aliased_import_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "k.py", "import random as rnd", "x = rnd.getrandbits(64)")
            self.assertEqual(len(find_insecure_rng(d)), 1)

    def test_from_import_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "k.py", "from random import randint", "x = randint(1, 9)")
            self.assertEqual(len(find_insecure_rng(d)), 1)

    def test_sympy_randprime_is_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "k.py", "from sympy import randprime",
                  "p = randprime(2**7, 2**8)")
            flags = find_insecure_rng(d)
            self.assertEqual(len(flags), 1)
            self.assertIn("sympy", flags[0]["detail"])

    def test_secure_sources_are_not_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "k.py", "import random, secrets, os",
                  "a = secrets.randbelow(10)",
                  "b = os.urandom(16)",
                  "c = random.SystemRandom().choice([1, 2])")
            self.assertEqual(find_insecure_rng(d), [])

    def test_numpy_random_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "k.py", "import numpy as np",
                  "rng = np.random.default_rng(1)")
            self.assertEqual(find_insecure_rng(d), [])

    def test_only_provider_files_are_checked(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "crypto.py", "import random", "x = random.randint(1, 5)")
            write(d, "other.py", "import random", "x = random.randint(1, 5)")
            flags = find_insecure_rng(d, provider_files={"crypto.py"})
            self.assertEqual([f["file"] for f in flags], ["crypto.py"])

    def test_syntax_error_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            write(d, "bad.py", "def (:")
            self.assertEqual(find_insecure_rng(d), [])


if __name__ == "__main__":
    unittest.main()
