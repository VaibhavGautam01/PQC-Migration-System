"""Tests for the confirmed size decisions, experiments and edge totals.

Covers the team's answers: part1 has two real key paths (256-bit and at most
8-bit), the video project is 'user-selectable, UI default 2048', and Vaibhav's
31/95-bit attack results are local small-key snapshots, not the projects of record.

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

import build_dashboard as bd  # noqa: E402
import cbom  # noqa: E402
import quantum_mapper as qm  # noqa: E402

FACTS_PATH = os.path.join(ROOT, "data", "manual_facts.json")
PART1, VIDEO = "Final-Year-project-part1", "Secure-Video-Steganography"


def f(project, file, line, primitive="RSA", key_size=None, **kw):
    item = {"project": project, "file": file, "line": line, "primitive": primitive,
            "pattern_id": "x", "confidence": "high", "key_size": key_size,
            "modulus_bits": None, "size_basis": None, "snippet": ""}
    item.update(kw)
    return item


# A stand-in for the real findings: sized keygen lines, size-less lines, call sites.
FINDINGS = [
    f(PART1, "src/rsa_utils.py", 27, key_size=128),
    f(PART1, "src/rsa_utils.py", 28, key_size=128),
    f(PART1, "src/rsa_utils.py", 29),                       # phi: no size
    f(PART1, "src/rsa_utils.py", 30, key_size=128),
    f(PART1, "src/rsa_utils.py", 41),                       # pow: no size
    f(PART1, "src/r_channel_stego.py", 12, key_size=8),
    f(PART1, "src/r_channel_stego.py", 20),
    f(VIDEO, "video/rsa.py", 5, key_size=1024),
    f(VIDEO, "video/rsa.py", 9),                            # pow: no size
    f(VIDEO, "video/ui.py", 33, key_size=1024),
]


def facts():
    with open(FACTS_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class TestOverrideMatching(unittest.TestCase):
    def test_lines_condition(self):
        out, rep = qm.apply_overrides(
            [f("P", "a.py", 1), f("P", "a.py", 2), f("P", "a.py", 3)],
            [{"id": "o", "confirmed": True, "match": {"lines": [1, 3]}, "set": {"modulus_bits": 9}}])
        self.assertEqual([x["modulus_bits"] for x in out], [9, None, 9])
        self.assertEqual(rep[0]["matched"], 2)

    def test_has_size_condition_skips_findings_without_any_size(self):
        out, _ = qm.apply_overrides(
            [f("P", "a.py", 1, key_size=16), f("P", "a.py", 2), f("P", "a.py", 3, modulus_bits=5)],
            [{"id": "o", "confirmed": True, "match": {"has_size": True}, "set": {"modulus_bits": 9}}])
        self.assertEqual([x["modulus_bits"] for x in out], [9, None, 9])

    def test_has_size_false_or_missing_means_no_restriction(self):
        out, _ = qm.apply_overrides(
            [f("P", "a.py", 1)],
            [{"id": "o", "confirmed": True, "match": {"has_size": False}, "set": {"modulus_bits": 9}}])
        self.assertEqual(out[0]["modulus_bits"], 9)


class TestRealFactsFile(unittest.TestCase):
    def setUp(self):
        self.out, self.report = qm.apply_overrides(FINDINGS, facts()["size_overrides"])
        self.by_loc = {(x["file"], x["line"]): x for x in self.out}

    def test_every_override_is_confirmed_and_has_a_source(self):
        for ov in facts()["size_overrides"]:
            with self.subTest(id=ov["id"]):
                self.assertTrue(ov["confirmed"])
                self.assertTrue(ov["source"])

    def test_part1_keygen_override_hits_only_lines_27_28_30(self):
        for line in (27, 28, 30):
            self.assertEqual(self.by_loc[("src/rsa_utils.py", line)]["modulus_bits"], 256)
        self.assertIsNone(self.by_loc[("src/rsa_utils.py", 29)]["modulus_bits"])
        self.assertIsNone(self.by_loc[("src/rsa_utils.py", 41)]["modulus_bits"])
        matched = {r["id"]: r["matched"] for r in self.report}
        self.assertEqual(matched["part1-keygen-256"], 3)

    def test_part1_rchannel_override_gives_8_bits(self):
        self.assertEqual(self.by_loc[("src/r_channel_stego.py", 12)]["modulus_bits"], 8)

    def test_video_override_only_touches_findings_that_already_have_a_size(self):
        self.assertEqual(self.by_loc[("video/rsa.py", 5)]["modulus_bits"], 2048)
        self.assertEqual(self.by_loc[("video/ui.py", 33)]["modulus_bits"], 2048)
        self.assertIsNone(self.by_loc[("video/rsa.py", 9)]["modulus_bits"])

    def test_the_31_and_95_bit_figures_never_become_key_sizes(self):
        sizes = {x["modulus_bits"] for x in self.out}
        self.assertFalse({31, 95} & sizes)


class TestCbomFromDecisions(unittest.TestCase):
    def setUp(self):
        out, _ = qm.apply_overrides(FINDINGS, facts()["size_overrides"])
        self.doc = cbom.build_cbom(qm.map_findings(out), facts())
        self.rsa = {(e["project"], e["key_size_bits"]): e for e in self.doc["entries"]}

    def test_cbom_is_valid(self):
        self.assertEqual(cbom.validate_cbom(self.doc), [])

    def test_entries_use_the_confirmed_sizes(self):
        self.assertEqual(self.rsa[(PART1, 256)]["size_status"], "override-confirmed")
        self.assertEqual(self.rsa[(PART1, 8)]["size_status"], "override-confirmed")
        self.assertEqual(self.rsa[(VIDEO, 2048)]["size_status"], "override-confirmed")

    def test_qubit_estimates_follow_the_confirmed_sizes(self):
        self.assertEqual(self.rsa[(PART1, 256)]["quantum_risk"]["logical_qubits_estimate"], 515)
        self.assertEqual(self.rsa[(PART1, 8)]["quantum_risk"]["logical_qubits_estimate"], 19)
        self.assertEqual(self.rsa[(VIDEO, 2048)]["quantum_risk"]["logical_qubits_estimate"], 4099)

    def test_size_less_lines_stay_in_their_own_unknown_entry(self):
        self.assertEqual(self.rsa[(PART1, None)]["size_status"], "unknown")
        self.assertEqual(self.rsa[(VIDEO, None)]["size_status"], "unknown")

    def test_video_entry_says_the_size_is_user_selectable(self):
        text = " ".join(self.rsa[(VIDEO, 2048)]["notes"])
        self.assertIn("user-selectable", text)
        self.assertIn("UI default", text)
        self.assertIn("below the 2048-bit minimum", text)

    def test_part1_entries_mention_both_real_key_paths_and_the_unused_default(self):
        text = " ".join(self.rsa[(PART1, 256)]["notes"])
        self.assertIn("generate_keypair(bits=128)", text)
        self.assertIn("generate_small_keypair()", text)
        self.assertIn("n < 256", text)
        self.assertIn("not used", text)

    def test_classical_risk_reflects_the_confirmed_sizes(self):
        self.assertEqual(self.rsa[(PART1, 256)]["classical_risk"]["status"], "practically-breakable")
        self.assertEqual(self.rsa[(PART1, 8)]["classical_risk"]["status"], "practically-breakable")
        self.assertEqual(self.rsa[(VIDEO, 2048)]["classical_risk"]["status"], "meets-minimum")


class TestExperiments(unittest.TestCase):
    def setUp(self):
        self.doc = cbom.build_cbom(qm.map_findings(FINDINGS), facts())

    def test_both_experiments_are_in_the_cbom(self):
        self.assertEqual({e["key_bits"] for e in self.doc["experiments"]}, {31, 95})

    def test_every_experiment_is_labelled_not_the_project_of_record(self):
        for exp in self.doc["experiments"]:
            self.assertIn("local small-key snapshot", exp["target"])
            self.assertIn("not the project of record", exp["target"])

    def test_experiments_are_never_attached_to_entries(self):
        for entry in self.doc["entries"]:
            self.assertEqual(entry["classical_risk"]["evidence"], [])
            self.assertNotIn("0.0002", json.dumps(entry))

    def test_validation_rejects_an_unlabelled_experiment(self):
        bad = copy.deepcopy(self.doc)
        bad["experiments"][0]["target"] = "the image project"
        self.assertTrue(any("not the project of record" in p for p in cbom.validate_cbom(bad)))

    def test_validation_rejects_a_missing_experiment_field(self):
        bad = copy.deepcopy(self.doc)
        del bad["experiments"][0]["result"]
        self.assertTrue(any("result" in p for p in cbom.validate_cbom(bad)))

    def test_markdown_has_the_experiments_section_with_the_warning(self):
        text = cbom.render_markdown(self.doc)
        self.assertIn("## Supporting experiments (local small-key snapshots)", text)
        self.assertIn("not on the projects of record", text)
        self.assertIn("31-bit modulus factored in 0.0002 s", text)

    def test_no_experiments_section_when_there_are_none(self):
        text = cbom.render_markdown(cbom.build_cbom(qm.map_findings(FINDINGS), None))
        self.assertNotIn("## Supporting experiments", text)

    def test_consistency_check_still_passes(self):
        mapped = qm.map_findings(FINDINGS)
        self.assertEqual(cbom.check_consistency(cbom.build_cbom(mapped, facts()), mapped), [])


class TestDashboardWithDecisions(unittest.TestCase):
    def build(self, totals=True):
        data = {"findings": FINDINGS}
        if totals:
            data["edge_case_totals"] = {"padding": 4, "indirect_usage": 10}
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = os.path.join(tmp.name, "findings.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return bd.build_context(path, FACTS_PATH)

    def test_edge_case_totals_are_shown_in_detection(self):
        text = bd.render_detection(self.build())
        self.assertIn("Edge-case module totals: indirect usage 10, padding 4", text)
        self.assertIn("confirmed by hand", text)

    def test_no_totals_line_when_the_file_has_none(self):
        self.assertNotIn("Edge-case module totals", bd.render_detection(self.build(totals=False)))

    def test_list_shaped_findings_file_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "f.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(FINDINGS, fh)
            ctx = bd.build_context(path, FACTS_PATH)
        self.assertIsNone(ctx["edge_totals"])

    def test_risk_section_lists_experiments_with_their_label(self):
        text = bd.render_risk(self.build())
        self.assertIn("**Supporting experiments** (local small-key snapshots, not the projects of record)", text)
        self.assertIn("31-bit modulus factored in 0.0002 s", text)

    def test_detection_reports_all_three_overrides_as_applied(self):
        self.assertIn("3 confirmed and applied, 0 unconfirmed", bd.render_detection(self.build()))

    def test_cli_still_works_with_the_real_facts_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            findings = os.path.join(tmp, "f.json")
            out = os.path.join(tmp, "d.md")
            with open(findings, "w", encoding="utf-8") as fh:
                json.dump({"findings": FINDINGS, "edge_case_totals": {"padding": 4}}, fh)
            with contextlib.redirect_stdout(io.StringIO()):
                code = bd.main([findings, "--facts", FACTS_PATH, "--out", out])
            self.assertEqual(code, 0)
            with open(out, encoding="utf-8") as fh:
                self.assertIn("Supporting experiments", fh.read())


if __name__ == "__main__":
    unittest.main()
