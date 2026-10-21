"""Tests for q1_factor.quantum_factor. They use a FAKE runner, so no qiskit is needed here;
the real circuit end to end is the slow test at the bottom (RUN_SLOW=1)."""
import importlib.util
import os
import unittest

from src import quantum_guard as G
from src import q1_factor as QF

HAS_QISKIT = importlib.util.find_spec("qiskit_aer") is not None
SLOW = os.environ.get("RUN_SLOW") == "1" or os.environ.get("SLOW_TESTS") == "1"


def fake_runner_factory(outcomes_by_a, m):
    """Runner returning a pre-made histogram per base a (simulates measured counts)."""
    calls = []

    def runner(a, N, shots):
        calls.append(a)
        counts = {format(y, f"0{m}b"): c for y, c in outcomes_by_a.get(a, {0: shots}).items()}
        return {"counts": counts, "inputs": {"N": N, "a": a, "counting_qubits": m},
                "question_group": "shor_pe_change_N_a"}, None
    runner.calls = calls
    return runner


class QuantumFactorLogic(unittest.TestCase):
    def test_uses_measured_counts_to_get_factors(self):
        r = fake_runner_factory({2: {64: 50, 192: 50}}, 8)          # phases 1/4 and 3/4, N=15
        out = QF.quantum_factor(15, runner=r)
        self.assertEqual(out["factors"], (3, 5))
        self.assertEqual(out["period"], 4)
        self.assertEqual(out["method"], "quantum circuit")
        self.assertEqual(r.calls, [2])

    def test_failed_base_moves_on_to_next_base(self):
        # N=35: base 2 measures only y=0 (no information), so base 3 must be tried.
        # For base 3 the phase 341/4096 ~ 1/12 gives period 12 and factors (5, 7).
        r = fake_runner_factory({3: {341: 100}}, 12)
        out = QF.quantum_factor(35, runner=r)
        self.assertEqual(r.calls, [2, 3])
        self.assertEqual(out["a"], 3)
        self.assertEqual(out["factors"], (5, 7))

    def test_lucky_gcd_needs_no_circuit(self):
        r = fake_runner_factory({}, 8)
        out = QF.quantum_factor(6, runner=r)                        # a=2 shares factor 2 with 6
        self.assertEqual(out["factors"], (2, 3))
        self.assertEqual(out["method"], "lucky gcd")
        self.assertEqual(r.calls, [])

    def test_gives_up_after_max_tries(self):
        r = fake_runner_factory({}, 12)                             # always only y=0
        out = QF.quantum_factor(35, runner=r, max_tries=2)
        self.assertIsNone(out["factors"])
        self.assertEqual(out["method"], "failed")
        self.assertEqual(len(r.calls), 2)

    def test_records_carry_the_stego_evidence_group(self):
        r = fake_runner_factory({2: {64: 100}}, 8)
        out = QF.quantum_factor(15, runner=r)
        self.assertTrue(all(rec["question_group"] == QF.STEGO_GROUP for rec in out["records"]))


class GuardAndSlow(unittest.TestCase):
    def test_q1_factor_passes_the_static_guard(self):
        self.assertEqual(G.scan_file("src/q1_factor.py", "all"), [])

    @unittest.skipUnless(HAS_QISKIT and SLOW, "slow quantum test: set RUN_SLOW=1")
    def test_real_circuit_factors_15_21_35(self):
        for N, want in ((15, (3, 5)), (21, (3, 7)), (35, (5, 7))):
            out = QF.quantum_factor(N)
            self.assertEqual(out["factors"], want, N)


if __name__ == "__main__":
    unittest.main()
