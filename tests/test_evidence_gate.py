import tempfile
import unittest
from pathlib import Path

from src import evidence_gate as G
from src import quantum_runs as QR


def make_run(run_id="r1", inputs=None, result=None, group="shor_N15", diagram="d/r1.png"):
    return {
        "run_id": run_id, "timestamp_utc": QR.now_utc(), "algorithm": "shor_pe",
        "question_group": group, "inputs": inputs or {"N": 15, "a": 7},
        "qubits": 8, "depth": 40, "gate_counts": {"cx": 10}, "shots": 1000,
        "backend": "AerSimulator", "backend_version": "0.17.2", "qiskit_version": "2.5.2",
        "seed_simulator": 12345, "seed_transpiler": 12345,
        "counts": {"00": 500, "11": 500}, "success_rate": 0.9, "runtime_seconds": 0.5,
        "diagram_file": diagram, "label": "Aer simulator, toy size",
        "simulated": True, "result": result or {"period": 4},
    }


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "d").mkdir()
        for name in ("r1.png", "r2.png"):
            (self.root / "d" / name).write_bytes(b"png")

    def tearDown(self):
        self.tmp.cleanup()

    def pair(self):
        return [make_run("r1", {"N": 15, "a": 7}, {"period": 4}, diagram="d/r1.png"),
                make_run("r2", {"N": 21, "a": 2}, {"period": 6}, diagram="d/r2.png")]

    def test_no_runs_is_not_an_error(self):
        self.assertEqual(G.check_runs([], self.root), ([], []))

    def test_complete_pair_passes_even_in_strict_mode(self):
        self.assertEqual(G.check_runs(self.pair(), self.root, strict=True), ([], []))

    def test_incomplete_record_is_an_error(self):
        runs = self.pair()
        del runs[0]["seed_simulator"]
        errors, _ = G.check_runs(runs, self.root)
        self.assertTrue(any("seed_simulator" in e for e in errors))

    def test_missing_diagram_file_is_an_error(self):
        runs = self.pair()
        runs[1]["diagram_file"] = "d/missing.png"
        errors, _ = G.check_runs(runs, self.root)
        self.assertTrue(any("diagram file not found" in e for e in errors))

    def test_duplicate_run_id_is_an_error(self):
        runs = self.pair()
        runs[1]["run_id"] = "r1"
        errors, _ = G.check_runs(runs, self.root)
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_single_run_group_is_a_warning_then_an_error_in_strict_mode(self):
        runs = self.pair()[:1]
        errors, warnings = G.check_runs(runs, self.root)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)
        errors, warnings = G.check_runs(runs, self.root, strict=True)
        self.assertEqual(len(errors), 1)
        self.assertEqual(warnings, [])

    def test_same_question_twice_fails_change_the_question(self):
        runs = [make_run("r1", diagram="d/r1.png"), make_run("r2", diagram="d/r2.png")]
        _, warnings = G.check_runs(runs, self.root)
        self.assertEqual(len(warnings), 1)

    def test_same_inputs_with_different_results_still_fail(self):
        runs = [make_run("r1", {"N": 15, "a": 7}, {"period": 4}, diagram="d/r1.png"),
                make_run("r2", {"N": 15, "a": 7}, {"period": 2}, diagram="d/r2.png")]
        _, warnings = G.check_runs(runs, self.root)
        self.assertEqual(len(warnings), 1)

    def test_changed_input_but_same_result_fails(self):
        runs = [make_run("r1", {"N": 15, "a": 7}, {"period": 4}, diagram="d/r1.png"),
                make_run("r2", {"N": 21, "a": 2}, {"period": 4}, diagram="d/r2.png")]
        _, warnings = G.check_runs(runs, self.root)
        self.assertEqual(len(warnings), 1)


class RealRepoGate(unittest.TestCase):
    def test_committed_runs_have_complete_records(self):
        n, errors, _ = G.run_gate()
        self.assertEqual(errors, [], f"{n} runs in data/quantum_runs.json, problems: {errors}")


if __name__ == "__main__":
    unittest.main()
