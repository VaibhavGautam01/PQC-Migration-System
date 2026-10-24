import json
import tempfile
import unittest
from pathlib import Path

import run_pipeline
from src import risk_run


def names(project):
    return [title for title, _ in run_pipeline.build_steps(project)]


class PipelineStageTests(unittest.TestCase):
    def test_stage_order_scan_then_risk_then_report_then_tests(self):
        n = names("both")
        scan = next(i for i, t in enumerate(n) if "Scan" in t)
        risk = next(i for i, t in enumerate(n) if "Risk score" in t)
        report = next(i for i, t in enumerate(n) if "Mapper" in t)
        self.assertLess(scan, risk)
        self.assertLess(risk, report)

    def test_tests_run_last(self):
        for p in run_pipeline.PROJECTS:
            self.assertIn("Test suite", names(p)[-1])

    def test_risk_stage_receives_the_project(self):
        for p in run_pipeline.PROJECTS:
            args = next(a for t, a in run_pipeline.build_steps(p) if "Risk score" in t)
            self.assertEqual(args[args.index("--project") + 1], p)

    def test_single_project_never_overwrites_committed_scores(self):
        for p in ("image", "video"):
            args = next(a for t, a in run_pipeline.build_steps(p) if "Risk score" in t)
            self.assertIn("--out", args)
            self.assertNotEqual(Path(args[args.index("--out") + 1]).name, "risk_scores.json")
        args = next(a for t, a in run_pipeline.build_steps("both") if "Risk score" in t)
        self.assertNotIn("--out", args)

    def test_full_stage_order(self):
        order = ["Scan", "Risk score", "Mapper", "advisor report", "Before/after", "Evidence gate", "Test suite"]
        for p in run_pipeline.PROJECTS:
            n = names(p)
            idx = [next(i for i, t in enumerate(n) if key in t) for key in order]
            self.assertEqual(idx, sorted(idx), p)

    def test_stage_titles_are_numbered_in_order(self):
        for p in run_pipeline.PROJECTS:
            self.assertEqual([t.split(".")[0] for t in names(p)], [str(i) for i in range(1, len(names(p)) + 1)])

    def test_before_after_stage_follows_the_project(self):
        self.assertEqual([t for t in names("image") if "Before/after" in t].__len__(), 1)
        self.assertIn("(image)", next(t for t in names("image") if "Before/after" in t))
        self.assertIn("(video)", next(t for t in names("video") if "Before/after" in t))
        self.assertEqual(len([t for t in names("both") if "Before/after" in t]), 2)

    def test_evidence_gate_stage_runs_the_gate_module(self):
        args = next(a for t, a in run_pipeline.build_steps("both") if "Evidence gate" in t)
        self.assertEqual(args, ["-m", "src.evidence_gate"])

    def test_outputs_checked_per_project(self):
        names_ = lambda p: {x.name for x in run_pipeline.outputs_for(p)}  # noqa: E731
        self.assertIn("before_after_image.json", names_("image"))
        self.assertNotIn("before_after_video.json", names_("image"))
        self.assertIn("before_after_video.json", names_("video"))
        self.assertNotIn("risk_scores.json", names_("video"))
        self.assertTrue({"risk_scores.json", "before_after_image.json", "before_after_video.json",
                         "pqc_advisor_report.md", "findings.json", "risk_report.md"} <= names_("both"))

    def test_every_stage_script_exists(self):
        for p in run_pipeline.PROJECTS:
            for title, args in run_pipeline.build_steps(p):
                if args[0] != "-m":
                    self.assertTrue((run_pipeline.ROOT / args[0]).is_file(), (title, args[0]))

    def test_input_option_is_a_clear_not_built_yet_message(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_pipeline.main(["--input", "some_image.png"])
        self.assertEqual(code, 2)
        self.assertIn("not implemented yet", buf.getvalue())

    def test_unknown_project_rejected(self):
        with self.assertRaises(ValueError):
            run_pipeline.build_steps("audio")
        with self.assertRaises(SystemExit):
            run_pipeline.main(["--project", "audio"])

    def test_risk_run_out_option_writes_only_that_project(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "r.json"
            risk_run.main(["--project", "video", "--out", str(out)])
            self.assertEqual(list(json.loads(out.read_text())["projects"]), ["video"])


if __name__ == "__main__":
    unittest.main()
