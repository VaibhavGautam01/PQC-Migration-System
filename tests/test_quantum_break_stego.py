"""
Tests for src/quantum_break_stego.py: the "break a stego image" dashboard feature.

Fast tests here cover everything EXCEPT the quantum circuit itself (extraction, RSA block
splitting, key rebuilding, decryption, the oversize-N guard) with plain RSA toy keys - no
qiskit needed. The slow test factors a real small N with the real Q1 circuit on Aer.

Run the fast tests: python -m unittest tests.test_quantum_break_stego -v
Run the slow one  : set RUN_SLOW=1   (Command Prompt) then the same command
"""
import importlib.util
import math
import os
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from src import quantum_break_stego as QB

HAS_QISKIT = importlib.util.find_spec("qiskit") is not None and \
    importlib.util.find_spec("qiskit_aer") is not None
SLOW = os.environ.get("RUN_SLOW") == "1" or os.environ.get("SLOW_TESTS") == "1"


def toy_rsa_key(p=61, q=53, e=17):
    """A tiny RSA key for tests (N = 3233, 12 bits, well under the 16-bit cap)."""
    n = p * q
    d = pow(e, -1, (p - 1) * (q - 1))
    return p, q, e, n, d


def make_cover(path, size=200, seed=1):
    Image.fromarray(np.random.default_rng(seed).integers(0, 256, (size, size, 3), dtype=np.uint8)).save(path)


class ReferenceFormatRoundTrip(unittest.TestCase):
    def test_embed_then_extract_recovers_the_exact_hex_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            cover, stego = Path(tmp) / "cover.png", Path(tmp) / "stego.png"
            make_cover(cover)
            QB.embed_reference(cover, "0123abcd" * 10, stego)
            self.assertEqual(QB.extract_reference(stego), "0123abcd" * 10)

    def test_too_long_for_the_cover_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            cover, stego = Path(tmp) / "cover.png", Path(tmp) / "stego.png"
            make_cover(cover, size=5)
            with self.assertRaises(QB.BreakError):
                QB.embed_reference(cover, "ab" * 1000, stego)

    def test_wrong_length_header_is_reported_not_crashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            stego = Path(tmp) / "random.png"
            make_cover(stego, size=20)                      # no real header inside: random bits
            with self.assertRaises(QB.BreakError):
                QB.extract_reference(stego)


class RsaBlockHandling(unittest.TestCase):
    def test_hex_width_matches_the_project_rule(self):
        self.assertEqual(QB.hex_width(3233), 4)              # 12-bit N -> 2 bytes -> 4 hex chars
        self.assertEqual(QB.hex_width(255), 2)
        self.assertEqual(QB.hex_width(256), 4)

    def test_blocks_round_trip_for_every_byte_value(self):
        p, q, e, n, d = toy_rsa_key()
        message = bytes(range(0, 256, 17))                   # every byte must be < n (3233)
        cipher = [pow(b, e, n) for b in message]
        w = QB.hex_width(n)
        hex_text = "".join(format(c, f"0{w}x") for c in cipher)
        blocks = QB.blocks_from_hex(hex_text, n)
        self.assertEqual(blocks, cipher)
        self.assertEqual(QB.decrypt_blocks(blocks, d, n), message)

    def test_non_hex_text_is_rejected(self):
        with self.assertRaises(QB.BreakError):
            QB.blocks_from_hex("zzzz", 3233)

    def test_wrong_block_width_is_rejected(self):
        with self.assertRaises(QB.BreakError):
            QB.blocks_from_hex("abc", 3233)                  # not a multiple of 4

    def test_rebuild_private_key_matches_the_real_d(self):
        p, q, e, n, d = toy_rsa_key()
        self.assertEqual(QB.rebuild_private_key(e, n, p, q), d)
        self.assertEqual(QB.rebuild_private_key(e, n, q, p), d)   # order of p, q should not matter

    def test_rebuild_rejects_factors_that_do_not_multiply_to_n(self):
        with self.assertRaises(QB.BreakError):
            QB.rebuild_private_key(17, 3233, 3, 5)

    def test_decrypt_rejects_a_value_that_is_not_one_byte(self):
        # a block that decrypts to >= 256 means e/N were given wrong; must not silently misdecode
        with self.assertRaises(QB.BreakError):
            QB.decrypt_blocks([9999999], 1, 10**9 + 7)


class EndToEndWithAFakeCircuit(unittest.TestCase):
    """The whole pipeline (image in, message out), with the Shor step replaced by a fake
    `factor_modulus` so this runs on any machine, without qiskit."""

    def test_break_stego_image_end_to_end(self):
        p, q, e, n, d = toy_rsa_key()
        message = b"HI QUANTUM"
        cipher = [pow(b, e, n) for b in message]
        w = QB.hex_width(n)
        hex_text = "".join(format(c, f"0{w}x") for c in cipher)
        with tempfile.TemporaryDirectory() as tmp:
            cover, stego = Path(tmp) / "cover.png", Path(tmp) / "stego.png"
            make_cover(cover)
            QB.embed_reference(cover, hex_text, stego)

            real_factor = QB.factor_modulus
            QB.factor_modulus = lambda nn, shots=0, max_tries=0, progress=None: {
                "factors": (p, q), "a": 7, "period": 4, "method": "fake (test stand-in)",
                "attempts": [{"a": 7, "period": 4, "factors": [p, q]}], "records": []}
            try:
                result = QB.break_stego_image(stego, e, n)
            finally:
                QB.factor_modulus = real_factor

        self.assertEqual(result["message"], message)
        self.assertEqual((result["p"], result["q"]), (p, q))
        self.assertEqual(result["d"], d)

    def test_mismatched_block_width_is_caught_before_any_circuit_runs(self):
        p, q, e, n, _ = toy_rsa_key()
        with tempfile.TemporaryDirectory() as tmp:
            cover, stego = Path(tmp) / "cover.png", Path(tmp) / "stego.png"
            make_cover(cover)
            QB.embed_reference(cover, "abc", stego)           # 3 hex chars: not a whole block for any N
            with self.assertRaises(QB.BreakError):
                QB.break_stego_image(stego, e, n)

    def test_oversize_n_is_caught_before_any_circuit_runs(self):
        p, q, e, n, _ = toy_rsa_key()
        with tempfile.TemporaryDirectory() as tmp:
            cover, stego = Path(tmp) / "cover.png", Path(tmp) / "stego.png"
            make_cover(cover)
            QB.embed_reference(cover, "ab" * 4, stego)
            with self.assertRaises(QB.BreakError):
                QB.break_stego_image(stego, e, 2 ** 20 + 7)    # above MAX_MODULUS_BITS


class OversizeModulusIsRefused(unittest.TestCase):
    def test_above_the_bit_cap_is_refused_without_touching_qiskit(self):
        with self.assertRaises(QB.BreakError):
            QB.factor_modulus(2 ** 20 + 7)                    # 21 bits > MAX_MODULUS_BITS


@unittest.skipUnless(HAS_QISKIT and SLOW, "slow quantum test: install qiskit and set RUN_SLOW=1")
class RealShorCircuit(unittest.TestCase):
    def test_factor_modulus_finds_the_real_factors(self):
        out = QB.factor_modulus(3233, shots=2048)             # 61 x 53, real Q1 circuit on Aer
        self.assertEqual(out["factors"], (53, 61))
        self.assertEqual(out["method"], "quantum circuit")

    def test_whole_pipeline_with_the_real_circuit(self):
        p, q, e, n, d = toy_rsa_key()
        message = b"QC"
        cipher = [pow(b, e, n) for b in message]
        w = QB.hex_width(n)
        hex_text = "".join(format(c, f"0{w}x") for c in cipher)
        with tempfile.TemporaryDirectory() as tmp:
            cover, stego = Path(tmp) / "cover.png", Path(tmp) / "stego.png"
            make_cover(cover)
            QB.embed_reference(cover, hex_text, stego)
            result = QB.break_stego_image(stego, e, n, shots=2048)
        self.assertEqual(result["message"], message)
        self.assertEqual(result["d"], d)


if __name__ == "__main__":
    unittest.main()
