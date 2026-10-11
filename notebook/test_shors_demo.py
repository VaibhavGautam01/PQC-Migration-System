"""
test_shors_demo.py
------------------
Reliability tests for the Shor's N=15 demo (Issue #9).
Run with:  python -m unittest test_shors_demo -v
"""

import unittest

from shors_demo import (
    factors_from_bitstring,
    factors_from_period,
    run_shor_attempts,
)

ATTEMPTS_PER_RUN = 100
NUMBER_OF_RUNS = 5


class TestFactorsFromPeriod(unittest.TestCase):
    def test_period_4_gives_3_and_5(self):
        self.assertEqual(factors_from_period(4), (3, 5))

    def test_odd_period_rejected(self):
        self.assertIsNone(factors_from_period(1))
        self.assertIsNone(factors_from_period(3))

    def test_wrong_period_rejected(self):
        # r = 2 is a wrong guess: 7^2 mod 15 = 4, not 1
        self.assertIsNone(factors_from_period(2))

    def test_nonpositive_period_rejected(self):
        self.assertIsNone(factors_from_period(0))
        self.assertIsNone(factors_from_period(-4))


class TestFactorsFromBitstring(unittest.TestCase):
    def test_lucky_outcomes_give_3_and_5(self):
        self.assertEqual(factors_from_bitstring("0100"), (3, 5))   # phase 1/4
        self.assertEqual(factors_from_bitstring("1100"), (3, 5))   # phase 3/4

    def test_unlucky_outcomes_give_none(self):
        self.assertIsNone(factors_from_bitstring("0000"))          # phase 0
        self.assertIsNone(factors_from_bitstring("1000"))          # phase 1/2


class TestReliabilityAcrossRuns(unittest.TestCase):
    """Run the whole circuit several times; each run has many attempts."""

    @classmethod
    def setUpClass(cls):
        cls.runs = [run_shor_attempts(ATTEMPTS_PER_RUN) for _ in range(NUMBER_OF_RUNS)]

    def test_every_success_is_exactly_3_and_5(self):
        for i, attempts in enumerate(self.runs):
            for bitstring in attempts:
                result = factors_from_bitstring(bitstring)
                with self.subTest(run=i, outcome=bitstring):
                    self.assertIn(result, (None, (3, 5)))

    def test_every_run_finds_the_factors(self):
        for i, attempts in enumerate(self.runs):
            successes = [b for b in attempts if factors_from_bitstring(b) == (3, 5)]
            with self.subTest(run=i):
                self.assertGreater(len(successes), 0)

    def test_success_rate_is_near_one_half(self):
        # Ideal expectation is 50%. The 25%-75% window is about 5 standard
        # deviations wide, so a correct circuit essentially never fails it.
        for i, attempts in enumerate(self.runs):
            rate = sum(factors_from_bitstring(b) == (3, 5) for b in attempts) / len(attempts)
            with self.subTest(run=i, rate=rate):
                self.assertTrue(0.25 <= rate <= 0.75)

    def test_only_expected_phases_appear(self):
        for attempts in self.runs:
            self.assertTrue({int(b, 2) for b in attempts} <= {0, 4, 8, 12})


if __name__ == "__main__":
    unittest.main()