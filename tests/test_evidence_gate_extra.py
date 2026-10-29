import json
import tempfile
import unittest
from pathlib import Path

from src import evidence_gate as G
from src import quantum_runs as QR
from tests.test_evidence_gate import make_run  # noqa: E402


class ExtraFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        (self.root / "d").mkdir()
        for name in ("r1.png", "r2.png", "r3.png"):
            (self.root / "d" / name).write_bytes(b"png")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, content):
        (self.data / name).write_text(json.dumps(content), encoding="utf-8")

    def main_file(self):
        runs = [make_run("r1", {"N": 15, "a": 7}, {"period": 4}, diagram="d/r1.png"),
                make_run("r2", {"N": 21, "a": 2}, {"period": 6}, diagram="d/r2.png")]
        self.write("quantum_runs.json", {"schema_version": 1, "runs": runs})

    def legacy_q6(self):
        # shaped like the real Q6 file: a bare list, fields outside the evidence schema
        self.write("quantum_runs_q6.json", [{"algorithm": "BB84", "inputs": {"n_qubits": 1024},
                                             "qubits": 1024, "label": "Aer simulator, toy size"}])

    def test_unconverted_extra_file_is_a_warning_not_an_error(self):
        self.main_file()
        self.legacy_q6()
        n, errors, warnings = G.run_gate(root=self.root, data_dir=self.data)
        self.assertEqual((n, errors), (2, []))
        self.assertEqual(len(warnings), 1)
        self.assertIn("quantum_runs_q6.json", warnings[0])
        self.assertIn("not in the evidence format", warnings[0])

    def test_strict_turns_that_warning_into_an_error(self):
        self.main_file()
        self.legacy_q6()
        n, errors, warnings = G.run_gate(root=self.root, strict=True, data_dir=self.data)
        self.assertEqual(warnings, [])
        self.assertEqual(len(errors), 1)
        self.assertIn("quantum_runs_q6.json", errors[0])

    def test_valid_records_in_an_extra_file_are_counted_and_checked(self):
        self.main_file()
        self.write("quantum_runs_q6.json", {"schema_version": 1, "runs": [
            make_run("r3", {"n_qubits": 8}, {"qber": 0.0}, group="bb84", diagram="d/r3.png")]})
        n, errors, warnings = G.run_gate(root=self.root, data_dir=self.data)
        self.assertEqual(n, 3)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 1)           # group bb84 has one run: change-the-question
        self.assertIn("bb84", warnings[0])

    def test_run_id_repeated_in_two_files_is_an_error(self):
        self.main_file()
        self.write("quantum_runs_q6.json", {"runs": [make_run("r1", diagram="d/r1.png")]})
        _, errors, _ = G.run_gate(root=self.root, data_dir=self.data)
        self.assertTrue(any("duplicate run_id" in e for e in errors))

    def test_unreadable_extra_file_is_reported_not_a_crash(self):
        self.main_file()
        (self.data / "quantum_runs_q7.json").write_text("{not json", encoding="utf-8")
        n, errors, warnings = G.run_gate(root=self.root, data_dir=self.data)
        self.assertEqual((n, errors), (2, []))
        self.assertIn("quantum_runs_q7.json: cannot read file", warnings[0])

    def test_explicit_path_still_checks_only_that_file(self):
        self.main_file()
        self.legacy_q6()
        n, errors, warnings = G.run_gate(path=self.data / "quantum_runs.json", root=self.root)
        self.assertEqual((n, errors, warnings), (2, [], []))

    def test_no_extra_files_behaves_as_before(self):
        self.main_file()
        self.assertEqual(G.run_gate(root=self.root, strict=True, data_dir=self.data), (2, [], []))

    def test_page_loader_skips_records_that_are_not_in_the_format_yet(self):
        self.main_file()
        self.legacy_q6()
        self.assertEqual(len(QR.load_all_valid_runs(self.data)), 2)


class RealRepoExtraFiles(unittest.TestCase):
    def test_real_extra_files_do_not_break_the_normal_gate(self):
        n, errors, _ = G.run_gate()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
