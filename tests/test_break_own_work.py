"""Tests for extras/break_own_work.py. No qiskit needed; needs kyber-py/pycryptodome/PIL
(same as the Week 2 PQC tests) - skipped with a message if those are missing."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HAS_PQC = all(importlib.util.find_spec(m) for m in ("kyber_py", "Crypto"))


def load_script():
    spec = importlib.util.spec_from_file_location("break_own_work", str(ROOT / "extras/break_own_work.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(HAS_PQC, "kyber-py / pycryptodome not installed")
class NonceReuse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_script()

    def test_reused_nonce_leaks_the_xor_as_expected(self):
        findings = []
        self.m.check_nonce_reuse(findings)
        leak = next(f for f in findings if "XOR" in f["check"])
        self.assertEqual(leak["status"], "FOUND A GAP")        # the general attack class is real
        self.assertIn("True", leak["detail"])

    def test_hybrid_encrypt_never_reuses_a_nonce_in_normal_use(self):
        findings = []
        self.m.check_nonce_reuse(findings)
        safe = next(f for f in findings if "hybrid_encrypt()" in f["check"])
        self.assertEqual(safe["status"], "CONFIRMED SAFE")


@unittest.skipUnless(HAS_PQC, "kyber-py / pycryptodome not installed")
class ScoreGaming(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_script()

    def test_mislabelling_category_is_flagged_as_a_gap(self):
        findings = []
        self.m.check_score_gaming(findings)
        self.assertTrue(any("mislabelling" in f["check"] for f in findings))
        self.assertTrue(all(f["status"] == "FOUND A GAP" for f in findings))

    def test_weights_file_has_no_integrity_check(self):
        findings = []
        self.m.check_score_gaming(findings)
        self.assertTrue(any("risk_weights.json" in f["check"] for f in findings))


if __name__ == "__main__":
    unittest.main()
