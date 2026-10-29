"""Week 3 Day 4: functional equivalence for the video migration (same message in, same message out)."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import hybrid, video_pqc


def make_frames(seed=0, count=20, size=4000):
    return [random.Random(seed * 1000 + i).randbytes(size) for i in range(count)]


class TestVideoEquivalence(unittest.TestCase):
    def test_same_message_in_same_message_out(self):
        for length in (0, 1, 14, 256, 1000):
            msg = random.Random(length).randbytes(length)
            with self.subTest(length=length):
                pk, sk = hybrid.generate_keypair()                 # fresh keys each time
                stego = video_pqc.hide_message(pk, msg, make_frames(length))
                self.assertEqual(video_pqc.reveal_message(sk, stego), msg)

    def test_two_embeddings_differ_but_decrypt_to_the_same_message(self):
        pk, sk = hybrid.generate_keypair()
        msg = b"same message, two embeddings"
        frames = make_frames(7)
        a = video_pqc.hide_message(pk, msg, frames)
        b = video_pqc.hide_message(pk, msg, frames)
        self.assertNotEqual(a, b)                                   # fresh KEM randomness and nonce each time
        self.assertEqual(video_pqc.reveal_message(sk, a), msg)
        self.assertEqual(video_pqc.reveal_message(sk, b), msg)

    def test_wrong_key_does_not_return_the_message(self):
        pk, _ = hybrid.generate_keypair()
        _, other_sk = hybrid.generate_keypair()
        msg = b"only the right key reads this"
        stego = video_pqc.hide_message(pk, msg, make_frames(3))
        try:
            out = video_pqc.reveal_message(other_sk, stego)
        except Exception:
            return
        self.assertNotEqual(out, msg)


if __name__ == "__main__":
    unittest.main()
