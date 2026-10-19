"""
Tests for the gate-level Shor circuit (Q2).
Fast: structure, post-processing, forbidden-helper scan.
Slow (runs the circuit): set SLOW_TESTS=1 (PowerShell: $env:SLOW_TESTS="1")
"""
import os
import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from q2_shor import build_shor_ipea, shor_layout  # type: ignore # noqa: E402
from q2_shor_run import factors_from_measurement, run_shor  # type: ignore # noqa: E402

SLOW = os.environ.get("SLOW_TESTS") == "1"
FORBIDDEN = ("sympy", "factorint", "n_order", "multiplicative_order", "isprime", "primefactors")


class TestLayoutAndStructure(unittest.TestCase):
    def test_qubit_count_is_2n_plus_3(self):
        for N in (15, 21, 35):
            n = N.bit_length()
            self.assertEqual(shor_layout(N)["qubits"], 2 * n + 3)
            self.assertEqual(build_shor_ipea(2, N).num_qubits, 2 * n + 3)

    def test_one_classical_bit_per_phase_bit(self):
        self.assertEqual(build_shor_ipea(7, 15).num_clbits, 8)       # default m = 2n
        self.assertEqual(build_shor_ipea(7, 15, m=3).num_clbits, 3)

    def test_registers_do_not_overlap(self):
        lay = shor_layout(21)
        used = lay["x"] + lay["b"] + [lay["anc"], lay["c"]]
        self.assertEqual(sorted(used), list(range(lay["qubits"])))

    def test_circuit_uses_midcircuit_measurement_and_reset(self):
        ops = build_shor_ipea(7, 15, m=3).count_ops()
        self.assertEqual(ops.get("measure"), 3)
        self.assertEqual(ops.get("reset"), 2)
        self.assertGreaterEqual(ops.get("if_else", ops.get("if", 0)), 1)

    def test_bad_inputs(self):
        for a, N in ((5, 15), (3, 15), (2, 16), (2, 1)):
            with self.subTest(a=a, N=N):
                with self.assertRaises(ValueError):
                    build_shor_ipea(a, N)


class TestChangeTheQuestionBuilds(unittest.TestCase):
    """Same code, different N and a: only the inputs change."""
    def test_builds_for_several_inputs(self):
        for a, N in ((7, 15), (2, 15), (2, 21), (4, 21), (2, 35), (3, 35)):
            with self.subTest(a=a, N=N):
                self.assertEqual(build_shor_ipea(a, N, m=2).num_qubits, 2 * N.bit_length() + 3)


class TestPostProcessing(unittest.TestCase):
    def test_n15_lucky_outcomes(self):
        self.assertEqual(factors_from_measurement(64, 8, 7, 15), (3, 5))     # phase 1/4
        self.assertEqual(factors_from_measurement(192, 8, 7, 15), (3, 5))    # phase 3/4

    def test_n15_phase_one_half_recovered_by_multiple(self):
        self.assertEqual(factors_from_measurement(128, 8, 7, 15), (3, 5))    # r = 2 is wrong, 4 works

    def test_zero_gives_nothing(self):
        self.assertIsNone(factors_from_measurement(0, 8, 7, 15))

    def test_n21_phases(self):
        self.assertEqual(factors_from_measurement(171, 10, 2, 21), (3, 7))   # about 1/6
        self.assertEqual(factors_from_measurement(853, 10, 2, 21), (3, 7))   # about 5/6

    def test_never_returns_a_wrong_factorisation(self):
        for N, a, m in ((15, 7, 8), (21, 2, 10), (35, 2, 12)):
            for y in range(0, 2 ** m, max(1, 2 ** m // 257)):
                f = factors_from_measurement(y, m, a, N)
                if f:
                    self.assertEqual(f[0] * f[1], N)
                    self.assertTrue(1 < f[0] <= f[1] < N)


class TestForbiddenHelpers(unittest.TestCase):
    """Rule 8, simple version: the builders must not use factoring or order-finding helpers."""
    def test_builders_do_not_mention_forbidden_names(self):
        for name in ("q2_arith.py", "q2_shor.py"):
            text = (SRC / name).read_text(encoding="utf-8")
            for word in FORBIDDEN:
                self.assertNotIn(word, text, f"{name} mentions {word}")


@unittest.skipUnless(SLOW, "set SLOW_TESTS=1 to run the circuit")
class TestRunsOnSimulator(unittest.TestCase):
    def test_n15_gives_only_multiples_of_64_and_finds_factors(self):
        rec, _ = run_shor(7, 15, shots=20)
        ys = {int(b, 2) for b in rec["counts"]}
        self.assertTrue(ys <= {0, 64, 128, 192}, ys)
        self.assertEqual(set(rec["factors_found"]) - {"3x5"}, set())
        self.assertGreater(rec["success_rate"], 0)
        self.assertEqual(rec["label"], "Aer simulator, toy size")
        self.assertEqual(rec["qubits"], 11)

    def test_change_the_question_n21(self):
        rec, _ = run_shor(2, 21, shots=10)
        self.assertEqual(set(rec["factors_found"]) - {"3x7"}, set())
        self.assertGreater(rec["success_rate"], 0)


if __name__ == "__main__":
    unittest.main()