"""
test_qubit_estimator.py
-----------------------
Unit tests for qubit_estimator.py (Issue #7).
Run with:  python -m unittest test_qubit_estimator -v
"""

import unittest

from qubit_estimator import (
    GROVER_AES_LOGICAL_QUBITS,
    grover_effective_security,
    grover_logical_qubits,
    grover_verdict,
    shor_logical_qubits,
)

INVALID_INPUTS = [0, -1, -512, 1.5, 1024.0, "1024", None, True, False]


class TestShorLogicalQubits(unittest.TestCase):
    def test_512_bit_dummy_key(self):
        self.assertEqual(shor_logical_qubits(512), 1027)

    def test_1024_bit_dummy_key(self):
        self.assertEqual(shor_logical_qubits(1024), 2051)

    def test_2048_bit_key(self):
        self.assertEqual(shor_logical_qubits(2048), 4099)

    def test_formula_holds_for_several_sizes(self):
        for n in (1, 64, 256, 3072, 4096):
            self.assertEqual(shor_logical_qubits(n), 2 * n + 3)

    def test_grows_with_key_size(self):
        self.assertLess(shor_logical_qubits(1024), shor_logical_qubits(2048))

    def test_returns_int(self):
        self.assertIsInstance(shor_logical_qubits(1024), int)

    def test_invalid_input_rejected(self):
        for bad in INVALID_INPUTS:
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    shor_logical_qubits(bad)


class TestGroverEffectiveSecurity(unittest.TestCase):
    def test_halves_the_key_size(self):
        self.assertEqual(grover_effective_security(128), 64)
        self.assertEqual(grover_effective_security(192), 96)
        self.assertEqual(grover_effective_security(256), 128)

    def test_never_exceeds_original_key_size(self):
        for k in (128, 192, 256):
            self.assertLess(grover_effective_security(k), k)

    def test_invalid_input_rejected(self):
        for bad in INVALID_INPUTS:
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    grover_effective_security(bad)


class TestGroverLogicalQubits(unittest.TestCase):
    def test_published_values(self):
        self.assertEqual(grover_logical_qubits(128), 2953)
        self.assertEqual(grover_logical_qubits(192), 4449)
        self.assertEqual(grover_logical_qubits(256), 6681)

    def test_table_has_exactly_the_aes_sizes(self):
        self.assertEqual(set(GROVER_AES_LOGICAL_QUBITS), {128, 192, 256})

    def test_larger_key_needs_more_qubits(self):
        self.assertLess(grover_logical_qubits(128), grover_logical_qubits(192))
        self.assertLess(grover_logical_qubits(192), grover_logical_qubits(256))

    def test_unknown_key_size_returns_none(self):
        self.assertIsNone(grover_logical_qubits(100))
        self.assertIsNone(grover_logical_qubits(512))

    def test_invalid_input_rejected(self):
        for bad in INVALID_INPUTS:
            with self.subTest(value=bad):
                with self.assertRaises(ValueError):
                    grover_logical_qubits(bad)


class TestGroverVerdict(unittest.TestCase):
    def test_aes_128_and_192_are_weakened(self):
        self.assertTrue(grover_verdict(128).startswith("WEAKENED"))
        self.assertTrue(grover_verdict(192).startswith("WEAKENED"))

    def test_aes_256_is_safe(self):
        self.assertTrue(grover_verdict(256).startswith("SAFE"))

    def test_boundary_at_128_effective_bits(self):
        self.assertTrue(grover_verdict(255).startswith("WEAKENED"))  # 127 effective
        self.assertTrue(grover_verdict(256).startswith("SAFE"))      # 128 effective


class TestShorVsGroverDifference(unittest.TestCase):
    """The report must not overstate the threat to symmetric keys."""

    def test_shor_breaks_rsa_but_grover_only_halves_aes(self):
        # Shor's on a 2048-bit RSA key needs far fewer qubits than Grover's on AES-256
        self.assertLess(shor_logical_qubits(2048), grover_logical_qubits(256))
        # ...but AES-256 still keeps 128-bit effective security
        self.assertEqual(grover_effective_security(256), 128)


if __name__ == "__main__":
    unittest.main()