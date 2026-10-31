"""Tests for extras/generate_test_set.py. The LSB/XOR-LSB/toy-RSA logic needs no external
libraries; the OAEP and ML-KEM-hybrid cases are skipped here if those libraries aren't
installed (same pattern as the rest of this project's PQC tests)."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HAS_PQC = all(importlib.util.find_spec(m) for m in ("kyber_py", "Crypto"))


def load_script():
    spec = importlib.util.spec_from_file_location("generate_test_set",
                                                   str(ROOT / "extras/generate_test_set.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ToyRsaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_script()

    def test_every_toy_n_round_trips(self):
        m = self.m
        for n_bits in m.TOY_KEY_TABLE:
            r = m.toy_rsa_textbook(b"HELLO", n_bits)
            blocks = [int.from_bytes(r["blob"][i:i + r["block_bytes"]], "big")
                     for i in range(0, len(r["blob"]), r["block_bytes"])]
            recovered = bytes(pow(b, r["d"], r["n"]) for b in blocks)
            self.assertEqual(recovered, bytes(r["plaintext_bytes_used"]), n_bits)

    def test_large_message_bytes_are_clamped_not_rejected(self):
        # ASCII "HELLO" (72-111) is larger than every toy N; this must not raise
        r = self.m.toy_rsa_textbook(b"HELLO WORLD", 15)
        self.assertTrue(all(b < 15 for b in r["plaintext_bytes_used"]))

    def test_distinct_toy_n_values_give_distinct_moduli(self):
        # regression test for the lambda late-binding bug found during development
        seen = {self.m.toy_rsa_textbook(b"x", n)["n"] for n in self.m.TOY_KEY_TABLE}
        self.assertEqual(len(seen), len(self.m.TOY_KEY_TABLE))


class EmbeddingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_script()

    def test_lsb_round_trip(self):
        cover = self.m.make_cover(64, 1)
        payload = b"a reasonably long test payload for the LSB method"
        stego = self.m.embed_lsb(cover, payload)
        self.assertEqual(self.m.extract_lsb(stego), payload)

    def test_lsb_rejects_a_payload_too_big_for_the_cover(self):
        cover = self.m.make_cover(8, 1)
        with self.assertRaises(ValueError):
            self.m.embed_lsb(cover, b"x" * 1000)

    def test_xor_lsb_round_trip_with_the_correct_key(self):
        cover = self.m.make_cover(64, 2)
        payload = b"another test payload, this time for XOR-LSB"
        key = b"a-test-key"
        stego = self.m.embed_xor_lsb(cover, payload, key)
        self.assertEqual(self.m.extract_xor_lsb(stego, key), payload)

    def test_xor_lsb_wrong_key_fails_cleanly_not_with_a_memory_crash(self):
        # regression test for the found-during-development bug: a garbage-decoded length
        # from the wrong key must raise ValueError, not attempt a multi-GB allocation
        cover = self.m.make_cover(64, 3)
        payload = b"payload"
        stego = self.m.embed_xor_lsb(cover, payload, b"right-key")
        with self.assertRaises(ValueError):
            self.m.extract_xor_lsb(stego, b"wrong-key")

    def test_lsb_and_xor_lsb_of_the_same_payload_differ(self):
        # sanity check that xor_lsb is not secretly identical to plain lsb
        cover = self.m.make_cover(64, 4)
        payload = b"distinguish me"
        a = self.m.embed_lsb(cover, payload)
        b = self.m.embed_xor_lsb(cover, payload, b"some-key")
        self.assertFalse((a == b).all())


@unittest.skipUnless(HAS_PQC, "kyber-py / pycryptodome not installed")
class FullPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_script()

    def test_mlkem_hybrid_payload_has_the_right_structure(self):
        r = self.m.mlkem_hybrid(b"test message")
        self.assertEqual(r["cipher"], "mlkem_hybrid")
        self.assertIn("overhead_bytes", r)

    def test_build_test_set_writes_one_manifest_entry_per_image(self):
        import json
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "test_set"
            manifest_path, n_items = self.m.build_test_set(
                out, count=1, seed=1, toy_ns=[15, 21], oaep_bits=1024,
                cover_size=128, message=b"HI")
            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(len(manifest["items"]), n_items)
            png_files = list(out.glob("*.png"))
            self.assertEqual(len(png_files), n_items)

    def test_distinct_toy_n_produce_distinct_filenames(self):
        # end-to-end regression test for the lambda late-binding bug
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "test_set"
            manifest_path, _ = self.m.build_test_set(
                out, count=1, seed=1, toy_ns=[15, 21, 35], oaep_bits=1024,
                cover_size=128, message=b"HI")
            import json
            manifest = json.loads(manifest_path.read_text())
            ns = {item["n"] for item in manifest["items"] if item.get("cipher") == "rsa_textbook"
                 and item.get("n_bits", 999) < 100}
            self.assertEqual(ns, {15, 21, 35})


if __name__ == "__main__":
    unittest.main()
