"""Slow quantum test (Aer simulator, toy size). Run with:
python -m unittest discover -s tests -p "slow_test*.py" -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import qrng, randtests


class TestQrng(unittest.TestCase):
    def test_seeded_output_passes_basic_tests(self):
        bits = qrng.generate_bits(65536, seed=7)
        self.assertEqual(len(bits), 65536)
        self.assertGreater(randtests.monobit_p(bits), 1e-4)
        self.assertGreater(randtests.runs_p(bits), 1e-4)
        self.assertGreater(randtests.byte_chi2(bits)[1], 1e-4)

    def test_same_seed_reproduces_and_other_seed_differs(self):
        self.assertEqual(qrng.generate_bits(2048, seed=3), qrng.generate_bits(2048, seed=3))
        self.assertNotEqual(qrng.generate_bits(2048, seed=3), qrng.generate_bits(2048, seed=4))


if __name__ == "__main__":
    unittest.main()