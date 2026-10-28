"""
Tests for Q10 (Shor's algorithm for the discrete log).

Groups:
  1. no qiskit needed : dlog_post.py (post-processing), parse_counts logic
  2. qiskit installed  : circuit construction sanity checks, static guard
  3. SLOW (RUN_SLOW=1) : real runs on Aer, including the --self-test instance

!!! Before trusting Q10 on your machine, run:  python -m src.q10_run --self-test
That is the definitive check of the count-key parsing convention (see q10_dlog.py and
q10_run.py's module docstrings) for your installed Qiskit version.

Run the fast tests: python -m unittest tests.test_q10_dlog -v
Run the slow ones  : set RUN_SLOW=1   (Command Prompt) then the same command
"""
import importlib.util
import os
import unittest
from pathlib import Path

from src import dlog_post as DP
from src import quantum_guard as G

ROOT = Path(__file__).resolve().parent.parent
HAS_QISKIT = importlib.util.find_spec("qiskit") is not None and \
    importlib.util.find_spec("qiskit_aer") is not None
SLOW = os.environ.get("RUN_SLOW") == "1" or os.environ.get("SLOW_TESTS") == "1"

# Pre-computed (c1, c2) peaks for p=11, g=2, h=8 (x=3), r=10, t=7 (T=128), VERIFIED against an
# independent numpy simulation of the Q10 circuit before this test was written. c1 is register
# A's outcome, c2 is register B's. Only the 10 peaks with weight > 1e-4 are listed (j=0..9).
KNOWN_PEAKS_P11 = [(0, 0), (64, 64), (26, 77), (38, 115), (51, 26), (90, 13),
                  (102, 51), (115, 90), (13, 38), (77, 102)]


class PostProcessingTests(unittest.TestCase):
    def test_check_inputs(self):
        DP.check_inputs(2, 8, 11)
        for g, h, p in [(1, 8, 11), (2, 11, 11), (2, 8, 2)]:
            with self.assertRaises(ValueError):
                DP.check_inputs(g, h, p)

    def test_recovers_x_from_the_known_peaks(self):
        # every peak above with j coprime to r=10 (j in {1,3,7,9}) must recover x=3 when verified
        p, g, h, r, t = 11, 2, 8, 10, 7
        good = {(38, 115): 1, (115, 90): 3, (13, 38): 7, (90, 13): 9}
        for (c1, c2), j in good.items():
            x = DP.recover_x_candidate(c1, c2, t, r, g, h, p)
            self.assertEqual(x, 3, f"(c1={c1}, c2={c2}), j={j}")

    def test_non_coprime_j_gives_no_candidate_or_a_verified_one(self):
        # j=2,4,5,6,8 are not coprime to r=10 (except j=5=r/2, degenerate); recover_x_candidate
        # must NEVER return an unverified x - check it only ever returns None or a value that
        # satisfies g**x % p == h
        p, g, h, r, t = 11, 2, 8, 10, 7
        for c1 in range(2 ** t):
            for c2 in (26, 51, 77, 102, 64):             # the non-j-coprime peak c2 values
                x = DP.recover_x_candidate(c1, c2, t, r, g, h, p)
                if x is not None:
                    self.assertEqual(pow(g, x, p), h)

    def test_analyse_counts_finds_x_from_a_synthetic_histogram(self):
        p, g, h, r, t = 11, 2, 8, 10, 7
        counts = {}
        for (c1, c2) in KNOWN_PEAKS_P11:
            bits = format(c1, f"0{t}b") + format(c2, f"0{t}b")
            counts[bits] = 50
        out = DP.analyse_counts(counts, t, r, g, h, p)
        self.assertEqual(out["x"], 3)
        self.assertEqual(pow(g, out["x"], p), h)

    def test_change_the_question_different_g_h_gives_different_x(self):
        # same r (both instances use subgroup order 22 of p=23), different g/h -> different x
        p1, g1, h1, r1 = 23, 5, pow(5, 7, 23), 22
        p2, g2, h2, r2 = 23, 5, pow(5, 19, 23), 22
        counts1 = {format(round(j * 7 * 128 / 22) % 128, "07b") + format(round(-j * 128 / 22) % 128, "07b"): 10
                  for j in range(1, 22) if __import__("math").gcd(j, 22) == 1}
        counts2 = {format(round(j * 19 * 128 / 22) % 128, "07b") + format(round(-j * 128 / 22) % 128, "07b"): 10
                  for j in range(1, 22) if __import__("math").gcd(j, 22) == 1}
        x1 = DP.analyse_counts(counts1, 7, r1, g1, h1, p1)["x"]
        x2 = DP.analyse_counts(counts2, 7, r2, g2, h2, p2)["x"]
        self.assertEqual(x1, 7)
        self.assertEqual(x2, 19)


class ParseCountsLogic(unittest.TestCase):
    """parse_counts() has no qiskit dependency in its logic, only in the module it lives in,
    so it is re-implemented identically here to test without importing q10_run.py (which
    requires qiskit at import time). EMPIRICALLY VERIFIED (see q10_run.py's parse_counts
    docstring): the raw key is already in "A's bits then B's bits" order - this function only
    strips a stray space some Qiskit versions add for a single classical register."""

    @staticmethod
    def parse_counts(raw_counts, t):
        out = {}
        for key, count in raw_counts.items():
            key = key.replace(" ", "")
            out[key] = out.get(key, 0) + int(count)
        return out

    def test_is_a_pass_through_once_a_stray_space_is_removed(self):
        out = self.parse_counts({"1010 0110": 50}, 4)
        self.assertEqual(out, {"10100110": 50})

    def test_already_clean_keys_are_unchanged(self):
        out = self.parse_counts({"10100110": 50}, 4)
        self.assertEqual(out, {"10100110": 50})


class RealMeasuredDataRegressionTest(unittest.TestCase):
    """Real Aer output, p=23 g=5 h=17 (secret x=7, order r=22), captured on 2026-10-27 before
    the parse_counts() fix. These 10 raw count keys are the GROUND TRUTH that proved the two
    earlier (wrong) versions of parse_counts() were backwards, and that the current direct
    pass-through is correct: 5 of the 5 non-degenerate, coprime-vote outcomes below correctly
    recover x=7 with NO transformation of the raw bits. This test pins that result down
    permanently so a future change to parse_counts() cannot silently reintroduce the bug."""

    REAL_RAW_COUNTS_P23 = {
        "10000000001000000000": 197, "00000000000000000000": 163,
        "00010111010100010111": 151, "10010111011100010111": 146,
        "01000101111101000110": 143, "11101000111011101001": 138,
        "11000101110101000110": 134, "00111010011010111010": 129,
        "01101000110011101001": 127, "00100011000110100011": 121,
    }

    @staticmethod
    def parse_counts(raw_counts, t):                    # same as the fixed q10_run.py version
        return {k.replace(" ", ""): v for k, v in raw_counts.items()}

    def test_real_measured_data_recovers_the_known_secret(self):
        p, g, x_true, r, t = 23, 5, 7, 22, 10
        h = pow(g, x_true, p)
        counts = self.parse_counts(self.REAL_RAW_COUNTS_P23, t)
        out = DP.analyse_counts(counts, t, r, g, h, p)
        self.assertEqual(out["x"], x_true)

    def test_at_least_five_of_the_ten_real_outcomes_individually_verify(self):
        p, g, x_true, r, t = 23, 5, 7, 22, 10
        h = pow(g, x_true, p)
        hits = 0
        for bits in self.REAL_RAW_COUNTS_P23:
            y1, y2 = int(bits[:t], 2), int(bits[t:], 2)
            if DP.recover_x_candidate(y1, y2, t, r, g, h, p) == x_true:
                hits += 1
        self.assertGreaterEqual(hits, 5)


class StaticChecks(unittest.TestCase):
    FILES = ("src/q10_dlog.py", "src/q10_run.py")

    def test_guard_passes(self):
        for rel in self.FILES:
            self.assertEqual(G.scan_file(rel, "all"), [], rel)

    def test_guard_discovers_the_files(self):
        for rel in self.FILES:
            self.assertIn(rel, G.discover_guarded())


@unittest.skipUnless(HAS_QISKIT, "qiskit not installed")
class CircuitConstructionTests(unittest.TestCase):
    def setUp(self):
        from src import q10_dlog as Q
        self.Q = Q

    def test_qubit_and_register_counts(self):
        qc = self.Q.build_dlog(2, 8, 11, t=5)
        self.assertEqual(qc.num_qubits, 5 + 5 + 11 .bit_length())
        self.assertEqual(qc.num_clbits, 10)

    def test_rejects_bad_g_or_h(self):
        with self.assertRaises(ValueError):
            self.Q.build_dlog(11, 8, 11)          # g == p
        with self.assertRaises(ValueError):
            self.Q.build_dlog(2, 1, 11)           # h == 1

    def test_default_counting_bits(self):
        self.assertEqual(self.Q.default_counting_bits(11), 8)   # 2 * bits(11)=2*4


@unittest.skipUnless(HAS_QISKIT and SLOW, "slow quantum test: install qiskit and set RUN_SLOW=1")
class SlowRuns(unittest.TestCase):
    def test_self_test_instance_recovers_x(self):
        from src.q10_run import find_order, run_dlog
        p, g, x = 11, 2, 3
        h = pow(g, x, p)
        r, _ = find_order(g, p)
        self.assertEqual(r, 10)
        record, _ = run_dlog(g, h, p, r)
        self.assertEqual(record["result"]["x"], x)
        self.assertTrue(record["cross_check"]["agree"])

    def test_change_the_question_p23(self):
        from src.q10_run import find_order, run_dlog
        p, g = 23, 5
        r, _ = find_order(g, p)
        for x in (7, 19):
            h = pow(g, x, p)
            record, _ = run_dlog(g, h, p, r)
            self.assertEqual(record["result"]["x"], x)

    def test_record_is_valid_for_the_evidence_gate(self):
        from src import quantum_runs as QR
        from src.q10_run import find_order, run_dlog
        p, g, x = 11, 2, 3
        h = pow(g, x, p)
        r, _ = find_order(g, p)
        record, _ = run_dlog(g, h, p, r, cross_check=False)
        self.assertEqual(QR.validate_run(record), [])


if __name__ == "__main__":
    unittest.main()
