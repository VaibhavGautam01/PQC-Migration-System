import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE.parent))

import shor_run as SR  # type: ignore # noqa: E402
from q2_shor import build_shor_ipea  # type: ignore # noqa: E402
from src import evidence_gate as EG  # noqa: E402
from src import quantum_runs as QR  # noqa: E402


def fake_record(N, a, factors, stamp):
    """A record shaped like run_shor() output (no simulator needed)."""
    return {"id": f"q2-shor-N{N}-a{a}-{stamp}", "label": SR.LABEL, "N": N, "a": a, "n_bits": N.bit_length(),
            "phase_bits": 2 * N.bit_length(), "qubits": 2 * N.bit_length() + 3, "depth": 100,
            "gate_counts": {"h": 8, "cx": 4}, "shots": 20, "backend": "aer_simulator",
            "qiskit_version": "2.5.2", "qiskit_aer_version": "0.17.2",
            "seed_simulator": 12345, "seed_transpiler": 12345,
            "counts": {"00000000": 12, "11000000": 8}, "factors_found": {f"{factors[0]}x{factors[1]}": 12},
            "success_rate": 0.6, "transpile_seconds": 1.5, "run_seconds": 2.5,
            "diagram_file": None, "chi_square": None, "pending": []}


class TestQ2EvidenceRecord(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [mock.patch.object(SR, "ROOT", self.root),
                        mock.patch.object(SR, "DIAGRAM_DIR", self.root / "docs" / "circuits")]
        for p in self.patches:
            p.start()
        self.runs = self.root / "data" / "quantum_runs.json"

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_converted_record_passes_the_evidence_schema(self):
        qc = build_shor_ipea(7, 15)
        rel = SR.write_diagram(qc, 15, 7)
        rec = SR.to_evidence(fake_record(15, 7, (3, 5), "a"), rel)
        self.assertEqual(QR.validate_run(rec), [])
        self.assertEqual(rec["algorithm"], "shor_gate")
        self.assertEqual(rec["result"]["factors"], [3, 5])
        self.assertTrue(rec["simulated"])
        self.assertIn("simulator", rec["label"].lower())

    def test_diagram_file_is_a_labelled_summary_inside_the_repo(self):
        rel = SR.write_diagram(build_shor_ipea(7, 15), 15, 7)
        self.assertEqual(rel, "docs/circuits/q2_shor_gate_N15_a7.txt")
        text = (self.root / rel).read_text(encoding="utf-8")
        self.assertIn("structure summary", text)
        self.assertIn("qubits = 11", text)

    def test_save_appends_to_the_runs_object_not_a_list(self):
        SR.save_record(fake_record(15, 7, (3, 5), "a"), build_shor_ipea(7, 15), self.runs)
        SR.save_record(fake_record(21, 2, (3, 7), "b"), build_shor_ipea(2, 21), self.runs)
        runs = QR.load_runs(self.runs)
        self.assertEqual([r["inputs"]["N"] for r in runs], [15, 21])

    def test_two_different_n_pass_the_change_the_question_gate(self):
        SR.save_record(fake_record(15, 7, (3, 5), "a"), build_shor_ipea(7, 15), self.runs)
        SR.save_record(fake_record(21, 2, (3, 7), "b"), build_shor_ipea(2, 21), self.runs)
        errors, warnings = EG.check_runs(QR.load_runs(self.runs), root=self.root, strict=True)
        self.assertEqual((errors, warnings), ([], []))

    def test_same_run_twice_is_refused(self):
        rec = fake_record(15, 7, (3, 5), "a")
        SR.save_record(rec, build_shor_ipea(7, 15), self.runs)
        with self.assertRaises(ValueError):
            SR.save_record(rec, build_shor_ipea(7, 15), self.runs)

    def test_run_with_no_factors_gives_an_empty_result_not_a_crash(self):
        rec = fake_record(15, 7, (3, 5), "a")
        rec["factors_found"] = {}
        rec["success_rate"] = 0.0
        self.assertEqual(SR.to_evidence(rec, "x.txt")["result"]["factors"], [])


if __name__ == "__main__":
    unittest.main()
