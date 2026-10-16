import json
import tempfile
import unittest
from pathlib import Path

from src import quantum_runs as qr


def make_run(run_id="r1", inputs=None, result=None, group="shor_N15"):
    return {
        "run_id": run_id, "timestamp_utc": qr.now_utc(), "algorithm": "shor_pe",
        "question_group": group, "inputs": inputs or {"N": 15, "a": 7},
        "qubits": 8, "depth": 40, "gate_counts": {"cx": 10, "h": 4}, "shots": 1000,
        "backend": "AerSimulator", "backend_version": "0.17.2", "qiskit_version": "2.5.2",
        "seed_simulator": 12345, "seed_transpiler": 12345,
        "counts": {"00": 500, "11": 500}, "success_rate": 0.9, "runtime_seconds": 0.5,
        "diagram_file": "docs/circuits/r1.png", "label": "Aer simulator, toy size",
        "simulated": True, "result": result or {"period": 4},
    }


class QuantumRunTests(unittest.TestCase):
    def test_valid_record_has_no_problems(self):
        self.assertEqual(qr.validate_run(make_run()), [])

    def test_missing_field_is_reported(self):
        r = make_run(); del r["seed_simulator"]
        self.assertIn("missing field: seed_simulator", qr.validate_run(r))

    def test_counts_must_match_shots(self):
        r = make_run(); r["counts"] = {"00": 1}
        self.assertIn("counts do not add up to shots", qr.validate_run(r))

    def test_simulated_needs_simulator_label(self):
        r = make_run(); r["label"] = "quantum"
        self.assertTrue(any("rule 11" in p for p in qr.validate_run(r)))

    def test_bool_is_not_an_int(self):
        r = make_run(); r["shots"] = True
        self.assertTrue(qr.validate_run(r))

    def test_change_the_question(self):
        a = make_run("a", {"N": 15, "a": 7}, {"period": 4})
        b = make_run("b", {"N": 21, "a": 2}, {"period": 6})
        same = make_run("c", {"N": 15, "a": 7}, {"period": 4})
        self.assertTrue(qr.check_change_the_question([a, b], "shor_N15"))
        self.assertFalse(qr.check_change_the_question([a, same], "shor_N15"))
        self.assertFalse(qr.check_change_the_question([a], "shor_N15"))

    def test_append_and_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "runs.json"
            qr.append_run(make_run("x"), p)
            self.assertEqual(len(qr.load_runs(p)), 1)
            with self.assertRaises(ValueError):
                qr.append_run(make_run("x"), p)
            self.assertEqual(json.loads(p.read_text())["schema_version"], 1)

    def test_invalid_record_is_not_written(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "runs.json"
            r = make_run(); r["shots"] = 0
            with self.assertRaises(ValueError):
                qr.append_run(r, p)
            self.assertFalse(p.exists())


if __name__ == "__main__":
    unittest.main()
