"""Slow quantum tests (Aer simulator, toy size). Run with:
python -m unittest discover -s tests -p "slow_test*.py" -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import bb84, qkd_hybrid


class TestBB84(unittest.TestCase):
    def test_no_eve_gives_matching_key_and_zero_qber(self):
        out = bb84.run_bb84(n_qubits=1024, seed=11)
        self.assertEqual(out["qber"], 0.0)
        self.assertEqual(len(out["key"]), 32)
        self.assertEqual(out["record"]["label"], "Aer simulator, toy size")
        blob = qkd_hybrid.qkd_encrypt(out["key"], b"message under a BB84 key")
        self.assertEqual(qkd_hybrid.qkd_decrypt(out["key"], blob), b"message under a BB84 key")

    def test_change_the_question_gives_a_different_key(self):
        k1 = bb84.run_bb84(n_qubits=1024, seed=21)["key"]
        k2 = bb84.run_bb84(n_qubits=1024, seed=22)["key"]
        self.assertNotEqual(k1, k2)

    def test_same_seed_reproduces(self):
        self.assertEqual(bb84.run_bb84(n_qubits=1024, seed=31)["key"], bb84.run_bb84(n_qubits=1024, seed=31)["key"])

    def test_eve_is_detected_qber_near_25_percent(self):
        with self.assertRaises(bb84.QKDAbort) as cm:
            bb84.run_bb84(n_qubits=1024, seed=41, eve=True)
        self.assertIsNotNone(cm.exception.qber)
        self.assertGreater(cm.exception.qber, 0.15)
        self.assertLess(cm.exception.qber, 0.35)

    def test_tampered_classical_message_aborts(self):
        channel = bb84.AuthChannel(tamper=lambda w: bytes([w[0] ^ 1]) + w[1:])
        with self.assertRaises(bb84.QKDAbort):
            bb84.run_bb84(n_qubits=256, seed=51, channel=channel)

    def test_evidence_record_written(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "runs.json"
            bb84.run_bb84(n_qubits=1024, seed=61, evidence_path=path)
            rec = json.loads(path.read_text(encoding="utf-8"))[0]
            for field in ("algorithm", "qubits", "depth", "gate_counts", "shots", "backend",
                          "seed_simulator", "seed_transpiler", "run_seconds", "label"):
                self.assertIn(field, rec)


if __name__ == "__main__":
    unittest.main()