import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import hybrid, privacy_amp, qkd_hybrid


class TestPrivacyAmp(unittest.TestCase):
    def test_length_and_determinism(self):
        r = random.Random(1)
        bits = [r.getrandbits(1) for _ in range(100)]
        seed = [r.getrandbits(1) for _ in range(100 + 32 - 1)]
        out = privacy_amp.toeplitz_hash(bits, seed, 32)
        self.assertEqual(len(out), 32)
        self.assertEqual(out, privacy_amp.toeplitz_hash(bits, seed, 32))

    def test_linear_over_gf2(self):
        r = random.Random(2)
        x = [r.getrandbits(1) for _ in range(80)]
        y = [r.getrandbits(1) for _ in range(80)]
        seed = [r.getrandbits(1) for _ in range(80 + 24 - 1)]
        xy = [a ^ b for a, b in zip(x, y)]
        hx, hy, hxy = (privacy_amp.toeplitz_hash(v, seed, 24) for v in (x, y, xy))
        self.assertEqual(hxy, [a ^ b for a, b in zip(hx, hy)])

    def test_different_seed_changes_output(self):
        r = random.Random(3)
        bits = [r.getrandbits(1) for _ in range(64)]
        s1 = [r.getrandbits(1) for _ in range(64 + 16 - 1)]
        s2 = [r.getrandbits(1) for _ in range(64 + 16 - 1)]
        self.assertNotEqual(privacy_amp.toeplitz_hash(bits, s1, 16), privacy_amp.toeplitz_hash(bits, s2, 16))

    def test_bad_seed_length_rejected(self):
        with self.assertRaises(ValueError):
            privacy_amp.toeplitz_hash([0] * 10, [0] * 5, 4)

    def test_bits_to_bytes(self):
        self.assertEqual(privacy_amp.bits_to_bytes([1, 0, 0, 0, 0, 0, 0, 1]), b"\x81")
        with self.assertRaises(ValueError):
            privacy_amp.bits_to_bytes([1, 0, 1])


class TestQkdHybrid(unittest.TestCase):
    KEY = bytes(range(32))

    def test_round_trip_and_overhead(self):
        blob = qkd_hybrid.qkd_encrypt(self.KEY, b"hello qkd")
        self.assertEqual(len(blob), len(b"hello qkd") + 28)
        self.assertEqual(qkd_hybrid.qkd_decrypt(self.KEY, blob), b"hello qkd")

    def test_tamper_and_wrong_key_fail(self):
        blob = bytearray(qkd_hybrid.qkd_encrypt(self.KEY, b"hello qkd"))
        blob[-1] ^= 1
        with self.assertRaises(hybrid.HybridDecryptError):
            qkd_hybrid.qkd_decrypt(self.KEY, bytes(blob))
        with self.assertRaises(hybrid.HybridDecryptError):
            qkd_hybrid.qkd_decrypt(bytes(32), qkd_hybrid.qkd_encrypt(self.KEY, b"x"))

    def test_key_length_enforced(self):
        with self.assertRaises(ValueError):
            qkd_hybrid.qkd_encrypt(b"short", b"x")


if __name__ == "__main__":
    unittest.main()