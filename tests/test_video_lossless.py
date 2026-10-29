"""Week 3 Day 2: video round trip through a lossless container, plus a lossy-codec negative control.

Frames are written to disk as raw bytes (lossless by definition) and read back before extraction.
Classical code only; no quantum content.
"""
import random
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import hybrid, video_pqc

FRAMES = [random.Random(i).randbytes(4000) for i in range(20)]   # 500 B capacity per frame


def write_frames(folder, frames):
    paths = []
    for i, frame in enumerate(frames):
        p = Path(folder) / f"frame_{i:04d}.bin"
        with open(p, "wb") as fh:
            fh.write(frame)
        paths.append(p)
    return paths


def read_frames(paths):
    out = []
    for p in paths:
        with open(p, "rb") as fh:
            out.append(fh.read())
    return out


def flip_lsb(frames, frame_index, byte_index):
    out = [bytearray(f) for f in frames]
    out[frame_index][byte_index] ^= 1
    return [bytes(f) for f in out]


class TestVideoLossless(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pk, cls.sk = hybrid.generate_keypair()

    def assert_not_recovered(self, frames, msg):
        """Failing loudly is the expected outcome; returning the message would be the bug."""
        try:
            out = video_pqc.reveal_message(self.sk, frames)
        except Exception:
            return
        self.assertNotEqual(out, msg)

    def test_round_trip_through_lossless_files(self):
        for msg in (b"lossless round trip", bytes(range(256)) * 4):
            with self.subTest(length=len(msg)), tempfile.TemporaryDirectory() as d:
                stego = video_pqc.hide_message(self.pk, msg, FRAMES)
                back = read_frames(write_frames(d, stego))
                self.assertEqual(back, stego)                       # container is byte-identical
                self.assertEqual(video_pqc.reveal_message(self.sk, back), msg)

    def test_lossy_codec_simulation_destroys_the_payload(self):
        msg = b"lossy codecs destroy LSB data"
        stego = video_pqc.hide_message(self.pk, msg, FRAMES)
        smoothed = [bytes(b & 0xFE for b in f) for f in stego]      # clears every LSB, as a lossy codec may
        self.assert_not_recovered(smoothed, msg)

    def test_one_flipped_bit_after_storage_fails(self):
        msg = b"x" * 100
        with tempfile.TemporaryDirectory() as d:
            stego = video_pqc.hide_message(self.pk, msg, FRAMES)
            back = read_frames(write_frames(d, stego))
        self.assert_not_recovered(flip_lsb(back, 0, 100), msg)


if __name__ == "__main__":
    unittest.main()
