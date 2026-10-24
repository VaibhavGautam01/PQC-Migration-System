import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import hybrid, video_pqc

FRAMES = [random.Random(i).randbytes(4000) for i in range(20)]  # 500 B capacity per frame


def flip_lsb(frames, frame_index, byte_index):
    out = [bytes(f) for f in frames]
    f = bytearray(out[frame_index])
    f[byte_index] ^= 1
    out[frame_index] = bytes(f)
    return out


class TestVideoPqc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pk, cls.sk = hybrid.generate_keypair()
        cls.pk2, cls.sk2 = hybrid.generate_keypair()

    def test_round_trip_several_messages(self):
        for msg in (b"", b"hi", b"hello world" * 10, bytes(range(256))):
            with self.subTest(length=len(msg)):
                stego = video_pqc.hide_message(self.pk, msg, FRAMES)
                self.assertEqual(len(stego), len(FRAMES))
                self.assertEqual(video_pqc.reveal_message(self.sk, stego), msg)

    def test_payload_spans_several_frames_and_untouched_frames_are_identical(self):
        stego = video_pqc.hide_message(self.pk, b"x" * 100, FRAMES)   # 1221 B payload, 500 B per frame
        changed = [i for i, (a, b) in enumerate(zip(FRAMES, stego)) if a != b]
        self.assertEqual(changed, [0, 1, 2])
        for i in range(3, len(FRAMES)):
            self.assertEqual(FRAMES[i], stego[i])

    def test_only_lsbs_change(self):
        stego = video_pqc.hide_message(self.pk, b"lsb only", FRAMES)
        for a, b in zip(FRAMES, stego):
            for x, y in zip(a, b):
                self.assertLessEqual(abs(x - y), 1)

    def test_blob_readable_without_secret_but_not_decryptable(self):
        msg = b"top secret plaintext"
        stego = video_pqc.hide_message(self.pk, msg, FRAMES)
        flag, body = video_pqc.reveal_body(stego)                  # anyone can do this
        self.assertEqual(flag, video_pqc.FLAG_PLAIN)
        self.assertEqual(len(body), len(msg) + hybrid.OVERHEAD)
        self.assertNotIn(msg, body)
        with self.assertRaises(ValueError):
            video_pqc.reveal_message(self.sk2, stego)              # wrong key

    def test_tamper_in_each_used_frame_fails(self):
        stego = video_pqc.hide_message(self.pk, b"x" * 100, FRAMES)
        for frame_index, byte_index in ((0, 100), (1, 1000), (2, 1000)):
            with self.subTest(frame=frame_index):
                with self.assertRaises(ValueError):
                    video_pqc.reveal_message(self.sk, flip_lsb(stego, frame_index, byte_index))

    def test_tamper_in_header_fails(self):
        stego = video_pqc.hide_message(self.pk, b"header test", FRAMES)
        for byte_index in (0, 39):      # flag bit, last length bit
            with self.subTest(byte=byte_index):
                with self.assertRaises(ValueError):
                    video_pqc.reveal_message(self.sk, flip_lsb(stego, 0, byte_index))

    def test_capacity_error(self):
        with self.assertRaises(video_pqc.VideoCapacityError):
            video_pqc.hide_message(self.pk, b"0123456789", FRAMES[:2])

    def test_custom_frame_order(self):
        order = random.Random(5).sample(range(len(FRAMES)), len(FRAMES))
        stego = video_pqc.hide_message(self.pk, b"ordered", FRAMES, order=order)
        self.assertEqual(video_pqc.reveal_message(self.sk, stego, order=order), b"ordered")
        with self.assertRaises(ValueError):        # reading in the wrong order never succeeds
            video_pqc.reveal_message(self.sk, stego)

    def test_bad_order_rejected(self):
        with self.assertRaises(ValueError):
            video_pqc.hide_message(self.pk, b"x", FRAMES, order=[0, 0, 1])


if __name__ == "__main__":
    unittest.main()