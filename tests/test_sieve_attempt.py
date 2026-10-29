"""Tests for extras/sieve_attempt.py. Fast, no external dependencies."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_script():
    spec = importlib.util.spec_from_file_location("sieve_attempt", str(ROOT / "extras/sieve_attempt.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SieveAttemptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_script()

    def test_pollards_rho_factors_a_small_semiprime(self):
        import time
        f = self.m.pollards_rho(91, time.perf_counter() + 5)
        self.assertIn(f, (7, 13))

    def test_pollards_p_minus_1_factors_a_smooth_semiprime(self):
        import time
        # 3233 = 61 x 53; 60 = 2^2*3*5, 52=2^2*13, both small/smooth
        f = self.m.pollards_p_minus_1(3233, time.perf_counter() + 5)
        self.assertIn(f, (61, 53))

    def test_attempt_reports_completed_true_with_correct_factors(self):
        result = self.m.attempt(3233, budget_seconds=5)
        self.assertTrue(result["completed"])
        p, q = result["factors"]
        self.assertEqual(p * q, 3233)

    def test_pollards_rho_respects_an_already_expired_deadline(self):
        # deterministic regardless of CPU speed: the deadline is already in the past, so no
        # work can happen at all - must return None immediately, never guess a factor
        import time
        f = self.m.pollards_rho(3233, deadline=time.perf_counter() - 1)
        self.assertIsNone(f)

    def test_pollards_p_minus_1_respects_an_already_expired_deadline(self):
        import time
        f = self.m.pollards_p_minus_1(3233, deadline=time.perf_counter() - 1)
        self.assertIsNone(f)

    def test_attempt_honestly_reports_not_completed_with_an_expired_budget(self):
        # budget_seconds=0 means the deadline is effectively "now": whatever attempt() picks
        # as N, it must not report completed=True with a guessed factor
        result = self.m.attempt(3233, budget_seconds=0)
        self.assertFalse(result["completed"])
        self.assertIsNone(result["factors"])

    def test_load_modulus_from_project_is_explicit_about_being_unimplemented(self):
        with self.assertRaises(NotImplementedError):
            self.m.load_modulus_from_project("some/path")

    def test_self_test_function_passes(self):
        self.assertEqual(self.m.self_test(), 0)


if __name__ == "__main__":
    unittest.main()
