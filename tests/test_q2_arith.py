"""
Truth-table tests for the Q2 adders (rule 9): every basis input for small n,
compared with plain Python arithmetic.
Fast: python -m unittest discover -s tests
Slow (N = 15, 21): set SLOW_TESTS=1 first (PowerShell: $env:SLOW_TESTS="1")
"""
"""
Truth-table tests for the Q2 adders (rule 9): every basis input for small n,
compared with plain Python arithmetic.
Fast: python -m unittest discover -s tests
Slow (N = 15, 21): set SLOW_TESTS=1 first (PowerShell: $env:SLOW_TESTS="1")
"""
import itertools
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from qiskit import QuantumCircuit  # noqa: E402
from qiskit.quantum_info import Statevector  # noqa: E402

import math  # noqa: E402

from q2_arith import (controlled_modmul, modular_adder_phi,  # noqa: E402 # type: ignore
                      modular_exponentiation, modular_subtractor_phi, phi_add,
                      qft_dagger_gates, qft_gates)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


from q2_arith import (modular_adder_phi, phi_add, qft_dagger_gates,  # noqa: E402 # type: ignore
                      qft_gates)

SLOW = os.environ.get("SLOW_TESTS") == "1"


def outcome(qc):
    """The single measured basis state of a deterministic circuit, as an int."""
    probs = Statevector(qc).probabilities_dict()
    big = {k: p for k, p in probs.items() if p > 1e-9}
    assert len(big) == 1 and abs(sum(big.values()) - 1) < 1e-6, f"not deterministic: {big}"
    return int(next(iter(big)), 2)


def load(qc, qubits, value):
    for k, q in enumerate(qubits):
        if (value >> k) & 1:
            qc.x(q)


class TestQFT(unittest.TestCase):
    def test_qft_then_inverse_is_identity(self):
        for x in range(16):
            qc = QuantumCircuit(4)
            load(qc, range(4), x)
            qft_gates(qc, list(range(4)))
            qft_dagger_gates(qc, list(range(4)))
            self.assertEqual(outcome(qc), x)


class TestPhiAdd(unittest.TestCase):
    def test_add_all_inputs_4_qubits(self):
        reg = list(range(4))
        for x, a in itertools.product(range(16), repeat=2):
            qc = QuantumCircuit(4)
            load(qc, reg, x)
            qft_gates(qc, reg)
            phi_add(qc, reg, a)
            qft_dagger_gates(qc, reg)
            self.assertEqual(outcome(qc), (x + a) % 16, f"x={x} a={a}")

    def test_subtract(self):
        reg = list(range(4))
        for x, a in itertools.product(range(16), repeat=2):
            qc = QuantumCircuit(4)
            load(qc, reg, x)
            qft_gates(qc, reg)
            phi_add(qc, reg, a, sign=-1)
            qft_dagger_gates(qc, reg)
            self.assertEqual(outcome(qc), (x - a) % 16, f"x={x} a={a}")

    def test_controlled_add(self):
        reg, ctrl = [0, 1, 2], 3
        for c, x, a in itertools.product((0, 1), range(8), range(8)):
            qc = QuantumCircuit(4)
            load(qc, reg, x)
            if c:
                qc.x(ctrl)
            qft_gates(qc, reg)
            phi_add(qc, reg, a, controls=[ctrl])
            qft_dagger_gates(qc, reg)
            expected = ((x + a) % 8) + (c << 3) if c else x
            self.assertEqual(outcome(qc), expected, f"c={c} x={x} a={a}")


def check_modular_adder(test, N):
    n = N.bit_length()
    b = list(range(n + 1))
    anc = n + 1
    ctrls = [n + 2, n + 3]
    for a, bv, c1, c2 in itertools.product(range(N), range(N), (0, 1), (0, 1)):
        qc = QuantumCircuit(n + 4)
        load(qc, b, bv)
        if c1:
            qc.x(ctrls[0])
        if c2:
            qc.x(ctrls[1])
        qft_gates(qc, b)
        modular_adder_phi(qc, b, anc, a, N, controls=ctrls)
        qft_dagger_gates(qc, b)
        v = outcome(qc)
        got_b = v & (2 ** (n + 1) - 1)
        got_anc = (v >> (n + 1)) & 1
        got_c = (v >> (n + 2)) & 3
        expected_b = (bv + a) % N if (c1 and c2) else bv
        msg = f"N={N} a={a} b={bv} c=({c1},{c2})"
        test.assertEqual(got_b, expected_b, msg)
        test.assertEqual(got_anc, 0, "ancilla not returned to 0: " + msg)
        test.assertEqual(got_c, c1 + 2 * c2, "controls changed: " + msg)


class TestModularAdder(unittest.TestCase):
    def test_small_moduli(self):
        for N in (3, 5, 7):
            with self.subTest(N=N):
                check_modular_adder(self, N)

    def test_uncontrolled(self):
        N, n = 5, 3
        b, anc = list(range(n + 1)), n + 1
        for a, bv in itertools.product(range(N), repeat=2):
            qc = QuantumCircuit(n + 2)
            load(qc, b, bv)
            qft_gates(qc, b)
            modular_adder_phi(qc, b, anc, a, N)
            qft_dagger_gates(qc, b)
            self.assertEqual(outcome(qc), (bv + a) % N, f"a={a} b={bv}")

    def test_bad_inputs(self):
        qc = QuantumCircuit(5)
        with self.assertRaises(ValueError):
            modular_adder_phi(qc, [0, 1, 2], 3, 5, 5)      # a >= N
        with self.assertRaises(ValueError):
            modular_adder_phi(qc, [0, 1, 2], 3, 1, 5)      # N too big for register

    @unittest.skipUnless(SLOW, "set SLOW_TESTS=1 to run N = 15 and 21")
    def test_shor_sized_moduli_slow(self):
        for N in (15, 21):
            with self.subTest(N=N):
                check_modular_adder(self, N)
class TestModularSubtractor(unittest.TestCase):
    def test_subtract_all_inputs(self):
        for N in (3, 5, 7):
            n = N.bit_length()
            b = list(range(n + 1))
            anc, ctrl = n + 1, n + 2
            for a, bv, c in itertools.product(range(N), range(N), (0, 1)):
                qc = QuantumCircuit(n + 3)
                load(qc, b, bv)
                if c:
                    qc.x(ctrl)
                qft_gates(qc, b)
                modular_subtractor_phi(qc, b, anc, a, N, controls=[ctrl])
                qft_dagger_gates(qc, b)
                v = outcome(qc)
                expected = (bv - a) % N if c else bv
                msg = f"N={N} a={a} b={bv} c={c}"
                self.assertEqual(v & (2 ** (n + 1) - 1), expected, msg)
                self.assertEqual((v >> (n + 1)) & 1, 0, "ancilla not 0: " + msg)

    def test_add_then_subtract_restores_input(self):
        N, n = 7, 3
        b, anc = list(range(n + 1)), n + 1
        for a, bv in itertools.product(range(N), repeat=2):
            qc = QuantumCircuit(n + 2)
            load(qc, b, bv)
            qft_gates(qc, b)
            modular_adder_phi(qc, b, anc, a, N)
            modular_subtractor_phi(qc, b, anc, a, N)
            qft_dagger_gates(qc, b)
            self.assertEqual(outcome(qc), bv, f"a={a} b={bv}")

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            modular_subtractor_phi(QuantumCircuit(5), [0, 1, 2, 3], 4, 7, 7)

def check_multiplier(test, N):
    n = N.bit_length()
    x, b = list(range(n)), list(range(n, 2 * n + 1))
    anc, c = 2 * n + 1, 2 * n + 2
    for a in range(1, N):
        if math.gcd(a, N) != 1:
            continue
        for xv, cv in itertools.product(range(N), (0, 1)):
            qc = QuantumCircuit(2 * n + 3)
            load(qc, x, xv)
            if cv:
                qc.x(c)
            controlled_modmul(qc, c, x, b, anc, a, N)
            v = outcome(qc)
            msg = f"N={N} a={a} x={xv} c={cv}"
            test.assertEqual(v & (2 ** n - 1), (a * xv) % N if cv else xv, "x: " + msg)
            test.assertEqual((v >> n) & (2 ** (n + 1) - 1), 0, "b not returned to 0: " + msg)
            test.assertEqual((v >> (2 * n + 1)) & 1, 0, "ancilla not 0: " + msg)
            test.assertEqual((v >> (2 * n + 2)) & 1, cv, "control changed: " + msg)


def check_exponentiation(test, N, a_values, m):
    n = N.bit_length()
    x, b = list(range(n)), list(range(n, 2 * n + 1))
    anc = 2 * n + 1
    e = list(range(2 * n + 2, 2 * n + 2 + m))
    for a in a_values:
        for ev in range(2 ** m):
            qc = QuantumCircuit(2 * n + 2 + m)
            qc.x(x[0])                       # x starts as |1>
            load(qc, e, ev)
            modular_exponentiation(qc, e, x, b, anc, a, N)
            v = outcome(qc)
            msg = f"N={N} a={a} e={ev}"
            test.assertEqual(v & (2 ** n - 1), pow(a, ev, N), "a^e mod N: " + msg)
            test.assertEqual((v >> n) & (2 ** (n + 1) - 1), 0, "b not 0: " + msg)
            test.assertEqual((v >> (2 * n + 1)) & 1, 0, "ancilla not 0: " + msg)
            test.assertEqual(v >> (2 * n + 2), ev, "exponent changed: " + msg)

def check_multiplier_samples(test, N, samples):
    """Spot-check the multiplier for chosen (a, x, control) cases."""
    n = N.bit_length()
    x, b = list(range(n)), list(range(n, 2 * n + 1))
    anc, c = 2 * n + 1, 2 * n + 2
    for a, xv, cv in samples:
        qc = QuantumCircuit(2 * n + 3)
        load(qc, x, xv)
        if cv:
            qc.x(c)
        controlled_modmul(qc, c, x, b, anc, a, N)
        v = outcome(qc)
        msg = f"N={N} a={a} x={xv} c={cv}"
        test.assertEqual(v & (2 ** n - 1), (a * xv) % N if cv else xv, "x: " + msg)
        test.assertEqual((v >> n) & (2 ** (n + 1) - 1), 0, "b not returned to 0: " + msg)
        test.assertEqual((v >> (2 * n + 1)) & 1, 0, "ancilla not 0: " + msg)
        test.assertEqual((v >> (2 * n + 2)) & 1, cv, "control changed: " + msg)


class TestModularMultiplier(unittest.TestCase):
    def test_all_inputs_small_moduli(self):
        for N in (3, 5):
            with self.subTest(N=N):
                check_multiplier(self, N)

    def test_bad_inputs(self):
        qc = QuantumCircuit(12)
        with self.assertRaises(ValueError):
            controlled_modmul(qc, 8, [0, 1, 2], [3, 4, 5, 6], 7, 3, 6)   # gcd(3, 6) != 1
        with self.assertRaises(ValueError):
            controlled_modmul(qc, 8, [0, 1], [3, 4, 5], 7, 2, 5)         # N too big for x

    @unittest.skipUnless(SLOW, "set SLOW_TESTS=1 to run N = 7")
    def test_n7_slow(self):
        check_multiplier(self, 7)
    @unittest.skipUnless(SLOW, "set SLOW_TESTS=1 to run N = 35")
    def test_n35_sampled_slow(self):
        check_multiplier_samples(self, 35, [(2, 1, 1), (2, 17, 1), (3, 34, 1), (12, 29, 1), (2, 17, 0)])

class TestModularExponentiation(unittest.TestCase):
    def test_n3_all_exponents(self):
        check_exponentiation(self, 3, (2,), m=3)

    def test_n5_all_bases(self):
        check_exponentiation(self, 5, (2, 3, 4), m=2)

    @unittest.skipUnless(SLOW, "set SLOW_TESTS=1 to run N = 15")
    def test_n15_slow(self):
        check_exponentiation(self, 15, (7,), m=2)

if __name__ == "__main__":
    unittest.main()