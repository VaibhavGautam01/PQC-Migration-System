import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import randtests


class TestRandTests(unittest.TestCase):
    def test_all_zeros_fail_monobit(self):
        self.assertLess(randtests.monobit_p([0] * 10000), 1e-6)

    def test_balanced_sequence_passes_monobit(self):
        self.assertAlmostEqual(randtests.monobit_p([0, 1] * 5000), 1.0)

    def test_alternating_bits_fail_runs(self):
        self.assertLess(randtests.runs_p([0, 1] * 5000), 1e-6)

    def test_constant_bytes_fail_chi_square(self):
        bits = randtests.bits_from_bytes(bytes([65]) * 4000)
        self.assertLess(randtests.byte_chi2(bits)[1], 1e-6)

    def test_chi_square_needs_enough_data(self):
        with self.assertRaises(ValueError):
            randtests.byte_chi2([0, 1] * 100)

    def test_bits_from_bytes(self):
        self.assertEqual(randtests.bits_from_bytes(b"\x81"), [1, 0, 0, 0, 0, 0, 0, 1])


if __name__ == "__main__":
    unittest.main()