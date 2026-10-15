"""
test_migration_demo.py
----------------------
Unit tests for migration_demo.py (RSA vs ML-KEM-768 migration demo).
Run with:  python -m unittest test_migration_demo -v   (from notebook/)
or:        python run_tests.py
"""

import unittest

import migration_demo as md

HAS_KEM = md.ML_KEM_768 is not None
HAS_AES = md.AESGCM is not None
MSG = b"PQC!"


class TestPrimes(unittest.TestCase):
    def test_known_primes_and_composites(self):
        for p in (2, 3, 97, 7919, 2**61 - 1):
            self.assertTrue(md.is_probable_prime(p), p)
        for c in (0, 1, 4, 91, 7917, 561, 2**61 + 1):
            self.assertFalse(md.is_probable_prime(c), c)

    def test_random_prime_has_requested_size(self):
        p = md.random_prime(40)
        self.assertEqual(p.bit_length(), 40)
        self.assertTrue(md.is_probable_prime(p))


class TestTextbookRsa(unittest.TestCase):
    def test_key_has_requested_size_and_is_consistent(self):
        key = md.textbook_keygen(64)
        self.assertEqual(key["n"].bit_length(), 64)
        self.assertEqual(key["p"] * key["q"], key["n"])
        self.assertEqual(pow(pow(12345, key["e"], key["n"]), key["d"], key["n"]), 12345)

    def test_roundtrip(self):
        key = md.textbook_keygen(64)
        c = md.textbook_encrypt(MSG, key["n"], key["e"])
        self.assertEqual(md.textbook_decrypt(c, key["n"], key["d"], len(MSG)), MSG)

    def test_same_message_gives_same_ciphertext(self):
        key = md.textbook_keygen(64)
        self.assertEqual(md.textbook_encrypt(MSG, key["n"], key["e"]),
                         md.textbook_encrypt(MSG, key["n"], key["e"]))

    def test_message_too_long_is_rejected(self):
        key = md.textbook_keygen(32)
        with self.assertRaises(ValueError):
            md.textbook_encrypt(b"far too long for a 32-bit modulus", key["n"], key["e"])

    def test_tiny_key_size_is_rejected(self):
        with self.assertRaises(ValueError):
            md.textbook_keygen(16)

    def test_pollard_rho_finds_a_real_factor(self):
        p, q = md.random_prime(24), md.random_prime(24)
        while p == q:
            q = md.random_prime(24)
        f = md.pollard_rho(p * q)
        self.assertIn(f, (p, q))

    def test_attack_reads_the_message_from_the_public_key_only(self):
        key = md.textbook_keygen(64)
        c = md.textbook_encrypt(MSG, key["n"], key["e"])
        result = md.attack_textbook(key["n"], key["e"], c, len(MSG))
        self.assertEqual(result["plaintext"], MSG)
        self.assertEqual(sorted((result["p"], result["q"])), sorted((key["p"], key["q"])))

    def test_run_textbook_summary(self):
        r = md.run_textbook(64, MSG)
        self.assertFalse(r["randomised"])
        self.assertTrue(r["roundtrip_ok"])
        self.assertTrue(r["attack_recovered"])
        self.assertEqual(r["ciphertext_bytes"], 8)


@unittest.skipUnless(HAS_AES, "cryptography is not installed")
class TestRsaOaep(unittest.TestCase):
    def test_roundtrip_is_randomised_and_256_bytes(self):
        r = md.run_rsa_oaep(2048, MSG)
        self.assertTrue(r["roundtrip_ok"])
        self.assertTrue(r["randomised"])
        self.assertEqual(r["ciphertext_bytes"], 256)


@unittest.skipUnless(HAS_KEM and HAS_AES, "kyber-py or cryptography is not installed")
class TestMlKemHybrid(unittest.TestCase):
    def test_fips_203_sizes_for_ml_kem_768(self):
        r = md.run_ml_kem_hybrid(MSG)
        self.assertEqual(r["public_key_bytes"], 1184)
        self.assertEqual(r["private_key_bytes"], 2400)
        self.assertEqual(r["kem_ciphertext_bytes"], 1088)
        self.assertEqual(r["shared_secret_bytes"], 32)

    def test_roundtrip_and_wrong_key_failure(self):
        r = md.run_ml_kem_hybrid(MSG)
        self.assertTrue(r["roundtrip_ok"])
        self.assertTrue(r["wrong_key_secret_differs"])

    def test_wire_size_is_kem_ciphertext_plus_nonce_and_tagged_message(self):
        r = md.run_ml_kem_hybrid(MSG)
        self.assertEqual(r["ciphertext_bytes"], 1088 + 12 + len(MSG) + 16)


class TestCompare(unittest.TestCase):
    def test_returns_all_three_entries(self):
        res = md.compare(MSG, textbook_bits=48, rsa_bits=2048)
        self.assertEqual(set(res), {"textbook", "oaep", "mlkem"})
        self.assertTrue(res["textbook"]["roundtrip_ok"])

    def test_cli_returns_zero_when_everything_works(self):
        if not (HAS_KEM and HAS_AES):
            self.skipTest("optional dependencies missing")
        self.assertEqual(md.main(["--textbook-bits", "48"]), 0)


if __name__ == "__main__":
    unittest.main()
