import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_sizes


class TestSizes(unittest.TestCase):
    def test_documented_sizes_match_code(self):
        for name, doc, code, ok in check_sizes.check():
            with self.subTest(item=name):
                self.assertTrue(ok, f"{name}: documented {doc}, code {code}")


if __name__ == "__main__":
    unittest.main()