import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import repo_check as rc  # type: ignore # noqa: E402


def make_repo(root, findings=31, readme=None, final=None, weights="v1.0", lock="v1.0", model=None):
    root = Path(root)
    for d in ("outputs", "data", "docs"):
        (root / d).mkdir(exist_ok=True)
    (root / "outputs" / "findings.json").write_text(json.dumps({"findings": [{}] * findings}), encoding="utf-8")
    (root / "data" / "risk_weights.json").write_text(json.dumps({"version": weights}), encoding="utf-8")
    (root / "data" / "risk_weights.lock.json").write_text(json.dumps({"version": lock}), encoding="utf-8")
    (root / "README.md").write_text(readme if readme is not None else
                                    f"Scanner: {findings} findings. Weights (frozen as {weights}, see x).", encoding="utf-8")
    (root / "docs" / "final_report.md").write_text(final if final is not None else
                                                   f"**{findings} findings**, RSA {findings - 1} and SHA 1.", encoding="utf-8")
    (root / "docs" / "risk_model.md").write_text(model if model is not None else f"# Risk Model ({weights})\n", encoding="utf-8")


class RepoCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def problems(self, **kw):
        make_repo(self.root, **{k: v for k, v in kw.items() if k != "tracked"})
        return rc.run_checks(self.root, tracked=kw.get("tracked", []))[1]

    def test_consistent_repo_has_no_problems(self):
        self.assertEqual(self.problems(), [])

    def test_wrong_findings_count_is_found(self):
        p = self.problems(readme="The scanner finds 26 findings.", final="**31 findings**")
        self.assertTrue(any("README.md: says 26 findings" in x for x in p))

    def test_per_type_counts_are_not_mistaken_for_the_total(self):
        self.assertEqual(self.problems(final="**31 findings** (RSA 30 and SHA 1). RSA (30 findings) maps to Shor."), [])

    def test_weights_version_mismatch_in_readme_model_and_lock(self):
        p = self.problems(readme="(frozen as v0.1, see x)", model="# Risk Model (v0.1)\n", lock="v0.1")
        text = "\n".join(p)
        self.assertIn("README.md: names weights v0.1", text)
        self.assertIn("docs/risk_model.md: names weights v0.1", text)
        self.assertIn("lock.json has version v0.1", text)

    def test_stale_text_is_found(self):
        p = self.problems(final="**31 findings**. 372 tests pass. Used about 8 bits.")
        self.assertTrue(any("372 tests" in x for x in p))
        self.assertTrue(any("about 8 bits" in x for x in p))

    def test_tracked_generated_files_are_found(self):
        p = self.problems(tracked=["README.md", "legacy_log.txt", "docs/risk_report_sections.md", "outputs/tmp_x.json", "src/a.py"])
        text = "\n".join(p)
        for f in ("legacy_log.txt", "docs/risk_report_sections.md", "outputs/tmp_x.json"):
            self.assertIn(f, text)
        self.assertNotIn("src/a.py", text)

    def test_no_git_skips_the_tracked_check_without_failing(self):
        make_repo(self.root)
        notes, problems = rc.run_checks(self.root, tracked=None)
        self.assertEqual(problems, [])
        self.assertTrue(any(n.startswith("SKIP: git") for n in notes))

    def test_open_fill_markers_are_listed_but_not_a_failure(self):
        make_repo(self.root)
        (self.root / "docs" / "report").mkdir()
        (self.root / "docs" / "report" / "c.md").write_text("A FILL here and FILL there", encoding="utf-8")
        notes, problems = rc.run_checks(self.root, tracked=[])
        self.assertEqual(problems, [])
        self.assertIn("docs/report/c.md: 2 FILL marker(s) still open", notes)

    def test_badge_test_count_is_read_from_the_readme(self):
        make_repo(self.root, readme="![Tests](https://x/Tests-858_passing-green)")
        self.assertEqual(rc.badge_test_count(self.root), 858)

    def test_release_gate_lists_open_markers_and_a_failing_evidence_gate(self):
        make_repo(self.root)
        (self.root / "docs" / "report").mkdir()
        (self.root / "docs" / "report" / "c.md").write_text("text FILL here\nCONFIRM WITH SIR: java\nclean line\n", encoding="utf-8")
        data = self.root / "data"
        (data / "quantum_runs.json").write_text(json.dumps({"schema_version": 1, "runs": []}), encoding="utf-8")
        (data / "quantum_runs_q6.json").write_text(json.dumps([{"algorithm": "BB84"}]), encoding="utf-8")
        problems = rc.check_release(self.root, data_dir=data)
        text = "\n".join(problems)
        self.assertIn("open FILL marker at docs/report/c.md:1", text)
        self.assertIn("open CONFIRM WITH SIR marker at docs/report/c.md:2", text)
        self.assertIn("quantum_runs_q6.json", text)
        self.assertNotIn("c.md:3", text)

    def test_release_gate_passes_on_a_clean_tree(self):
        make_repo(self.root)
        (self.root / "data" / "quantum_runs.json").write_text(json.dumps({"schema_version": 1, "runs": []}), encoding="utf-8")
        self.assertEqual([p for p in rc.check_release(self.root, data_dir=self.root / "data")
                          if not p.startswith("uncommitted")], [])

    def test_test_folders_match_run_tests(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import run_tests  # type: ignore
        self.assertEqual(rc.TEST_DIRS, [p.name for p in run_tests.TEST_DIRS])

    def test_missing_files_do_not_crash(self):
        notes, problems = rc.run_checks(self.root, tracked=[])
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
