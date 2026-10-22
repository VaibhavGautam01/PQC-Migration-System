import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import layer_presets as lp  # type: ignore # noqa: E402


class TestPresets(unittest.TestCase):
    def test_every_preset_scores(self):
        for name in lp.preset_names():
            for exposure in ("keyless", "bypassable", "keyed"):
                with self.subTest(name=name, exposure=exposure):
                    r = lp.score_preset(name, exposure, modulus_bits=2048)
                    self.assertTrue(0 <= r["overall"] <= 100)

    def test_known_values(self):
        cases = [("ml_dsa_65", "keyless", None, 4.7), ("slh_dsa", "keyless", None, 4.7),
                 ("rsa_signature_pss", "keyless", 2048, 50.8), ("crc32_integrity", "bypassable", None, 30.4),
                 ("sha256_passphrase_frame_key", "bypassable", None, 35.8),
                 ("random_key_frame_selection_v2", "bypassable", None, 7.3),
                 ("ml_kem_768_aes_256_gcm", "keyless", None, 4.7), ("rsa_textbook", "keyless", 256, 91.9)]
        for name, exp, bits, expected in cases:
            with self.subTest(name=name):
                self.assertEqual(round(lp.score_preset(name, exp, modulus_bits=bits)["overall"], 1), expected)

    def test_rsa_presets_need_a_modulus(self):
        for name in ("rsa_textbook", "rsa_oaep", "rsa_signature_pss"):
            with self.assertRaises(ValueError):
                lp.score_preset(name, "keyless")

    def test_non_rsa_presets_ignore_a_modulus(self):
        self.assertEqual(lp.score_preset("ml_dsa_65", "keyless", modulus_bits=1024)["overall"],
                         lp.score_preset("ml_dsa_65", "keyless")["overall"])

    def test_unknown_preset(self):
        with self.assertRaises(ValueError):
            lp.score_preset("rot13", "keyless")

    def test_provisional_flags(self):
        self.assertTrue(lp.is_provisional("ml_dsa_65"))
        self.assertTrue(lp.is_provisional("random_key_frame_selection_v2"))
        self.assertFalse(lp.is_provisional("rsa_textbook"))
        self.assertFalse(lp.is_provisional("ml_kem_768_aes_256_gcm"))

    def test_pqc_signature_scores_far_below_rsa_signature(self):
        rsa = lp.score_preset("rsa_signature_pss", "keyless", modulus_bits=2048)["overall"]
        pqc = lp.score_preset("ml_dsa_65", "keyless")["overall"]
        self.assertGreater(rsa - pqc, 40)

    def test_every_preset_has_a_note(self):
        self.assertTrue(all(p["note"] for p in lp.PRESETS.values()))


if __name__ == "__main__":
    unittest.main()