import unittest

from src import q2_arith as Q
from src import truth_table as T


def draper_add(a, n):
    """b -> (b + a) mod 2**n, built from QFT, phi_add and inverse QFT."""
    def block(qc):
        qs = list(range(n))
        Q.qft_gates(qc, qs)
        Q.phi_add(qc, qs, a)
        Q.qft_dagger_gates(qc, qs)
    return block


class HarnessTests(unittest.TestCase):
    def test_adder_matches_python_on_every_input(self):
        n = 3
        for a in range(2 ** n):
            self.assertEqual(
                T.verify_basis_map(n, draper_add(a, n), lambda x, a=a: (x + a) % 2 ** n), [],
                f"a={a}")

    def test_adder_matches_python_on_random_inputs_for_larger_n(self):
        n = 5
        ins = T.random_inputs(n, 6)
        self.assertEqual(len(ins), 6)
        self.assertEqual(T.verify_basis_map(n, draper_add(11, n), lambda x: (x + 11) % 2 ** n, ins), [])

    def test_wrong_expectation_is_reported(self):
        fails = T.verify_basis_map(3, draper_add(3, 3), lambda x: (x + 4) % 8)
        self.assertEqual(len(fails), 8)

    def test_non_permutation_block_is_reported(self):
        def hadamard(qc):
            qc.h(0)
        fails = T.verify_basis_map(2, hadamard, lambda x: x)
        self.assertTrue(any("spread" in f for f in fails))

    def test_x_gate_flips_the_right_bit(self):
        self.assertEqual(T.verify_basis_map(3, lambda qc: qc.x(1), lambda x: x ^ 2), [])

    def test_random_inputs_are_reproducible(self):
        self.assertEqual(T.random_inputs(6, 5), T.random_inputs(6, 5))
        self.assertEqual(T.random_inputs(2, 10), [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
