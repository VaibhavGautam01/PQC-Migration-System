"""Primitive-name coverage and legacy ciphers (review notes from Vaibhav).

Names such as RSA-2048, P256, ED448 and 3DES must be recognised, and legacy
ciphers must map to Grover's as 'weak classically', not 'manual review'.

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import quantum_mapper as qm  # noqa: E402


class TestNamesAreRecognised(unittest.TestCase):
    CASES = {
        "RSA": ["RSA", "RSA-2048", "RSA2048", "RSA-OAEP", "rsa_pss"],
        "ECC": ["P256", "P-256", "P384", "P-521", "secp256r1", "secp256k1", "prime256v1",
                "brainpoolP256r1", "ED448", "X448", "Ed25519", "ECDSA-P256", "ECDHE", "ECDH"],
        "DH": ["DH", "DHE", "FFDHE2048", "Diffie-Hellman"],
        "DSA": ["DSA", "DSA-2048"],
        "AES": ["AES", "AES-256-GCM", "aes_128_cbc"],
        "SHA": ["SHA", "SHA-1", "SHA-256", "SHA3-512", "SHAKE128", "HMAC-SHA256"],
        "3DES": ["3DES", "TripleDES", "TDES", "DES3", "DESede", "DES-EDE3", "3DES-CBC"],
        "DES": ["DES", "DES-CBC", "DES-ECB"],
        "RC4": ["RC4", "ARCFOUR"],
        "BLOWFISH": ["Blowfish", "blowfish-cbc"],
    }

    def test_all_names_map_to_the_expected_primitive(self):
        for expected, names in self.CASES.items():
            for name in names:
                with self.subTest(name=name):
                    self.assertEqual(qm.canonical_primitive(name), expected)

    def test_look_alike_names_are_not_matched(self):
        for name in ("ROT13", "", "Twofish", "SHAPE", "DESCRIPTOR", "HMAC-MD5", "MD5"):
            with self.subTest(name=name):
                self.assertIsNone(qm.canonical_primitive(name))

    def test_unrecognised_names_still_become_unknown(self):
        r = qm.map_finding({"primitive": "ROT13"})
        self.assertEqual(r["impact"], "UNKNOWN")
        self.assertIsNone(r["classically_weak"])


class TestSizesFromNames(unittest.TestCase):
    def test_sizes(self):
        cases = {"RSA-2048": 2048, "RSA-4096": 4096, "DSA-2048": 2048, "FFDHE3072": 3072,
                 "P256": 256, "P-384": 384, "P521": 521, "ED448": 448, "Ed25519": 256,
                 "secp256r1": 256, "AES-128": 128, "SHA3-512": 512, "HMAC-SHA256": 256,
                 "Blowfish-448": 448}
        for name, bits in cases.items():
            with self.subTest(name=name):
                self.assertEqual(qm.map_finding({"primitive": name})["size_used_bits"], bits)

    def test_name_size_does_not_trigger_the_prime_size_warning(self):
        self.assertIsNone(qm.map_finding({"primitive": "RSA-2048"})["size_warning"])

    def test_explicit_modulus_bits_still_beats_the_name(self):
        r = qm.map_finding({"primitive": "RSA-2048", "modulus_bits": 256})
        self.assertEqual(r["size_used_bits"], 256)

    def test_bare_names_have_no_size(self):
        for name in ("RSA", "DES", "RC4", "3DES"):
            with self.subTest(name=name):
                self.assertIsNone(qm.map_finding({"primitive": name})["size_used_bits"])


class TestLegacyCiphers(unittest.TestCase):
    def test_all_legacy_ciphers_route_to_grover_and_are_classically_weak(self):
        for name in ("3DES", "DES", "RC4", "Blowfish"):
            with self.subTest(name=name):
                r = qm.map_finding({"primitive": name})
                self.assertEqual(r["quantum_algorithm"], qm.GROVER)
                self.assertEqual(r["impact"], "WEAKENED")
                self.assertTrue(r["classically_weak"])
                self.assertIn("AES-256", r["pqc_replacement"])
                self.assertIn("already weak classically", r["grover_assessment"])

    def test_fixed_effective_strength_overrides_the_key_size(self):
        self.assertEqual(qm.map_finding({"primitive": "DES"})["post_quantum_security_bits"], 28)
        self.assertEqual(qm.map_finding({"primitive": "3DES"})["post_quantum_security_bits"], 56)
        # a scanner key_size of 168 (3 x 56 + parity) must not give 84
        r = qm.map_finding({"primitive": "3DES", "key_size": 168})
        self.assertEqual(r["post_quantum_security_bits"], 56)
        self.assertEqual(r["size_used_bits"], 168)

    def test_size_dependent_legacy_ciphers(self):
        self.assertIsNone(qm.map_finding({"primitive": "RC4"})["post_quantum_security_bits"])
        self.assertEqual(qm.map_finding({"primitive": "Blowfish", "key_size": 128})["post_quantum_security_bits"], 64)

    def test_modern_primitives_are_not_marked_classically_weak(self):
        for name in ("RSA", "AES-256", "SHA-256", "ECDSA"):
            with self.subTest(name=name):
                self.assertFalse(qm.map_finding({"primitive": name})["classically_weak"])

    def test_legacy_ciphers_are_never_routed_to_shor(self):
        for name in qm.LEGACY_CIPHERS:
            self.assertEqual(qm.route_algorithm(name), qm.GROVER)

    def test_table_stays_consistent_with_the_routing_rule(self):
        for name, entry in qm.PRIMITIVE_TABLE.items():
            self.assertEqual(entry["quantum_algorithm"], qm.FAMILY_TO_ALGORITHM[entry["family"]], name)


if __name__ == "__main__":
    unittest.main()
