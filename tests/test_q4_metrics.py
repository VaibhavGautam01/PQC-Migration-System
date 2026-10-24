import sys
import unittest
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import q4_metrics as q4  # type: ignore # noqa: E402


class TestModuli(unittest.TestCase):
    def test_each_modulus_has_exactly_n_bits_and_is_odd(self):
        for n, N in q4.MODULI.items():
            self.assertEqual(N.bit_length(), n)
            self.assertEqual(N % 2, 1)

    def test_moduli_are_the_planned_semiprimes(self):
        self.assertEqual(q4.MODULI, {4: 15, 5: 21, 6: 35, 7: 77, 8: 221})

    def test_unknown_size_rejected(self):
        for bad in (3, 9, 0, "4"):
            with self.assertRaises(ValueError):
                q4.modulus_for(bad)


class TestCircuits(unittest.TestCase):
    def test_iteration_circuit_uses_2n_plus_3_qubits(self):
        for n in (4, 5, 6):
            self.assertEqual(q4.iteration_circuit(n).num_qubits, 2 * n + 3)

    def test_full_circuit_uses_2n_plus_3_qubits_and_2n_clbits(self):
        qc = q4.full_circuit(4)
        self.assertEqual(qc.num_qubits, 11)
        self.assertEqual(qc.num_clbits, 8)

    def test_builder_module_has_no_forbidden_helpers(self):
        text = (SRC / "q4_metrics.py").read_text(encoding="utf-8")
        for word in ("sympy", "factorint", "n_order", "multiplicative_order", "isprime"):
            self.assertNotIn(word, text)


if __name__ == "__main__":
    unittest.main()