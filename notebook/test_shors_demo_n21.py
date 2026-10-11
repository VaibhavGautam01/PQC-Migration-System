"""
test_shors_demo_n21.py
----------------------
Reliability tests for the Shor's N=21 demo (Issue #9).
Run with:  python -m unittest test_shors_demo_n21 -v
"""

import unittest

from shors_demo import (
    A21,
    N21,
    N_COUNT21,
    factors_from_bitstring,
    factors_from_period,
    run_shor_attempts_n21,
)

ATTEMPTS_PER_RUN = 200
NUMBER_OF_RUNS = 5


def decode(bitstring):
    """Measured bitstring -> factors of 21 (or None)."""
    return factors_from_bitstring(bitstring, A21, N21, N_COUNT21)


class TestN21PostProcessing(unittest.TestCase):
    def test_period_6_gives_3_and_7(self):
        self.assertEqual(factors_from_period(6, A21, N21), (3, 7))

    def test_true_period_is_6(self):
        self.assertEqual(pow(A21, 6, N21), 1)
        for r in (1, 2, 3, 4, 5):
            self.assertNotEqual(pow(A21, r, N21), 1)

    def test_wrong_or_odd_periods_rejected(self):
        for r in (0, 1, 2, 3, 4, 5):
            with self.subTest(r=r):
                self.assertIsNone(factors_from_period(r, A21, N21))

    def test_lucky_peaks_give_3_and_7(self):
        self.assertEqual(decode("00101011"), (3, 7))   # 43  -> phase ~1/6
        self.assertEqual(decode("11010101"), (3, 7))   # 213 -> phase ~5/6

    def test_unlucky_peaks_give_none(self):
        self.assertIsNone(decode("00000000"))          # 0   -> phase 0
        self.assertIsNone(decode("01010101"))          # 85  -> phase ~1/3
        self.assertIsNone(decode("10000000"))          # 128 -> phase 1/2
        self.assertIsNone(decode("10101011"))          # 171 -> phase ~2/3


class TestN21ReliabilityAcrossRuns(unittest.TestCase):
    """Run the whole circuit several times; each run has many attempts."""

    @classmethod
    def setUpClass(cls):
        cls.runs = [run_shor_attempts_n21(ATTEMPTS_PER_RUN) for _ in range(NUMBER_OF_RUNS)]

    def test_every_success_is_exactly_3_and_7(self):
        for i, attempts in enumerate(self.runs):
            for bitstring in attempts:
                with self.subTest(run=i, outcome=bitstring):
                    self.assertIn(decode(bitstring), (None, (3, 7)))

    def test_every_run_finds_the_factors(self):
        for i, attempts in enumerate(self.runs):
            successes = [b for b in attempts if decode(b) == (3, 7)]
            with self.subTest(run=i):
                self.assertGreater(len(successes), 0)

    def test_success_rate_is_in_expected_range(self):
        for i, attempts in enumerate(self.runs):
            rate = sum(decode(b) == (3, 7) for b in attempts) / len(attempts)
            with self.subTest(run=i, rate=rate):
                self.assertTrue(0.15 <= rate <= 0.45)

    def test_all_attempts_are_valid_bitstrings(self):
        for attempts in self.runs:
            self.assertEqual(len(attempts), ATTEMPTS_PER_RUN)
            for b in attempts:
                self.assertEqual(len(b), N_COUNT21)


if __name__ == "__main__":
    unittest.main()