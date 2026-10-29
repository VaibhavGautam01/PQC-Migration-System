import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import hybrid


class TestHkdf(unittest.TestCase):
    def test_rfc5869_case_1(self):
        okm = hybrid.hkdf_sha256(
            bytes([0x0b] * 22), 42,
            salt=bytes(range(0x00, 0x0d)), info=bytes(range(0xf0, 0xfa)))
        self.assertEqual(okm.hex(),
            "3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf"
            "34007208d5b887185865")


class TestHybrid(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pk, cls.sk = hybrid.generate_keypair()
        cls.pk2, cls.sk2 = hybrid.generate_keypair()

    def test_round_trip(self):
        msg = b"attack at dawn"
        blob = hybrid.hybrid_encrypt(self.pk, msg)
        self.assertEqual(hybrid.hybrid_decrypt(self.sk, blob), msg)

    def test_empty_message(self):
        blob = hybrid.hybrid_encrypt(self.pk, b"")
        self.assertEqual(hybrid.hybrid_decrypt(self.sk, blob), b"")

    def test_overhead_is_1116(self):
        msg = b"x" * 100
        self.assertEqual(len(hybrid.hybrid_encrypt(self.pk, msg)), 100 + 1116)

    def test_two_encryptions_differ(self):
        msg = b"same message"
        self.assertNotEqual(hybrid.hybrid_encrypt(self.pk, msg),
                            hybrid.hybrid_encrypt(self.pk, msg))

    def test_tamper_every_region(self):
        blob = hybrid.hybrid_encrypt(self.pk, b"tamper me please")
        positions = {"kem_ct": 0, "kem_ct_end": 1087, "nonce": 1088,
                     "tag": 1100, "ciphertext": len(blob) - 1}
        for name, pos in positions.items():
            bad = bytearray(blob)
            bad[pos] ^= 0x01
            with self.subTest(region=name):
                with self.assertRaises(hybrid.HybridDecryptError):
                    hybrid.hybrid_decrypt(self.sk, bytes(bad))

    def test_wrong_key_fails(self):
        blob = hybrid.hybrid_encrypt(self.pk, b"secret")
        with self.assertRaises(hybrid.HybridDecryptError):
            hybrid.hybrid_decrypt(self.sk2, blob)

    def test_truncated_fails(self):
        blob = hybrid.hybrid_encrypt(self.pk, b"secret")
        with self.assertRaises(hybrid.HybridDecryptError):
            hybrid.hybrid_decrypt(self.sk, blob[:500])

    def test_aad_mismatch_fails(self):
        blob = hybrid.hybrid_encrypt(self.pk, b"secret", aad=b"image")
        with self.assertRaises(hybrid.HybridDecryptError):
            hybrid.hybrid_decrypt(self.sk, blob, aad=b"video")
        self.assertEqual(hybrid.hybrid_decrypt(self.sk, blob, aad=b"image"), b"secret")


if __name__ == "__main__":
    unittest.main()