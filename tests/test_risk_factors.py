"""One test class per factor F1-F6. Run: python -m unittest discover -s tests"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from risk_score import (  # noqa: E402 # type: ignore
    f1_quantum_exposure, f2_qubit_cost, f3_classical_key_weakness,
    f4_construction_weakness, f5_data_lifetime, f5_effective,
    f6_effective, f6_exposure, load_weights,
)


class TestWeightsFile(unittest.TestCase):
    def test_loads_and_has_version(self):
        self.assertEqual(load_weights()["version"], "v1.0")

    def test_f1_none_category_is_zero(self):
        # no quantum-vulnerable algorithm in the layer (for example CRC32)
        self.assertEqual(f1_quantum_exposure("none"), 0.0)

    def test_weight_groups_sum_to_one(self):
        w = load_weights()
        for group in ("quantum_weights", "classical_weights", "overall_weights", "project_weights"):
            self.assertAlmostEqual(sum(w[group].values()), 1.0, msg=group)


class TestF1(unittest.TestCase):
    def test_shor_broken_is_100(self):
        self.assertEqual(f1_quantum_exposure("shor_broken"), 100)

    def test_nist_pqc_is_5(self):
        self.assertEqual(f1_quantum_exposure("nist_pqc"), 5)

    def test_grover_bands(self):
        self.assertEqual(f1_quantum_exposure("symmetric", 128), 10)
        self.assertEqual(f1_quantum_exposure("symmetric", 127), 30)
        self.assertEqual(f1_quantum_exposure("symmetric", 112), 30)
        self.assertEqual(f1_quantum_exposure("symmetric", 111), 60)
        self.assertEqual(f1_quantum_exposure("symmetric", 64), 60)

    def test_invalid(self):
        for args in (("magic",), ("symmetric",), ("symmetric", -1)):
            with self.assertRaises(ValueError):
                f1_quantum_exposure(*args)


class TestF2(unittest.TestCase):
    def test_worked_values(self):
        self.assertAlmostEqual(f2_qubit_cost(512), 66.28, places=1)    # q = 1027
        self.assertAlmostEqual(f2_qubit_cost(1024), 56.27, places=1)   # q = 2051
        self.assertAlmostEqual(f2_qubit_cost(2048), 46.24, places=1)   # q = 4099

    def test_decreases_with_key_size(self):
        self.assertGreater(f2_qubit_cost(512), f2_qubit_cost(2048))

    def test_limits(self):
        self.assertEqual(f2_qubit_cost(8), 100)             # q = 19, formula > 100
        self.assertEqual(f2_qubit_cost(10 ** 9), 20)        # huge key, floor at 20

    def test_not_applicable_and_invalid(self):
        self.assertIsNone(f2_qubit_cost(None))
        for bad in (0, -5, 1.5, "512", True):
            with self.assertRaises(ValueError):
                f2_qubit_cost(bad)


class TestF3(unittest.TestCase):
    def test_bands(self):
        for bits, expected in ((32, 100), (512, 100), (513, 80), (1023, 80),
                               (1024, 50), (2047, 50), (2048, 10), (4096, 10)):
            with self.subTest(bits=bits):
                self.assertEqual(f3_classical_key_weakness(bits), expected)

    def test_monotonic(self):
        sizes = (256, 512, 768, 1024, 2048, 3072)
        scores = [f3_classical_key_weakness(b) for b in sizes]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_not_applicable_and_invalid(self):
        self.assertIsNone(f3_classical_key_weakness(None))
        with self.assertRaises(ValueError):
            f3_classical_key_weakness(0)


class TestF4(unittest.TestCase):
    def test_values(self):
        self.assertEqual(f4_construction_weakness("no_padding_deterministic"), 100)
        self.assertEqual(f4_construction_weakness("deterministic_or_oracle"), 80)
        self.assertEqual(f4_construction_weakness("padding_without_aead"), 40)
        self.assertEqual(f4_construction_weakness("oaep"), 5)
        self.assertEqual(f4_construction_weakness("aead"), 5)

    def test_unknown(self):
        with self.assertRaises(ValueError):
            f4_construction_weakness("rot13")


class TestF5(unittest.TestCase):
    def test_mosca(self):
        self.assertEqual(f5_data_lifetime(5, 2, 10), 70)
        self.assertEqual(f5_data_lifetime(5, 2, 5), 100)    # (5+2)/5 > 1, capped
        self.assertEqual(f5_data_lifetime(5, 2, 20), 35)

    def test_gating(self):
        self.assertEqual(f5_effective(70, 100), 70)
        self.assertAlmostEqual(f5_effective(70, 5), 3.5)    # ML-KEM layer
        self.assertEqual(f5_effective(70, 0), 0)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            f5_data_lifetime(5, 2, 0)
        with self.assertRaises(ValueError):
            f5_data_lifetime(-1, 2, 10)


class TestF6(unittest.TestCase):
    def test_values(self):
        self.assertEqual(f6_exposure("keyless"), 100)
        self.assertEqual(f6_exposure("bypassable"), 90)
        self.assertEqual(f6_exposure("keyed"), 30)

    def test_gating_uses_max_of_f3_f4(self):
        self.assertEqual(f6_effective(100, 10, 5), 10)      # RSA-2048 + OAEP
        self.assertEqual(f6_effective(100, 100, 100), 100)  # RSA-512 no padding

    def test_f3_not_applicable_uses_f4_alone(self):
        self.assertEqual(f6_effective(100, None, 5), 5)     # ML-KEM + AES-GCM

    def test_unknown(self):
        with self.assertRaises(ValueError):
            f6_exposure("sometimes")


if __name__ == "__main__":
    unittest.main()