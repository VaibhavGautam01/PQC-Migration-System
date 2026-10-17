"""Formula tests with the worked reference values (plan section 4)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from risk_score import (band, classical_weakness, overall_risk,  # noqa: E402
                        project_score, quantum_risk, score_layer)

# X = 5, Y = 2, Z = 10; F6 = 100 (keyless); F4 = 5 for OAEP and AES-GCM
CASES = {
    "RSA-512 no padding": (dict(category="shor_broken", construction="no_padding_deterministic",
                                exposure="keyless", modulus_bits=512), (84.1, 100.0, 90.4)),
    "RSA-1024 no padding": (dict(category="shor_broken", construction="no_padding_deterministic",
                                 exposure="keyless", modulus_bits=1024), (81.6, 80.0, 80.9)),
    "RSA-2048 OAEP": (dict(category="shor_broken", construction="oaep",
                           exposure="keyless", modulus_bits=2048), (79.1, 8.5, 50.8)),
    "ML-KEM-768 + AES-256-GCM": (dict(category="nist_pqc", construction="aead",
                                      exposure="keyless", modulus_bits=None), (4.5, 5.0, 4.7)),
}


class TestWorkedValues(unittest.TestCase):
    def test_reference_cases(self):
        for name, (kwargs, (q, c, o)) in CASES.items():
            with self.subTest(case=name):
                r = score_layer(**kwargs)
                self.assertAlmostEqual(r["quantum"], q, places=1)
                self.assertAlmostEqual(r["classical"], c, places=1)
                self.assertAlmostEqual(r["overall"], o, places=1)

    def test_reference_order(self):
        o = {n: score_layer(**k)["overall"] for n, (k, _) in CASES.items()}
        names = list(CASES)
        for hi, lo in zip(names, names[1:]):
            self.assertGreater(o[hi], o[lo], f"{hi} should score above {lo}")

    def test_bands_of_reference_cases(self):
        self.assertEqual(score_layer(**CASES["RSA-512 no padding"][0])["band"], "Critical")
        self.assertEqual(score_layer(**CASES["RSA-2048 OAEP"][0])["band"], "High")
        self.assertEqual(score_layer(**CASES["ML-KEM-768 + AES-256-GCM"][0])["band"], "Low")


class TestMonotonic(unittest.TestCase):
    def test_bigger_key_never_raises_score(self):
        scores = [score_layer("shor_broken", "no_padding_deterministic", "keyless", bits)["overall"]
                  for bits in (256, 512, 768, 1024, 2048, 3072, 4096)]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_added_padding_never_raises_score(self):
        order = ["no_padding_deterministic", "deterministic_or_oracle",
                 "padding_without_aead", "oaep"]
        scores = [score_layer("shor_broken", c, "keyless", 2048)["overall"] for c in order]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_exposure_cannot_push_up_a_strong_layer(self):
        low = score_layer("nist_pqc", "aead", "keyed")["overall"]
        high = score_layer("nist_pqc", "aead", "keyless")["overall"]
        self.assertLess(high - low, 5)      # gated: exposure barely matters

    def test_longer_secrecy_never_lowers_quantum_risk(self):
        qs = [score_layer("shor_broken", "oaep", "keyless", 2048, x_years=x)["quantum"]
              for x in (1, 2, 5, 10)]
        self.assertEqual(qs, sorted(qs))


class TestFormulas(unittest.TestCase):
    def test_quantum_risk_formula(self):
        self.assertAlmostEqual(quantum_risk(100, 60, 70), 0.5 * 100 + 0.25 * 60 + 0.25 * 70)

    def test_quantum_risk_rescales_when_f2_missing(self):
        self.assertAlmostEqual(quantum_risk(5, None, 3.5), (0.5 * 5 + 0.25 * 3.5) / 0.75)

    def test_classical_formula_and_rescale(self):
        self.assertAlmostEqual(classical_weakness(50, 100, 100), 0.4 * 50 + 0.3 * 100 + 0.3 * 100)
        self.assertAlmostEqual(classical_weakness(None, 5, 5), 5.0)

    def test_overall(self):
        self.assertAlmostEqual(overall_risk(80, 20), 0.6 * 80 + 0.4 * 20)

    def test_project_score_weakest_link(self):
        self.assertAlmostEqual(project_score([90, 10]), 0.7 * 90 + 0.3 * 50)
        self.assertAlmostEqual(project_score([40]), 40)
        self.assertGreaterEqual(project_score([90, 10]), 50)   # one bad layer dominates

    def test_project_score_needs_a_layer(self):
        with self.assertRaises(ValueError):
            project_score([])

    def test_no_factor_applies(self):
        with self.assertRaises(ValueError):
            quantum_risk(None, None, None)


class TestBands(unittest.TestCase):
    def test_edges(self):
        for s, b in ((0, "Low"), (24.99, "Low"), (25, "Moderate"), (49.99, "Moderate"),
                     (50, "High"), (74.99, "High"), (75, "Critical"), (100, "Critical")):
            with self.subTest(score=s):
                self.assertEqual(band(s), b)

    def test_invalid(self):
        for bad in (-1, 100.1, "50", None, True):
            with self.assertRaises(ValueError):
                band(bad)


if __name__ == "__main__":
    unittest.main()