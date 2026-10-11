"""Synthetic ECC tests: prove the mapper handles more than RSA (Issue #5).

The real findings only contain RSA, so these tests use made-up ECC findings.

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import quantum_mapper as qm  # noqa: E402


def ecc(primitive, bits=None, line=1, **extra):
    item = {"project": "SYNTHETIC-ECC", "file": "synthetic/ecc.py", "line": line,
            "primitive": primitive, "pattern_id": "synthetic", "confidence": "high",
            "key_size": bits, "modulus_bits": None, "size_basis": "synthetic", "snippet": ""}
    item.update(extra)
    return item


SYNTHETIC = [
    ecc("ECDSA", 256, line=1),
    ecc("ECDSA", 384, line=2),
    ecc("ECDH", 256, line=3),
    ecc("Ed25519", 256, line=4),
    ecc("X25519", 256, line=5),
    ecc("ECC", None, line=6),
]


class TestEccMapping(unittest.TestCase):
    def setUp(self):
        self.mapped = qm.map_findings(SYNTHETIC)

    def test_every_ecc_variant_maps_to_ecc(self):
        for m in self.mapped:
            with self.subTest(primitive=m["primitive"]):
                self.assertEqual(m["canonical_primitive"], "ECC")

    def test_every_ecc_variant_routes_to_shor_and_is_broken(self):
        for m in self.mapped:
            with self.subTest(primitive=m["primitive"]):
                self.assertEqual(m["quantum_algorithm"], qm.SHOR)
                self.assertEqual(m["impact"], "BROKEN")
                self.assertEqual(m["post_quantum_security_bits"], 0)

    def test_hard_problem_is_ecdlp_not_factoring(self):
        for m in self.mapped:
            self.assertIn("Elliptic-curve", m["hard_problem"])

    def test_curve_size_is_kept_and_does_not_raise_a_prime_size_warning(self):
        sizes = [m["size_used_bits"] for m in self.mapped]
        self.assertEqual(sizes, [256, 384, 256, 256, 256, None])
        self.assertTrue(all(m["size_warning"] is None for m in self.mapped))

    def test_pqc_recommendation_mentions_ml_dsa_and_ml_kem(self):
        text = self.mapped[0]["pqc_replacement"]
        self.assertIn("ML-DSA", text)
        self.assertIn("ML-KEM", text)

    def test_ecc_is_not_routed_to_grover(self):
        self.assertNotIn(qm.GROVER, {m["quantum_algorithm"] for m in self.mapped})

    def test_grover_assessment_is_not_applicable_to_ecc(self):
        self.assertTrue(all(m["grover_assessment"] is None for m in self.mapped))


class TestEccMixedWithOtherPrimitives(unittest.TestCase):
    def setUp(self):
        mixed = SYNTHETIC[:2] + [
            {"project": "SYNTHETIC-ECC", "file": "synthetic/rsa.py", "line": 9, "primitive": "RSA",
             "modulus_bits": 2048},
            {"project": "SYNTHETIC-ECC", "file": "synthetic/aes.py", "line": 3, "primitive": "AES-256"},
        ]
        self.mapped = qm.map_findings(mixed)

    def test_routing_is_per_finding_in_a_mixed_list(self):
        algos = [m["quantum_algorithm"] for m in self.mapped]
        self.assertEqual(algos, [qm.SHOR, qm.SHOR, qm.SHOR, qm.GROVER])

    def test_summary_counts_each_primitive_separately(self):
        counts = {}
        for m in self.mapped:
            counts[m["canonical_primitive"]] = counts.get(m["canonical_primitive"], 0) + 1
        self.assertEqual(counts, {"ECC": 2, "RSA": 1, "AES": 1})

    def test_report_lists_ecc_beside_other_primitives(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.md")
            qm.generate_mapping_report(self.mapped, path)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        self.assertIn("| ECC |", text)
        self.assertIn("| RSA |", text)
        self.assertIn("| AES |", text)

    def test_ecc_override_is_not_needed_and_does_not_break_validation(self):
        self.assertEqual(qm.validate_findings(SYNTHETIC), [])


if __name__ == "__main__":
    unittest.main()
