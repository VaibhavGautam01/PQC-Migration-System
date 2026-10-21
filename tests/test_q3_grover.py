"""
Tests for Q3 (Grover on a toy cipher).

Groups
  1. no qiskit needed : classical cipher, theory formulas, numpy emulator
  2. qiskit installed : the gate lists (truth tables, oracle phase, static checks)
  3. SLOW (RUN_SLOW=1): full Grover runs, in the numpy emulator and on Aer

Run the fast tests : python -m unittest tests.test_q3_grover -v
Run the slow ones  : set RUN_SLOW=1   then the same command (Command Prompt syntax)
"""
import ast
import importlib.util
import os
import unittest
from pathlib import Path

import numpy as np

from src import grover_emulator as EM
from src import grover_theory as GT
from src import quantum_guard as G
from src import toy_cipher as T

ROOT = Path(__file__).resolve().parent.parent
HAS_QISKIT = importlib.util.find_spec("qiskit") is not None and \
    importlib.util.find_spec("qiskit_aer") is not None
SLOW = os.environ.get("RUN_SLOW") == "1" or os.environ.get("SLOW_TESTS") == "1"


class ToyCipherTests(unittest.TestCase):
    def test_sbox_is_a_permutation(self):
        self.assertEqual(sorted(T.SBOX), list(range(16)))

    def test_bit_permutation_is_a_permutation(self):
        self.assertEqual(sorted(T.BIT_PERM), list(range(8)))

    def test_rotl8(self):
        self.assertEqual(T.rotl8(0b10000001, 3), 0b00001100)
        self.assertEqual(T.rotl8(0xAB, 8), 0xAB)

    def test_encryption_is_a_permutation_for_every_key(self):
        for key in (0, 1, 183, 255):
            self.assertEqual(sorted(T.encrypt(key, p) for p in range(256)), list(range(256)))

    def test_two_default_pairs_identify_every_key_uniquely(self):
        # 16 bits of constraint for an 8-bit key: exactly one key matches, for all 256 secrets
        for secret in range(256):
            self.assertEqual(T.keys_matching(T.make_pairs(secret)), [secret])

    def test_consistent_checks_both_pairs(self):
        pairs = T.make_pairs(183)
        self.assertTrue(T.consistent(183, pairs))
        self.assertFalse(T.consistent(182, pairs))


class TheoryTests(unittest.TestCase):
    def test_start_probability_is_m_over_n(self):
        self.assertAlmostEqual(GT.success_probability(0, 1, 256), 1 / 256)
        self.assertAlmostEqual(GT.success_probability(0, 4, 256), 4 / 256)

    def test_optimal_rounds(self):
        self.assertEqual(GT.optimal_iterations(1, 256), 12)       # about pi/4 * sqrt(256)
        self.assertEqual(GT.optimal_iterations(4, 256), 6)        # fewer rounds with 4 solutions
        self.assertGreater(GT.success_probability(12, 1, 256), 0.999)

    def test_distribution_sums_to_one(self):
        for marked in ([7], [7, 99], [1, 2, 3, 4]):
            self.assertAlmostEqual(sum(GT.expected_distribution(5, marked, 256)), 1.0, places=12)

    def test_success_falls_after_the_optimum(self):
        self.assertLess(GT.success_probability(24, 1, 256), 0.5)  # overshoot: probability drops


class EmulatorTests(unittest.TestCase):
    def test_hadamard_makes_equal_superposition(self):
        s = EM.emulate([("h", 0), ("h", 1)], 2)
        self.assertTrue(np.allclose(np.abs(s) ** 2, 0.25))

    def test_x_and_mcx(self):
        s = EM.emulate([("x", 0), ("x", 1), ("mcx", (0, 1), 2)], 3)   # |011> -> |111>
        self.assertAlmostEqual(abs(s[0b111]), 1.0)
        s = EM.emulate([("x", 0), ("mcx", (0, 1), 2)], 3)             # control 1 is 0: no flip
        self.assertAlmostEqual(abs(s[0b001]), 1.0)

    def test_run_classical_rejects_hadamard(self):
        with self.assertRaises(ValueError):
            EM.run_classical([("h", 0)], {})

    def test_register_probabilities(self):
        s = EM.emulate([("x", 1)], 3)
        p = EM.register_probabilities(s, [0, 1])
        self.assertAlmostEqual(p[0b10], 1.0)


@unittest.skipUnless(HAS_QISKIT, "qiskit not installed")
class GateListTests(unittest.TestCase):
    def setUp(self):
        from src import q3_grover as Q
        self.Q = Q

    def test_sbox_network_equals_the_table_on_every_input(self):        # rule 9
        for v in range(16):
            out = EM.run_classical(self.Q.sbox_ops((0, 1, 2, 3)), {i: (v >> i) & 1 for i in range(4)})
            self.assertEqual(sum(out[i] << i for i in range(4)), T.SBOX[v])

    def test_cipher_gates_equal_classical_cipher_for_all_keys(self):    # rule 9 truth table
        Q = self.Q
        for plaintext in (0x00, 0x5A, 0xC3, 0xFF, 0x13):
            ops, out_wires = Q.encrypt_ops(plaintext)
            for key in range(256):
                bits = {Q.KEY[i]: (key >> i) & 1 for i in range(8)}
                result = EM.run_classical(ops, bits)
                cipher = sum(result.get(out_wires[j], 0) << j for j in range(8))
                self.assertEqual(cipher, T.encrypt(key, plaintext), (plaintext, key))

    def test_encrypt_ops_are_self_inverse(self):
        Q = self.Q
        ops, _ = Q.encrypt_ops(0x5A)
        bits = {Q.KEY[i]: (183 >> i) & 1 for i in range(8)}
        back = EM.run_classical(list(ops) + list(reversed(ops)), bits)
        self.assertEqual({q: v for q, v in back.items() if v}, {q: v for q, v in bits.items() if v})

    def test_oracle_flips_only_the_matching_key_and_leaves_ancillas_clean(self):
        Q = self.Q
        for secret in (183, 42):
            pairs = T.make_pairs(secret)
            ops = [("h", q) for q in Q.KEY] + Q.oracle_ops(pairs)
            state = EM.emulate(ops, Q.NUM_QUBITS)
            index = np.arange(state.size)
            self.assertLess(np.abs(state[(index >> 8) != 0]).max(), 1e-12)   # STATE, FLAGS back to 0
            amp = state[:256] * 16                                           # 16 = sqrt(256)
            expected = np.ones(256)
            expected[secret] = -1
            self.assertTrue(np.allclose(amp, expected))

    def test_oracle_with_a_single_pair_marks_every_matching_key(self):
        Q = self.Q
        pairs = T.make_pairs(77)[:1]
        marked = T.keys_matching(pairs)
        self.assertGreaterEqual(len(marked), 1)             # one 8-bit pair is a weak constraint: a few keys may fit
        ops = [("h", q) for q in Q.KEY] + Q.oracle_ops(pairs)
        amp = EM.emulate(ops, Q.NUM_QUBITS)[:256] * 16
        self.assertEqual(sorted(np.nonzero(np.real(amp) < 0)[0].tolist()), marked)

    def test_qubit_layout_does_not_overlap(self):
        Q = self.Q
        self.assertEqual(sorted(Q.KEY + Q.STATE + Q.FLAGS), list(range(Q.NUM_QUBITS)))

    def test_rejects_three_pairs(self):
        with self.assertRaises(ValueError):
            self.Q.build_grover([(1, 2), (3, 4), (5, 6)], 1)

    def test_circuit_has_the_expected_registers(self):
        qc = self.Q.build_grover(T.make_pairs(183), 1)
        self.assertEqual(qc.num_qubits, 18)
        self.assertEqual(qc.num_clbits, 8)


class StaticChecks(unittest.TestCase):
    """Rule 3 and rule 8: the circuit builder must not be able to see the answer."""
    FILES = ("src/q3_grover.py", "src/q3_run.py")

    def test_guard_passes_on_q3_files(self):
        for rel in self.FILES:
            self.assertEqual(G.scan_file(rel, "all"), [], rel)

    def test_guard_discovers_q3_automatically(self):
        for rel in self.FILES:
            self.assertIn(rel, G.discover_guarded())

    def test_builder_imports_no_classical_helper(self):
        tree = ast.parse((ROOT / "src/q3_grover.py").read_text(encoding="utf-8"))
        banned = {"toy_cipher", "grover_theory", "grover_emulator", "shor_post", "sympy"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            else:
                continue
            for n in names:
                self.assertFalse(set(n.replace("src.", "").split(".")) & banned, n)

    def test_no_builder_function_takes_a_key(self):
        tree = ast.parse((ROOT / "src/q3_grover.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for arg in node.args.args:
                    self.assertNotIn(arg.arg, {"key", "secret", "secret_key", "marked_key"},
                                     f"{node.name}({arg.arg})")


@unittest.skipUnless(HAS_QISKIT and SLOW, "slow quantum test: install qiskit and set RUN_SLOW=1")
class SlowRuns(unittest.TestCase):
    def test_emulator_finds_the_key_for_three_different_pairs(self):     # change the question
        from src import q3_grover as Q
        for secret in (183, 42, 250):
            pairs = T.make_pairs(secret)
            k = GT.optimal_iterations(1, 256)
            state = EM.emulate(Q.grover_ops(pairs, k), Q.NUM_QUBITS)
            probs = EM.register_probabilities(state, list(Q.KEY))
            self.assertEqual(int(probs.argmax()), secret)
            self.assertGreater(probs[secret], 0.999)

    def test_aer_run_finds_the_key_and_matches_theory(self):
        from src import quantum_runs as QR
        from src.q3_run import run_q3
        rec = run_q3(183, 12, shots=2048, cross_check=True, diagram_file="docs/circuits/x.txt")
        self.assertEqual(rec["result"]["found_key"], 183)
        self.assertTrue(rec["result"]["verified"])
        self.assertGreater(rec["success_rate"], 0.95)
        self.assertGreater(rec["chi_square"]["p_value"], 0.001)
        self.assertTrue(rec["cross_check"]["agree"])
        clean = {k: v for k, v in rec.items() if not k.startswith("_")}
        self.assertEqual(QR.validate_run(clean), [])

    def test_aer_change_the_marked_key(self):
        from src.q3_run import run_q3
        a = run_q3(42, 12, shots=2048, diagram_file="docs/circuits/x.txt")
        b = run_q3(250, 12, shots=2048, diagram_file="docs/circuits/x.txt")
        self.assertEqual((a["result"]["found_key"], b["result"]["found_key"]), (42, 250))


if __name__ == "__main__":
    unittest.main()
