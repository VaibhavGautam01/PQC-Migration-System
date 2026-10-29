"""
Coverage and quality tests for the v2 frame-selection design
(docs/frame_select_v2_spec.md). Written before the implementation: they SKIP
until pqc_stego/frame_select_v2.py exists, then they must all pass.

Keys come from a fixed sequence, so every test is deterministic (never flaky).
Run: python -m unittest tests.test_frame_select_v2 -v
Slow tests (large videos): set SLOW_TESTS=1.
"""
import hashlib
import os
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from pqc_stego import frame_select_v2 as fs
except ImportError:           # implementation not written yet
    fs = None

SLOW = os.environ.get("SLOW_TESTS") == "1"


def key(i: int) -> bytes:
    """The i-th test key: 32 bytes, fixed and reproducible."""
    return hashlib.sha256(b"frame-select-test-key-%d" % i).digest()


def chi_square(counts, expected):
    return sum((c - expected) ** 2 / expected for c in counts)


@unittest.skipIf(fs is None, "pqc_stego/frame_select_v2.py not written yet")
class TestBasicProperties(unittest.TestCase):
    def test_indices_in_range_distinct_and_exact_count(self):
        for n, k in ((1, 1), (10, 10), (300, 40), (1000, 100), (5000, 7)):
            with self.subTest(n=n, k=k):
                sel = fs.select_frames(key(n + k), n, k)
                self.assertEqual(len(sel), k)
                self.assertEqual(len(set(sel)), k)
                self.assertTrue(all(isinstance(i, int) and 0 <= i < n for i in sel))

    def test_same_inputs_same_output(self):
        self.assertEqual(fs.select_frames(key(1), 500, 30), fs.select_frames(key(1), 500, 30))

    def test_different_keys_give_different_selections(self):
        seen = {tuple(fs.select_frames(key(i), 1000, 20)) for i in range(50)}
        self.assertEqual(len(seen), 50)

    def test_one_bit_key_change_changes_selection(self):
        k = bytearray(key(2))
        a = fs.select_frames(bytes(k), 1000, 20)
        k[0] ^= 1
        self.assertNotEqual(a, fs.select_frames(bytes(k), 1000, 20))

    def test_prefix_stable_so_extraction_can_read_frames_one_by_one(self):
        # The extractor learns the payload length from the first frames, so the
        # first j frames must not depend on how many frames are requested later.
        full = fs.select_frames(key(3), 800, 60)
        for j in (0, 1, 5, 30):
            self.assertEqual(fs.select_frames(key(3), 800, j), full[:j])

    def test_selection_depends_on_video_length(self):
        self.assertNotEqual(fs.select_frames(key(4), 500, 20), fs.select_frames(key(4), 501, 20))

    def test_all_frames_when_count_equals_total(self):
        sel = fs.select_frames(key(5), 257, 257)
        self.assertEqual(sorted(sel), list(range(257)))


@unittest.skipIf(fs is None, "pqc_stego/frame_select_v2.py not written yet")
class TestWholeVideoCoverage(unittest.TestCase):
    """The old scheme only reached frames 0 to 255. Every frame must be reachable."""

    def test_frames_beyond_255_are_reachable(self):
        hits = [i for t in range(200) for i in fs.select_frames(key(t), 1000, 20)]
        self.assertGreater(max(hits), 255)
        self.assertGreater(sum(i > 255 for i in hits) / len(hits), 0.6)   # about 74 percent expected

    def test_every_position_is_reachable_1000_frames(self):
        reached = set()
        for t in range(3000):
            reached.update(fs.select_frames(key(t), 1000, 20))
        missing = sorted(set(range(1000)) - reached)
        self.assertEqual(missing, [], f"unreachable frames: {missing[:10]}")

    def test_first_and_last_frames_reachable(self):
        for n in (300, 2000):
            reached = set()
            for t in range(1500):
                reached.update(fs.select_frames(key(t), n, 20))
            self.assertIn(0, reached)
            self.assertIn(n - 1, reached)

    @unittest.skipUnless(SLOW, "set SLOW_TESTS=1")
    def test_every_position_is_reachable_5000_frames_slow(self):
        reached = set()
        for t in range(6000):
            reached.update(fs.select_frames(key(t), 5000, 25))
        self.assertEqual(sorted(set(range(5000)) - reached), [])


@unittest.skipIf(fs is None, "pqc_stego/frame_select_v2.py not written yet")
class TestUniformity(unittest.TestCase):
    def test_every_position_equally_likely(self):
        n, k, trials = 50, 10, 4000
        counts = [0] * n
        for t in range(trials):
            for i in fs.select_frames(key(t), n, k):
                counts[i] += 1
        # expected 800 per frame, 49 degrees of freedom; 100 is about p = 1e-5
        self.assertLess(chi_square(counts, trials * k / n), 100)

    def test_first_selected_frame_is_uniform(self):
        n, trials = 20, 4000
        counts = [0] * n
        for t in range(trials):
            counts[fs.select_frames(key(t), n, 1)[0]] += 1
        self.assertLess(chi_square(counts, trials / n), 60)

    def test_uniform_for_a_range_that_does_not_divide_a_power_of_two(self):
        # guards against modulo bias: 1000 does not divide 2**64
        n, trials = 1000, 20000
        low = sum(fs.select_frames(key(t), n, 1)[0] < 500 for t in range(trials))
        self.assertLess(abs(low / trials - 0.5), 0.02)


@unittest.skipIf(fs is None, "pqc_stego/frame_select_v2.py not written yet")
class TestInputChecks(unittest.TestCase):
    def test_zero_count_gives_empty_list(self):
        self.assertEqual(fs.select_frames(key(0), 10, 0), [])

    def test_bad_arguments_are_rejected(self):
        bad = [(key(0), 0, 0), (key(0), 10, 11), (key(0), 10, -1), (key(0), -5, 1),
               (b"short", 10, 1), (key(0) + b"x", 10, 1), ("not bytes", 10, 1),
               (key(0), 10.0, 1), (key(0), 10, 1.5), (key(0), True, 1), (None, 10, 1)]
        for args in bad:
            with self.subTest(args=args[1:]):
                with self.assertRaises(ValueError):
                    fs.select_frames(*args)

    def test_generate_key_gives_32_fresh_bytes(self):
        keys = {fs.generate_key() for _ in range(20)}
        self.assertEqual(len(keys), 20)
        self.assertTrue(all(len(k) == 32 for k in keys))


@unittest.skipIf(fs is None, "pqc_stego/frame_select_v2.py not written yet")
class TestSourceHygiene(unittest.TestCase):
    def test_no_random_module_and_no_plain_sha256_of_a_passphrase(self):
        src = (ROOT / "pqc_stego" / "frame_select_v2.py").read_text(encoding="utf-8")
        self.assertNotIn("import random", src)
        self.assertNotIn("from random", src)
        self.assertIn("hmac", src)

    def test_speed_for_a_long_video(self):
        t0 = time.perf_counter()
        fs.select_frames(key(9), 200000, 2000)
        self.assertLess(time.perf_counter() - t0, 3.0)


class TestTestsAreSensitive(unittest.TestCase):
    """The checks above must be able to FAIL: run them against known-bad schemes."""

    @staticmethod
    def legacy(k, n, count):
        # the old behaviour: bytes of a SHA-256 digest used directly as frame numbers
        d = hashlib.sha256(k).digest()
        return list(dict.fromkeys(b % n if n <= 256 else b for b in d))[:count]

    def test_legacy_scheme_never_reaches_frame_256_or_higher(self):
        reached = set()
        for t in range(500):
            reached.update(self.legacy(key(t), 1000, 20))
        self.assertLessEqual(max(reached), 255)
        self.assertGreater(1000 - len(reached), 700)          # most frames unreachable

    def test_chi_square_detects_modulo_bias(self):
        n, k, trials = 50, 10, 4000
        counts = [0] * n
        for t in range(trials):
            d = hashlib.sha256(key(t)).digest()
            for b in dict.fromkeys(x % n for x in d[:k]):
                counts[b] += 1
        total = sum(counts)
        self.assertGreater(chi_square(counts, total / n), 100)


if __name__ == "__main__":
    unittest.main()