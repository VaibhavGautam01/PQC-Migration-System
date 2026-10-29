import unittest

from src import risk_score as rs


class RiskScoreEdgeTests(unittest.TestCase):
    def test_bigger_key_never_raises_score(self):
        scores = [rs.score_layer("shor_broken", "oaep", "keyless", modulus_bits=n)["overall"]
                  for n in (512, 1024, 2048, 3072)]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_padding_never_raises_score(self):
        none = rs.score_layer("shor_broken", "no_padding_deterministic", "keyless", modulus_bits=2048)["overall"]
        oaep = rs.score_layer("shor_broken", "oaep", "keyless", modulus_bits=2048)["overall"]
        self.assertLess(oaep, none)

    def test_ml_kem_with_aead_stays_low(self):
        r = rs.score_layer("nist_pqc", "aead", "keyless", modulus_bits=None)
        self.assertEqual(r["band"], "Low")
        self.assertLess(r["overall"], 10)


if __name__ == "__main__":
    unittest.main()
