"""Tests that symmetric and hash findings route to Grover's, never Shor's (Issue #5).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import quantum_mapper as qm  # noqa: E402


class TestGroverRouting(unittest.TestCase):
    AES_NAMES = ["AES", "AES-128", "AES-192", "AES-256", "AES128", "aes_256_gcm",
                 "AES-128-CBC", "AESGCM"]
    SHA_NAMES = ["SHA", "SHA1", "SHA-1", "SHA-224", "SHA-256", "SHA-384", "SHA-512",
                 "SHA3-256", "SHA3-512", "SHAKE128", "HMAC-SHA256", "HMAC_SHA512"]

    def test_aes_variants_route_to_grover(self):
        for name in self.AES_NAMES:
            with self.subTest(name=name):
                self.assertEqual(qm.route_algorithm(name), qm.GROVER)
                self.assertEqual(qm.map_finding({"primitive": name})["canonical_primitive"], "AES")

    def test_sha_variants_route_to_grover(self):
        for name in self.SHA_NAMES:
            with self.subTest(name=name):
                self.assertEqual(qm.route_algorithm(name), qm.GROVER)
                self.assertEqual(qm.map_finding({"primitive": name})["canonical_primitive"], "SHA")

    def test_symmetric_never_routes_to_shor(self):
        for name in self.AES_NAMES + self.SHA_NAMES:
            with self.subTest(name=name):
                self.assertNotEqual(qm.route_algorithm(name), qm.SHOR)

    def test_asymmetric_never_routes_to_grover(self):
        for name in ("RSA", "ECDSA", "ECDH", "DSA", "DH", "Ed25519"):
            with self.subTest(name=name):
                self.assertEqual(qm.route_algorithm(name), qm.SHOR)

    def test_unknown_primitive_has_no_route(self):
        self.assertIsNone(qm.route_algorithm("Blowfish"))
        self.assertIsNone(qm.route_algorithm("HMAC-MD5"))

    def test_table_is_consistent_with_routing_rule(self):
        for name, entry in qm.PRIMITIVE_TABLE.items():
            with self.subTest(name=name):
                self.assertEqual(entry["quantum_algorithm"],
                                 qm.FAMILY_TO_ALGORITHM[entry["family"]])

    def test_grover_halves_key_bits(self):
        expected = {"AES-128": 64, "AES-192": 96, "AES-256": 128,
                    "SHA-256": 128, "SHA-384": 192, "SHA-512": 256}
        for name, bits in expected.items():
            with self.subTest(name=name):
                self.assertEqual(qm.map_finding({"primitive": name})["post_quantum_security_bits"], bits)

    def test_grover_is_not_a_full_break(self):
        for name in ("AES-128", "AES-256", "SHA-256"):
            with self.subTest(name=name):
                r = qm.map_finding({"primitive": name})
                self.assertEqual(r["impact"], "WEAKENED")
                self.assertGreater(r["post_quantum_security_bits"], 0)


class TestGroverAssessment(unittest.TestCase):
    def test_not_applicable_to_asymmetric(self):
        self.assertIsNone(qm.grover_assessment("RSA", 2048))
        self.assertIsNone(qm.map_finding({"primitive": "RSA", "key_size": 2048})["grover_assessment"])

    def test_aes256_has_comfortable_margin(self):
        text = qm.map_finding({"primitive": "AES-256"})["grover_assessment"]
        self.assertIn("128-bit", text)
        self.assertIn("comfortable", text)

    def test_aes128_is_reduced_margin_not_a_break(self):
        text = qm.map_finding({"primitive": "AES-128"})["grover_assessment"]
        self.assertIn("64-bit", text)
        self.assertIn("not a break", text)

    def test_sha1_mentions_classical_weakness(self):
        text = qm.map_finding({"primitive": "SHA-1"})["grover_assessment"]
        self.assertIn("80-bit", text)
        self.assertIn("SHA-1", text)

    def test_unknown_size_is_reported_honestly(self):
        text = qm.map_finding({"primitive": "AES"})["grover_assessment"]
        self.assertIn("Size unknown", text)

    def test_unknown_primitive_has_key_but_no_assessment(self):
        r = qm.map_finding({"primitive": "Blowfish"})
        self.assertIn("grover_assessment", r)
        self.assertIsNone(r["grover_assessment"])


if __name__ == "__main__":
    unittest.main()
