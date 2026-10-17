"""Functional equivalence: the same message goes in and the same message comes out."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import hybrid, image_pqc

COVER = random.Random(7).randbytes(30000)


class TestEquivalence(unittest.TestCase):
    def test_same_message_in_same_message_out(self):
        pk, sk = hybrid.generate_keypair()
        rng = random.Random(3)
        messages = [b"", b"A", "unicode: caf\u00e9".encode("utf-8"), bytes(range(256)), rng.randbytes(500)]
        for msg in messages:
            with self.subTest(length=len(msg)):
                stego = image_pqc.hide_message(pk, msg, COVER)
                self.assertEqual(image_pqc.reveal_message(sk, stego), msg)

    def test_fresh_keys_each_time(self):
        msg = b"same message, different keys"
        for _ in range(3):
            pk, sk = hybrid.generate_keypair()
            self.assertEqual(image_pqc.reveal_message(sk, image_pqc.hide_message(pk, msg, COVER)), msg)


if __name__ == "__main__":
    unittest.main()