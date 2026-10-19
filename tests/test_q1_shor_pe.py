"""
Tests for Q1 (Shor phase estimation).

Three groups:
  1. FAST, no qiskit needed : post-processing, theory, chi-square, static guard.
  2. FAST, needs qiskit     : the matrix and the inverse-QFT gate list (skipped if qiskit missing).
  3. SLOW, needs qiskit     : runs the circuit on Aer. Enable with
       PowerShell:  $env:RUN_SLOW="1"; python -m unittest tests.test_q1_shor_pe -v
Run everything fast:  python -m unittest discover -s tests
"""
import cmath
import importlib.util
import math
import os
import unittest

from src import quantum_guard as G
from src import shor_post as SP

HAS_QISKIT = importlib.util.find_spec("qiskit") is not None and \
    importlib.util.find_spec("qiskit_aer") is not None
SLOW = os.environ.get("RUN_SLOW") == "1" or os.environ.get("SLOW_TESTS") == "1"


class PostProcessingTests(unittest.TestCase):
    def test_inputs_are_checked(self):
        SP.check_inputs(7, 15)
        for a, N in [(5, 15), (1, 15), (15, 15), (3, 2)]:
            with self.assertRaises(ValueError):
                SP.check_inputs(a, N)

    def test_decode_known_outcomes_n15_a7(self):
        m = 8                                    # phase = y/256, true period 4
        self.assertIsNone(SP.decode_outcome(0, m, 7, 15))
        self.assertEqual(SP.decode_outcome(64, m, 7, 15), 4)    # 1/4
        self.assertEqual(SP.decode_outcome(192, m, 7, 15), 4)   # 3/4
        self.assertEqual(SP.decode_outcome(128, m, 7, 15), 4)   # 1/2 -> r0=2 -> multiple 4

    def test_factors_from_period(self):
        self.assertEqual(SP.factors_from_period(7, 15, 4), (3, 5))
        self.assertIsNone(SP.factors_from_period(7, 15, 3))     # odd period
        self.assertIsNone(SP.factors_from_period(14, 15, 2))    # a**(r/2) = -1 mod N

    def test_analyse_counts_uses_only_the_counts(self):
        counts = {format(64, "08b"): 40, format(192, "08b"): 35,
                  format(128, "08b"): 20, format(0, "08b"): 5}
        out = SP.analyse_counts(counts, 8, 7, 15)
        self.assertEqual(out["period"], 4)
        self.assertEqual(out["factors"], [3, 5])
        self.assertAlmostEqual(out["success_rate"], 0.95)

    def test_change_the_question_changes_the_answer(self):
        # same functions, different (N, a): different period and factors (rule 6)
        a15 = SP.analyse_counts({format(64, "08b"): 100}, 8, 7, 15)
        self.assertEqual(a15["factors"], [3, 5])
        a21 = SP.analyse_counts({format(683, "012b"): 100}, 12, 2, 21)   # 683/4096 ~ 1/6
        self.assertEqual(a21["period"], 6)
        self.assertEqual(a21["factors"], [3, 7])


class TheoryAndChiSquareTests(unittest.TestCase):
    def test_distribution_sums_to_one(self):
        for N, a, m in [(15, 7, 8), (21, 2, 12), (35, 2, 12)]:
            self.assertAlmostEqual(sum(SP.theoretical_distribution(a, N, m)), 1.0, places=9)

    def test_n15_a7_peaks_at_multiples_of_quarter(self):
        probs = SP.theoretical_distribution(7, 15, 8)           # r = 4, M = 256
        for y in (0, 64, 128, 192):
            self.assertAlmostEqual(probs[y], 0.25, places=9)
        self.assertAlmostEqual(probs[1], 0.0, places=9)

    def test_order_for_theory(self):
        self.assertEqual(SP.true_order_for_theory(7, 15), 4)
        self.assertEqual(SP.true_order_for_theory(2, 21), 6)
        self.assertEqual(SP.true_order_for_theory(2, 35), 12)

    def test_chi2_p_value_known_points(self):
        self.assertAlmostEqual(SP.chi2_sf(3.841458820694124, 1), 0.05, places=6)
        self.assertAlmostEqual(SP.chi2_sf(18.307038053275146, 10), 0.05, places=6)
        self.assertAlmostEqual(SP.chi2_sf(0.0, 5), 1.0, places=9)

    def test_perfect_sample_matches_and_wrong_theory_is_rejected(self):
        probs = SP.theoretical_distribution(7, 15, 8)
        shots = 4000
        ideal = {format(y, "08b"): round(shots * p) for y, p in enumerate(probs) if p > 1e-9}
        good = SP.chi_square_vs_theory(ideal, probs)
        self.assertGreater(good["p_value"], 0.99)
        wrong = {format(y, "08b"): shots // 256 for y in range(256)}   # uniform: wrong circuit
        bad = SP.chi_square_vs_theory(wrong, probs)
        self.assertLess(bad["p_value"], 1e-6)


class StaticGuardTests(unittest.TestCase):
    """Rule 8: the Q1 circuit files must contain no classical shortcut."""

    def test_q1_files_pass_the_guard(self):
        for rel in ("src/q1_shor_pe.py", "src/q1_run.py"):
            self.assertEqual(G.scan_file(rel, "all"), [], rel)

    def test_guard_discovers_q1_automatically(self):
        self.assertIn("src/q1_shor_pe.py", G.discover_guarded())


@unittest.skipUnless(HAS_QISKIT, "qiskit not installed")
class BuilderTests(unittest.TestCase):
    def test_controlled_matrix_is_a_unitary_permutation(self):
        import numpy as np
        from src.q1_shor_pe import controlled_modmul_matrix
        for mult, N in [(7, 15), (4, 15), (2, 21), (16, 35)]:
            n = N.bit_length()
            M = controlled_modmul_matrix(mult, N, n)
            self.assertTrue(np.allclose(M.conj().T @ M, np.eye(2 ** (n + 1))))
            self.assertEqual(set(np.unique(M)), {0.0, 1.0})

    def test_controlled_matrix_matches_plain_arithmetic(self):
        # rule 9: truth table against plain Python on every basis input
        import numpy as np
        from src.q1_shor_pe import controlled_modmul_matrix
        N, mult = 21, 5
        n = N.bit_length()
        M = controlled_modmul_matrix(mult, N, n)
        for c in (0, 1):
            for x in range(2 ** n):
                out = int(np.argmax(np.abs(M[:, c + 2 * x])))
                want = (mult * x) % N if (c == 1 and x < N) else x
                self.assertEqual(out, c + 2 * want)

    def test_inverse_qft_ops_equal_inverse_dft(self):
        import numpy as np
        from src.q1_shor_pe import inverse_qft_ops
        for m in (2, 3, 4, 5):
            D = 2 ** m
            U = np.eye(D, dtype=complex)
            for op in inverse_qft_ops(m):
                U = _gate_matrix(op, m) @ U
            want = np.array([[cmath.exp(-2j * math.pi * x * y / D) for x in range(D)]
                             for y in range(D)]) / math.sqrt(D)
            self.assertTrue(np.allclose(U, want), f"m={m}")

    def test_bad_inputs_rejected(self):
        from src.q1_shor_pe import build_shor_pe
        with self.assertRaises(ValueError):
            build_shor_pe(5, 15)                                # gcd(5, 15) = 5


def _gate_matrix(op, m):
    """Full 2**m matrix of one gate-list entry (little-endian qubit order)."""
    import numpy as np
    D = 2 ** m
    G_ = np.zeros((D, D), dtype=complex)
    for i in range(D):
        bits = [(i >> q) & 1 for q in range(m)]
        if op[0] == "h":
            q = op[1]
            for b in (0, 1):
                j = i & ~(1 << q) | (b << q)
                G_[j, i] += (1 if not (bits[q] and b) else -1) / math.sqrt(2)
        elif op[0] == "cp":
            _, ang, c, t = op
            G_[i, i] = cmath.exp(1j * ang) if (bits[c] and bits[t]) else 1
        else:
            _, p, q = op
            j = i
            if bits[p] != bits[q]:
                j = i ^ (1 << p) ^ (1 << q)
            G_[j, i] = 1
    return G_


@unittest.skipUnless(HAS_QISKIT and SLOW, "slow quantum test: install qiskit and set RUN_SLOW=1")
class SlowRunTests(unittest.TestCase):
    def test_n15_a7_finds_3_and_5_and_matches_theory(self):
        from src.q1_run import run_q1
        rec, _ = run_q1(7, 15, shots=4096)
        self.assertEqual(rec["result"]["period"], 4)
        self.assertEqual(rec["result"]["factors"], [3, 5])
        self.assertGreater(rec["chi_square"]["p_value"], 0.001)
        self.assertTrue(rec["cross_check"]["agree"])
        self.assertEqual(rec["seed_simulator"], 12345)

    def test_change_the_question_n21_a2(self):
        from src.q1_run import run_q1
        rec, _ = run_q1(2, 21, shots=4096)
        self.assertEqual(rec["result"]["period"], 6)
        self.assertEqual(rec["result"]["factors"], [3, 7])

    def test_record_is_valid_for_the_evidence_gate(self):
        from src import quantum_runs as QR
        from src.q1_run import run_q1
        rec, _ = run_q1(7, 15, shots=1024, cross_check=False)
        self.assertEqual(QR.validate_run(rec), [])


if __name__ == "__main__":
    unittest.main()
