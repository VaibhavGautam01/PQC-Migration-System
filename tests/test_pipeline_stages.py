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
