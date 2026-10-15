"""RSA-MANUAL-MODULUS matches the real assignment n = p * q, not prose."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import scanner  # noqa: E402


def scan_lines(*lines):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "keys.py"
        path.write_text("\n".join(lines) + "\n")
        return [f for f in scanner.scan_path(d) if f["pattern_id"] == "RSA-MANUAL-MODULUS"]


class TestModulusPattern(unittest.TestCase):
    def test_assignment_is_detected(self):
        hits = scan_lines("def gen(p, q):", "    n = p * q", "    return n")
        self.assertEqual([h["line"] for h in hits], [2])

    def test_assignment_with_trailing_comment_is_detected(self):
        self.assertEqual(len(scan_lines("n = p * q  # modulus")), 1)

    def test_docstring_prose_is_not_detected(self):
        self.assertEqual(scan_lines('"""', "2. n = p * q", '"""'), [])

    def test_prose_mentioning_it_is_not_detected(self):
        self.assertEqual(scan_lines("# a pair with n = p*q in range"), [])

    def test_unrelated_product_is_not_detected(self):
        self.assertEqual(scan_lines("n = width * height"), [])


if __name__ == "__main__":
    unittest.main()
