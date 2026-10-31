import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import parameter_sets as ps  # type: ignore # noqa: E402


class TestSizesTable(unittest.TestCase):
    def test_sizes_grow_with_the_parameter_set(self):
        for field in ("ek", "dk", "ct"):
            vals = [ps.KEM[n][field] for n in ("ML-KEM-512", "ML-KEM-768", "ML-KEM-1024")]
            self.assertEqual(vals, sorted(vals))
        for field in ("pk", "sk", "sig"):
            vals = [ps.DSA[n][field] for n in ("ML-DSA-44", "ML-DSA-65", "ML-DSA-87")]
            self.assertEqual(vals, sorted(vals))

    def test_plan_table_values(self):
        self.assertEqual((ps.KEM["ML-KEM-768"]["ek"], ps.KEM["ML-KEM-768"]["ct"]), (1184, 1088))
        self.assertEqual((ps.KEM["ML-KEM-512"]["ek"], ps.KEM["ML-KEM-512"]["ct"]), (800, 768))
        self.assertEqual((ps.KEM["ML-KEM-1024"]["ek"], ps.KEM["ML-KEM-1024"]["ct"]), (1568, 1568))
        self.assertEqual((ps.DSA["ML-DSA-65"]["pk"], ps.DSA["ML-DSA-65"]["sig"]), (1952, 3309))
        self.assertEqual((ps.DSA["ML-DSA-44"]["pk"], ps.DSA["ML-DSA-44"]["sig"]), (1312, 2420))
        self.assertEqual((ps.DSA["ML-DSA-87"]["pk"], ps.DSA["ML-DSA-87"]["sig"]), (2592, 4627))

    def test_shared_secret_is_32_bytes(self):
        self.assertTrue(all(p["ss"] == 32 for p in ps.KEM.values()))

    def test_pairings_match_security_categories(self):
        cats = [(ps.KEM[k]["category"], ps.DSA[d]["category"]) for k, d in ps.PAIRINGS]
        self.assertEqual(cats, [(1, 2), (3, 3), (5, 5)])

    def test_verification_flag_is_a_boolean(self):
        self.assertIsInstance(ps.VERIFIED_AGAINST_STANDARDS, bool)


class TestOverhead(unittest.TestCase):
    def test_overhead_values(self):
        self.assertEqual(ps.payload_overhead("ML-KEM-512"), 796)
        self.assertEqual(ps.payload_overhead("ML-KEM-768"), 1116)
        self.assertEqual(ps.payload_overhead("ML-KEM-1024"), 1596)
        self.assertEqual(ps.payload_overhead("ML-KEM-768", "ML-DSA-65"), 4425)
        self.assertEqual(ps.payload_overhead("ML-KEM-512", "ML-DSA-44"), 3216)
        self.assertEqual(ps.payload_overhead("ML-KEM-1024", "ML-DSA-87"), 6223)

    def test_matches_the_hybrid_review_layout(self):
        import hybrid_review as hr # type: ignore
        self.assertEqual(ps.payload_overhead("ML-KEM-768"), hr.OVERHEAD)

    def test_payload_size_adds_the_message(self):
        self.assertEqual(ps.payload_size("ML-KEM-768", 100), 1216)
        self.assertEqual(ps.payload_size("ML-KEM-768", 0), 1116)

    def test_invalid(self):
        for args in (("ML-KEM-999",), ("ML-KEM-768", "ML-DSA-1")):
            with self.assertRaises(ValueError):
                ps.payload_overhead(*args)
        for bad in (-1, 1.5, "10", True):
            with self.assertRaises(ValueError):
                ps.payload_size("ML-KEM-768", bad)


class TestCapacity(unittest.TestCase):
    def test_capacity_bits(self):
        self.assertEqual(ps.capacity_bits(256, 256), 196608)
        self.assertEqual(ps.capacity_bits(10, 10, channels=1, bits_per_channel=2), 200)

    def test_min_square_side_fits_and_is_minimal(self):
        for payload in (0, 1, 896, 1216, 4525, 6323):
            s = ps.min_square_side(payload)
            self.assertGreaterEqual(s * s * 3, payload * 8)
            if s > 1:
                self.assertLess((s - 1) * (s - 1) * 3, payload * 8)

    def test_min_square_side_known_values(self):
        self.assertEqual(ps.min_square_side(1216), 57)
        self.assertEqual(ps.min_square_side(4525), 110)

    def test_frames_needed_with_header(self):
        # 128x128x3 = 49152 bits per frame, 49136 usable
        self.assertEqual(ps.frames_needed(6000, 128, 128), 1)
        self.assertEqual(ps.frames_needed(6323, 128, 128), 2)
        self.assertEqual(ps.frames_needed(0, 128, 128), 1)

    def test_frames_needed_header_can_matter(self):
        # exactly one frame's raw capacity needs two frames once the header is counted
        self.assertEqual(ps.frames_needed(49152 // 8, 128, 128), 2)

    def test_tiny_frame_rejected(self):
        with self.assertRaises(ValueError):
            ps.frames_needed(10, 2, 2, header_bits=16)

    def test_embedding_rate(self):
        self.assertAlmostEqual(ps.embedding_rate(1216, ps.capacity_bits(256, 256)), 0.0495, places=3)
        self.assertGreater(ps.embedding_rate(4525, 196608), ps.embedding_rate(1216, 196608))
        with self.assertRaises(ValueError):
            ps.embedding_rate(10, 0)

    def test_signing_always_costs_capacity(self):
        for kem, dsa in ps.PAIRINGS:
            self.assertGreater(ps.payload_size(kem, 100, dsa), ps.payload_size(kem, 100))


class TestLibrarySizes(unittest.TestCase):
    def test_compare_detects_a_difference(self):
        self.assertEqual(ps.compare_with_table({"ML-KEM-768": {"ct": 1088, "ek": 1184}}), [])
        self.assertEqual(ps.compare_with_table({"ML-KEM-768": {"ct": 1000}}), [("ML-KEM-768", "ct", 1088, 1000)])

    def test_installed_libraries_match_the_table(self):
        sizes, errors = ps.measure_library_sizes()
        if errors and not sizes:
            self.skipTest("kyber-py / dilithium-py not importable: " + "; ".join(errors))
        self.assertEqual(ps.compare_with_table(sizes), [])


if __name__ == "__main__":
    unittest.main()