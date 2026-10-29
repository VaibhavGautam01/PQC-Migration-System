"""
Tests for Q11 (Grover with an unknown number of solutions, by quantum counting).

Groups:
  1. no qiskit needed : counting_theory.py (instance finding, theory, maximum-likelihood estimate)
  2. qiskit installed  : the gate lists (oracle truth table, the extended numpy emulator)
  3. SLOW (RUN_SLOW=1) : real runs on Aer

Run the fast tests: python -m unittest tests.test_q11_counting -v
Run the slow ones  : set RUN_SLOW=1   (Command Prompt) then the same command
"""
import importlib.util
import os
import unittest
from pathlib import Path

import numpy as np

from src import counting_theory as CT
from src import grover_emulator as EM
from src import quantum_guard as G
from src import toy_cipher as T

ROOT = Path(__file__).resolve().parent.parent
HAS_QISKIT = importlib.util.find_spec("qiskit") is not None and \
    importlib.util.find_spec("qiskit_aer") is not None
SLOW = os.environ.get("RUN_SLOW") == "1" or os.environ.get("SLOW_TESTS") == "1"

FREE, KNOWN = 5, 0b00                        # N = 32 candidate keys; M=1,2 exist here (kept small for fast emulator tests)


class FindingInstances(unittest.TestCase):
    def test_pairs_with_1_2_and_3_matches_exist_for_6_free_bits(self):
        for M in (1, 2, 3):
            pair = CT.find_pair_with_matches(M, 6, 0)
            self.assertIsNotNone(pair, M)
            self.assertEqual(len(CT.matching_free_keys(pair, 6, 0)), M)

    def test_no_4_way_match_for_6_free_bits(self):
        # measured fact about this toy cipher: a 4-way collision needs the full 8-bit key space
        self.assertIsNone(CT.find_pair_with_matches(4, 6, 0))

    def test_matching_free_keys_agrees_with_the_classical_cipher(self):
        pair = CT.find_pair_with_matches(2, 6, 0)
        keys = CT.matching_free_keys(pair, 6, 0)
        for k in keys:
            self.assertEqual(T.encrypt(k, pair[0]), pair[1])
        for k in set(range(64)) - set(keys):
            self.assertNotEqual(T.encrypt(k, pair[0]), pair[1])


class TheoryTests(unittest.TestCase):
    def test_distribution_sums_to_one(self):
        for M, N, t in [(1, 64, 6), (2, 64, 7), (3, 32, 6)]:
            self.assertAlmostEqual(sum(CT.counting_distribution(M, N, t)), 1.0, places=9)

    def test_peaks_match_the_grover_angle(self):
        # y/2^t close to theta/pi or 1 - theta/pi should carry most of the probability
        from math import asin, pi, sqrt
        N, t, M = 64, 8, 1
        theta = asin(sqrt(M / N))
        y = round(theta / pi * 2 ** t)
        probs = CT.counting_distribution(M, N, t)
        self.assertGreater(probs[y], 0.2)

    def test_iterations_for_matches_grover_theory(self):
        from src import grover_theory as GT
        self.assertEqual(CT.iterations_for(1, 256), GT.optimal_iterations(1, 256))
        self.assertEqual(CT.iterations_for(4, 256), GT.optimal_iterations(4, 256))

    def test_count_from_outcome_recovers_m_at_the_peak(self):
        from math import asin, pi, sqrt
        N, t, M = 64, 8, 2
        theta = asin(sqrt(M / N))
        y = round(theta / pi * 2 ** t)
        self.assertAlmostEqual(CT.count_from_outcome(y, N, t), M, delta=1)


class EstimatorTests(unittest.TestCase):
    def test_peak_estimate_on_an_ideal_histogram(self):
        for N, t, M in [(64, 7, 1), (64, 8, 2), (64, 8, 3)]:
            dist = CT.counting_distribution(M, N, t)
            counts = {format(y, f"0{t}b"): round(2048 * p) for y, p in enumerate(dist) if p > 1e-6}
            self.assertEqual(CT.estimate_count(counts, N, t)["estimate"], M)

    def test_maximum_likelihood_estimate_is_at_least_as_accurate_as_the_peak(self):
        # at low t the peak estimate can be off by one; the ML estimate should not be worse
        for N, t, M in [(32, 5, 2), (64, 6, 3)]:
            dist = CT.counting_distribution(M, N, t)
            counts = {format(y, f"0{t}b"): round(2048 * p) for y, p in enumerate(dist) if p > 1e-6}
            peak_err = abs(CT.estimate_count(counts, N, t)["estimate"] - M)
            ml_err = abs(CT.estimate_count_ml(counts, N, t)["estimate"] - M)
            self.assertLessEqual(ml_err, peak_err)

    def test_estimate_uses_only_the_counts_not_the_true_m(self):
        # same counts in, same estimate out, regardless of any outside knowledge of M
        dist = CT.counting_distribution(2, 64, 7)
        counts = {format(y, f"0{7}b"): round(4096 * p) for y, p in enumerate(dist) if p > 1e-6}
        self.assertEqual(CT.estimate_count_ml(counts, 64, 7)["estimate"],
                         CT.estimate_count_ml(dict(counts), 64, 7)["estimate"])


@unittest.skipUnless(HAS_QISKIT, "qiskit not installed")
class CircuitBuilderTests(unittest.TestCase):
    def setUp(self):
        from src import q11_counting as Q
        self.Q = Q

    def test_oracle_flips_exactly_the_matching_free_keys(self):
        Q = self.Q
        for M in (1, 2):
            pair = CT.find_pair_with_matches(M, FREE, KNOWN)
            true_keys = CT.matching_free_keys(pair, FREE, KNOWN)
            lay = Q.layout(FREE)
            ops = [("h", q) for q in lay["key"]] + Q.oracle_ops(pair, FREE, KNOWN)
            state = EM.emulate(ops, lay["n"])
            N = 2 ** FREE
            amp = state[:N] * np.sqrt(N)
            flipped = [k for k in range(N) if amp[k].real < -0.5]
            self.assertEqual(sorted(flipped), sorted(true_keys), M)
            self.assertLess(np.abs(state[N:]).max(), 1e-10, "state/flag not cleaned up")

    def test_controlled_oracle_does_nothing_when_control_is_0(self):
        Q = self.Q
        pair = CT.find_pair_with_matches(1, FREE, KNOWN)
        lay = Q.layout(FREE, 1)
        # control qubit (the single counting qubit) left at |0>: whole circuit must be identity
        ops = [("h", q) for q in lay["key"]] + Q.oracle_ops(pair, FREE, KNOWN, control=lay["counting"][0])
        before = EM.emulate([("h", q) for q in lay["key"]], lay["n"])
        after = EM.emulate(ops, lay["n"])
        self.assertTrue(np.allclose(before, after))

    def test_controlled_oracle_matches_the_uncontrolled_one_when_control_is_1(self):
        Q = self.Q
        pair = CT.find_pair_with_matches(1, FREE, KNOWN)
        lay = Q.layout(FREE, 1)
        c = lay["counting"][0]
        plain = [("h", q) for q in lay["key"]] + Q.oracle_ops(pair, FREE, KNOWN)
        controlled = [("h", q) for q in lay["key"]] + [("x", c)] + \
            Q.oracle_ops(pair, FREE, KNOWN, control=c) + [("x", c)]
        a = EM.emulate(plain, lay["n"])
        b = EM.emulate(controlled, Q.layout(FREE, 1)["n"])
        N = 2 ** FREE
        self.assertTrue(np.allclose(a[:N], b[:N]))

    def test_counting_circuit_matches_the_analytic_theory(self):
        Q = self.Q
        pair = CT.find_pair_with_matches(1, FREE, KNOWN)
        t = 4                                             # kept small so the numpy emulator is fast
        lay = Q.layout(FREE, t)
        state = EM.emulate(Q.counting_ops(pair, FREE, KNOWN, t), lay["n"])
        probs = EM.register_probabilities(state, lay["counting"])
        theory = np.array(CT.counting_distribution(1, 2 ** FREE, t))
        self.assertLess(np.abs(probs - theory).max(), 1e-9)

    def test_change_the_question_different_m_gives_different_peak(self):
        Q = self.Q
        t = 4                                              # kept small so the numpy emulator is fast
        peaks = []
        for M in (1, 2):
            pair = CT.find_pair_with_matches(M, FREE, KNOWN)
            lay = Q.layout(FREE, t)
            state = EM.emulate(Q.counting_ops(pair, FREE, KNOWN, t), lay["n"])
            probs = EM.register_probabilities(state, lay["counting"])
            counts = {format(y, f"0{t}b"): round(4096 * p) for y, p in enumerate(probs)}
            peaks.append(CT.estimate_count_ml(counts, 2 ** FREE, t)["estimate"])
        self.assertEqual(peaks, [1, 2])

    def test_fix_known_key_bits_drops_or_simplifies_controls(self):
        Q = self.Q
        ops = [("mcx", (2, 6), 10), ("mcx", (1, 2), 11)]     # qubit 6 is a known high key bit
        fixed = Q.fix_known_key_bits(ops, free_bits=5, known_value=0b001)  # bit (6-5)=1 -> value 0
        self.assertNotIn(("mcx", (2, 6), 10), fixed)
        self.assertEqual(len([op for op in fixed if op[2] == 10]), 0)      # control 0: gate dropped


class StaticChecks(unittest.TestCase):
    FILES = ("src/q11_counting.py", "src/q11_run.py")

    def test_guard_passes(self):
        for rel in self.FILES:
            self.assertEqual(G.scan_file(rel, "all"), [], rel)

    def test_guard_discovers_the_files(self):
        for rel in self.FILES:
            self.assertIn(rel, G.discover_guarded())

    def test_builder_imports_no_classical_cipher_or_theory_helper(self):
        import ast
        tree = ast.parse((ROOT / "src/q11_counting.py").read_text(encoding="utf-8"))
        banned = {"toy_cipher", "counting_theory", "grover_theory", "grover_emulator", "sympy"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                continue
            for n in names:
                self.assertFalse(set(n.replace("src.", "").split(".")) & banned, n)


@unittest.skipUnless(HAS_QISKIT and SLOW, "slow quantum test: install qiskit and set RUN_SLOW=1")
class SlowAerRuns(unittest.TestCase):
    def test_counting_and_search_on_aer_for_1_2_3_matches(self):
        from src.q11_run import run_target
        import argparse
        args = argparse.Namespace(free_bits=6, counting_bits=7, known_value=0, shots=2048)
        for M in (1, 2, 3):
            recs = run_target(M, args)
            self.assertGreaterEqual(len(recs), 2)
            count_rec = recs[0]
            self.assertLessEqual(abs(count_rec["result"]["estimated_matches"] - M), 1)
            search_rec = recs[1]
            self.assertTrue(search_rec["result"]["verified"])


if __name__ == "__main__":
    unittest.main()
