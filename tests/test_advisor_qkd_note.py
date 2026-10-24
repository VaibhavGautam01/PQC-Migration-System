import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import pqc_advisor


class TestQkdNote(unittest.TestCase):
    def test_l1_has_qkd_note_with_honest_label(self):
        note = pqc_advisor.advise("L1")["qkd_note"]
        self.assertIn("Aer simulator, toy size", note)
        self.assertIn("ML-KEM stays the software-only recommendation", note)

    def test_note_is_optional_for_other_layers(self):
        self.assertNotIn("qkd_note", pqc_advisor.advise("L3"))


if __name__ == "__main__":
    unittest.main()