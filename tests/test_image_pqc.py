import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import hybrid, image_pqc

COVER = random.Random(1).randbytes(20000)  # fixed seed: same cover every run


class TestImagePqc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pk, cls.sk = hybrid.generate_keypair()
        cls.pk2, cls.sk2 = hybrid.generate_keypair()

    def test_round_trip_several_messages(self):
        for msg in (b"", b"hi", b"hello world" * 10, bytes(range(256))):
            with self.subTest(length=len(msg)):
                stego = image_pqc.hide_message(self.pk, msg, COVER)
                self.assertEqual(len(stego), len(COVER))
                self.assertEqual(image_pqc.reveal_message(self.sk, stego), msg)

    def test_only_lsbs_change(self):
        stego = image_pqc.hide_message(self.pk, b"lsb only", COVER)
        for a, b in zip(COVER, stego):
            self.assertLessEqual(abs(a - b), 1)

    def test_blob_extracts_without_secret_but_cannot_be_read(self):
        msg = b"top secret plaintext"
        stego = image_pqc.hide_message(self.pk, msg, COVER)
        blob = image_pqc.reveal_blob(stego)          # anyone can do this
        self.assertEqual(len(blob), len(msg) + hybrid.OVERHEAD)
        self.assertNotIn(msg, blob)                  # nothing readable, nothing to factor
        with self.assertRaises(hybrid.HybridDecryptError):
            hybrid.hybrid_decrypt(self.sk2, blob)    # wrong key fails

    def test_tamper_in_payload_region_fails(self):
        stego = bytearray(image_pqc.hide_message(self.pk, b"tamper test", COVER))
        for byte_index in (40, 2000, 8 * (4 + 1090)):   # inside KEM ct, KEM ct, nonce area
            bad = bytearray(stego)
            bad[byte_index] ^= 1
            with self.subTest(index=byte_index):
                with self.assertRaises(ValueError):
                    image_pqc.reveal_message(self.sk, bytes(bad))

    def test_tamper_in_length_header_fails(self):
        stego = bytearray(image_pqc.hide_message(self.pk, b"tamper test", COVER))
        stego[0] ^= 1
        with self.assertRaises(ValueError):
            image_pqc.reveal_message(self.sk, bytes(stego))

    def test_too_small_cover_rejected(self):
        with self.assertRaises(image_pqc.ImageCapacityError):
            image_pqc.hide_message(self.pk, b"x" * 100, COVER[:4000])

    def test_capacity_boundary(self):
        cover = COVER[:8 * (4 + 1116 + 10)]            # exactly fits a 10-byte message
        stego = image_pqc.hide_message(self.pk, b"0123456789", cover)
        self.assertEqual(image_pqc.reveal_message(self.sk, stego), b"0123456789")
        with self.assertRaises(image_pqc.ImageCapacityError):
            image_pqc.hide_message(self.pk, b"0123456789A", cover)


if __name__ == "__main__":
    unittest.main()