import unittest

from pqc_stego.hybrid import (HEADER_LEN, KEM_CT_LEN, NONCE_LEN,
                              generate_keypair, hybrid_decrypt, hybrid_encrypt)


class HybridTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ek, cls.dk = generate_keypair()

    def test_round_trip(self):
        msg = b"secret message for the image project"
        self.assertEqual(hybrid_decrypt(self.dk, hybrid_encrypt(self.ek, msg)), msg)

    def test_empty_and_long_messages(self):
        for msg in (b"", b"x" * 5000):
            self.assertEqual(hybrid_decrypt(self.dk, hybrid_encrypt(self.ek, msg)), msg)

    def test_blob_size(self):
        msg = b"hello"
        self.assertEqual(len(hybrid_encrypt(self.ek, msg)), HEADER_LEN + len(msg))

    def test_two_encryptions_differ(self):
        self.assertNotEqual(hybrid_encrypt(self.ek, b"same"), hybrid_encrypt(self.ek, b"same"))

    def test_tamper_each_region_fails(self):
        blob = bytearray(hybrid_encrypt(self.ek, b"tamper test message"))
        for pos in (0, KEM_CT_LEN - 1, KEM_CT_LEN, KEM_CT_LEN + NONCE_LEN, len(blob) - 1):
            bad = bytearray(blob)
            bad[pos] ^= 0x01
            with self.assertRaises(ValueError):
                hybrid_decrypt(self.dk, bytes(bad))

    def test_wrong_key_fails(self):
        _, other_dk = generate_keypair()
        with self.assertRaises(ValueError):
            hybrid_decrypt(other_dk, hybrid_encrypt(self.ek, b"msg"))

    def test_truncated_blob_fails(self):
        with self.assertRaises(ValueError):
            hybrid_decrypt(self.dk, b"short")


if __name__ == "__main__":
    unittest.main()
