import unittest

from stego_analyzer import cipher_identify as ci
from pqc_stego import hybrid


class IdentifyTests(unittest.TestCase):
    def test_empty_is_unrecognised(self):
        self.assertEqual(ci.identify(b"")["kind"], "unrecognised")

    def test_non_hex_is_unrecognised(self):
        self.assertEqual(ci.identify(b"not hex at all!")["kind"], "unrecognised")

    def test_one_byte_short_of_hybrid_is_unrecognised(self):
        blob = ("ab" * (hybrid.OVERHEAD - 1)).encode()
        self.assertEqual(ci.identify(blob)["kind"], "unrecognised")

    def test_hybrid_length_boundary(self):
        blob = ("ab" * hybrid.OVERHEAD).encode()
        r = ci.identify(blob)
        self.assertEqual(r["kind"], "ml_kem_aes_gcm")
        self.assertIn("length only", r["evidence"])

    def test_bad_public_keys_do_not_crash(self):
        for key in ({}, {"n": 0}, {"n": 1}, {"n": -5}, {"n": "abc"}):
            r = ci.identify(b"0a0b0c0d", public_key=key)
            self.assertIn("kind", r)


if __name__ == "__main__":
    unittest.main()
