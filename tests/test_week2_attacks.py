"""
Tests for the Week 2 attack and steganalysis scripts:
  extras/attack_pqc_image.py     attack on the PQC image variant (Day 3)
  extras/steganalysis_pqc.py     RSA payload vs PQC payload detectors (Day 4)
  src/q1_demo_batch.py           repeated Shor runs for data/demo_results.json (Day 2, slow)

Fast tests:  python -m unittest tests.test_week2_attacks -v
Slow test:   set RUN_SLOW=1   (Command Prompt) then the same command
The attack/steganalysis tests need the PQC libraries (kyber-py, pycryptodome) and Pillow; they
are skipped with a message if those are missing.
"""
import importlib.util
import os
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
HAS_PQC = all(importlib.util.find_spec(m) for m in ("kyber_py", "Crypto", "PIL"))
HAS_QISKIT = importlib.util.find_spec("qiskit") is not None and \
    importlib.util.find_spec("qiskit_aer") is not None
SLOW = os.environ.get("RUN_SLOW") == "1" or os.environ.get("SLOW_TESTS") == "1"


def load_script(name, relpath):
    """Import a script from extras/ (a folder that is not a Python package) by file path."""
    spec = importlib.util.spec_from_file_location(name, str(ROOT / relpath))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAS_PQC, "kyber-py / pycryptodome / Pillow not installed")
class AttackOnPqcImage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atk = load_script("attack_pqc_image", "extras/attack_pqc_image.py")

    def test_every_check_passes_with_the_reference_embedder(self):
        checks = self.atk.run_attack(self.atk.ReferenceCarrier(), b"HELLO", 200)
        failed = [c for c in checks if not c["ok"]]
        self.assertEqual(failed, [])

    def test_the_attack_covers_extraction_wrong_key_and_tampering(self):
        checks = self.atk.run_attack(self.atk.ReferenceCarrier(), b"HELLO", 200)
        names = " | ".join(c["check"] for c in checks)
        for needle in ("without any secret", "wrong secret key", "length header", "GCM tag",
                       "nonce", "KEM ciphertext", "OUTSIDE the payload"):
            self.assertIn(needle, names)

    def test_longer_message_also_tests_the_aes_part(self):
        checks = self.atk.run_attack(self.atk.ReferenceCarrier(), b"a longer message " * 3, 200)
        self.assertTrue(all(c["ok"] for c in checks))
        self.assertTrue(any("AES ciphertext" in c["check"] for c in checks))


@unittest.skipUnless(HAS_PQC, "kyber-py / pycryptodome / Pillow not installed")
class SteganalysisPqc(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.st = load_script("steganalysis_pqc", "extras/steganalysis_pqc.py")

    def test_textbook_rsa_round_trip(self):
        n, e, d = self.st.make_textbook_rsa(128)
        hex_str = self.st.rsa_hex_payload(b"HELLO", n, e)
        width = (n.bit_length() + 3) // 4
        blocks = [int(hex_str[i:i + width], 16) for i in range(0, len(hex_str), width)]
        self.assertEqual(bytes(pow(c, d, n) for c in blocks), b"HELLO")

    def test_rsa_payload_grows_per_character(self):
        n, e, _ = self.st.make_textbook_rsa(256)
        small = len(self.st.rsa_hex_payload(b"A" * 5, n, e))
        large = len(self.st.rsa_hex_payload(b"A" * 50, n, e))
        self.assertEqual(large, 10 * small)

    def test_embedding_round_trip_and_only_lsbs_change(self):
        cover = np.random.default_rng(1).integers(0, 256, 4000, dtype=np.uint8)
        data = b"deadbeef" * 20
        stego = self.st.embed_bytes(cover, data)
        self.assertEqual(self.st.lsb_stream_bytes(stego, len(data)), data)
        self.assertLessEqual(int(np.abs(cover.astype(int) - stego.astype(int)).max()), 1)

    def test_embedding_rejects_a_payload_that_does_not_fit(self):
        with self.assertRaises(ValueError):
            self.st.embed_bytes(np.zeros(100, dtype=np.uint8), b"x" * 20)

    def test_hex_header_detector(self):
        cover = np.random.default_rng(2).integers(0, 256, 8000, dtype=np.uint8)
        hex_stego = self.st.embed_bytes(cover, b"0123456789abcdef" * 10)
        self.assertTrue(self.st.hex_header_found(hex_stego))
        self.assertFalse(self.st.hex_header_found(cover))

    def test_length_header_detector(self):
        from pqc_stego import hybrid
        cover = np.random.default_rng(3).integers(0, 256, 40000, dtype=np.uint8)
        import struct
        data = struct.pack(">I", hybrid.OVERHEAD + 10) + os.urandom(hybrid.OVERHEAD + 10)
        self.assertTrue(self.st.length_header_plausible(self.st.embed_bytes(cover, data)))
        self.assertFalse(self.st.length_header_plausible(cover))

    def test_ones_fraction(self):
        v = np.array([0, 1, 2, 3, 4, 5, 6, 7], dtype=np.uint8)
        self.assertEqual(self.st.ones_fraction(v), 0.5)

    def test_chi_square_pair_test_separates_equalised_from_skewed(self):
        rng = np.random.default_rng(4)
        equalised = np.repeat(np.arange(256), 400).astype(np.uint8)       # every pair exactly equal
        rng.shuffle(equalised)
        skewed = np.concatenate([np.full(5000, 2 * k, np.uint8) for k in range(128)])  # only even values
        self.assertGreater(self.st.chi_square_pair_p(equalised), 0.99)
        self.assertLess(self.st.chi_square_pair_p(skewed), 1e-6)

    def test_crossover_length_matches_the_size_formulas(self):
        from pqc_stego import hybrid
        L = self.st.crossover_length(1024)
        rsa = lambda n: 128 * n                                     # bytes of RSA ciphertext
        pqc = lambda n: 4 + hybrid.OVERHEAD + n                     # raw hybrid payload bytes
        self.assertGreater(pqc(int(L) - 1), rsa(int(L) - 1))
        self.assertLess(pqc(int(L) + 2), rsa(int(L) + 2))

    def test_experiment_reports_the_size_difference(self):
        cover = self.st.synthetic_cover(256)
        rows, meta = self.st.run_experiment(cover, [5, 40], 512)
        by = {(r["message_chars"], r["payload"]): r for r in rows if r["payload"] != "clean cover"}
        self.assertGreater(by[(5, "PQC raw")]["payload_bytes"], by[(5, "RSA hex")]["payload_bytes"] // 4)
        self.assertLess(by[(40, "PQC raw")]["payload_bytes"], by[(40, "RSA hex")]["payload_bytes"])


@unittest.skipUnless(HAS_QISKIT and SLOW, "slow quantum test: install qiskit and set RUN_SLOW=1")
class DemoBatch(unittest.TestCase):
    def test_repeats_find_the_factors_and_match_theory(self):
        from src.q1_demo_batch import run_case
        case = run_case(7, 15, repeats=3, shots=1024)
        self.assertEqual(case["repeats_finding_factors"], 3)
        self.assertEqual(case["factors_found_in_repeats"], {"3x5": 3})
        self.assertGreater(case["pooled_chi_square"]["p_value"], 0.001)
        self.assertEqual([r["seed"] for r in case["runs"]], [12345, 12346, 12347])


if __name__ == "__main__":
    unittest.main()
