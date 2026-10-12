"""Tests for connecting the mapper to the real findings.json (Issue #6).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "src"))

import quantum_mapper as qm  # noqa: E402

REAL_FINDINGS = os.path.join(ROOT, "outputs", "findings.json")
SCHEMA_FIELDS = {"project", "file", "line", "primitive", "pattern_id", "confidence",
                 "key_size", "modulus_bits", "size_basis", "snippet"}


def rsa(file="a.py", line=1, **extra):
    base = {"project": "P", "file": file, "line": line, "primitive": "RSA",
            "key_size": 16, "modulus_bits": None}
    base.update(extra)
    return base


class TestValidateFindings(unittest.TestCase):
    def test_clean_list_has_no_problems(self):
        self.assertEqual(qm.validate_findings([rsa(line=1), rsa(line=2)]), [])

    def test_not_a_list(self):
        self.assertEqual(qm.validate_findings({"a": 1}), ["findings is not a list"])

    def test_missing_fields_are_reported(self):
        problems = qm.validate_findings([{"project": "P", "file": "a.py", "line": 1}])
        self.assertEqual(len(problems), 1)
        self.assertIn("primitive", problems[0])

    def test_duplicates_are_reported(self):
        problems = qm.validate_findings([rsa(), rsa()])
        self.assertTrue(any("duplicate" in p for p in problems))

    def test_non_object_entry(self):
        self.assertTrue(any("not an object" in p for p in qm.validate_findings([rsa(), "x"])))


class TestOverrides(unittest.TestCase):
    def ov(self, **kw):
        base = {"id": "o1", "confirmed": True,
                "match": {"project": "P", "file_contains": "rsa_utils", "primitive": "RSA"},
                "set": {"modulus_bits": 256, "size_basis": "manual"}, "source": "test"}
        base.update(kw)
        return base

    def test_confirmed_override_sets_modulus_and_clears_warning(self):
        findings = [rsa(file="src/rsa_utils.py")]
        out, report = qm.apply_overrides(findings, [self.ov()])
        mapped = qm.map_finding(out[0])
        self.assertEqual(mapped["size_used_bits"], 256)
        self.assertIsNone(mapped["size_warning"])
        self.assertEqual(out[0]["override_ids"], ["o1"])
        self.assertEqual(report[0]["matched"], 1)

    def test_unconfirmed_override_changes_nothing(self):
        findings = [rsa(file="src/rsa_utils.py")]
        out, report = qm.apply_overrides(findings, [self.ov(confirmed=False)])
        self.assertIsNone(out[0]["modulus_bits"])
        self.assertEqual(report[0]["matched"], 1)
        self.assertFalse(report[0]["confirmed"])

    def test_only_matching_findings_change(self):
        findings = [rsa(file="src/rsa_utils.py"), rsa(file="src/other.py", line=2)]
        out, _ = qm.apply_overrides(findings, [self.ov()])
        self.assertEqual(out[0]["modulus_bits"], 256)
        self.assertIsNone(out[1]["modulus_bits"])

    def test_override_matching_nothing_is_reported(self):
        _, report = qm.apply_overrides([rsa(file="x.py")], [self.ov()])
        self.assertEqual(report[0]["matched"], 0)

    def test_primitive_alias_matches(self):
        findings = [rsa(file="rsa_utils.py", primitive="rsa")]
        out, _ = qm.apply_overrides(findings, [self.ov()])
        self.assertEqual(out[0]["modulus_bits"], 256)

    def test_unrecognised_match_primitive_never_matches(self):
        ov = self.ov(match={"primitive": "ROT13"})
        _, report = qm.apply_overrides([rsa()], [ov])
        self.assertEqual(report[0]["matched"], 0)

    def test_input_is_not_mutated(self):
        findings = [rsa(file="rsa_utils.py")]
        snapshot = json.dumps(findings, sort_keys=True)
        qm.apply_overrides(findings, [self.ov()])
        self.assertEqual(json.dumps(findings, sort_keys=True), snapshot)


class TestFilesAndCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.findings = os.path.join(self.tmp.name, "f.json")
        self.facts = os.path.join(self.tmp.name, "facts.json")
        self.out = os.path.join(self.tmp.name, "out.json")
        with open(self.findings, "w") as fh:
            json.dump([rsa(file="rsa_utils.py"), rsa(file="b.py", line=2)], fh)
        with open(self.facts, "w") as fh:
            json.dump({"size_overrides": [
                {"id": "o1", "confirmed": True,
                 "match": {"file_contains": "rsa_utils"}, "set": {"modulus_bits": 256}},
                {"id": "o2", "confirmed": False,
                 "match": {"file_contains": "b.py"}, "set": {"modulus_bits": 8}}]}, fh)

    def run_main(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = qm.main(list(args))
        return code, buf.getvalue()

    def test_load_overrides_reads_manual_facts_layout(self):
        self.assertEqual(len(qm.load_overrides(self.facts)), 2)

    def test_cli_applies_confirmed_only_and_prints_status(self):
        code, text = self.run_main(self.findings, self.out, "--overrides", self.facts)
        self.assertEqual(code, 0)
        self.assertIn("OVERRIDE o1: matched 1 finding(s), applied", text)
        self.assertIn("OVERRIDE o2: matched 1 finding(s), NOT applied", text)
        with open(self.out) as fh:
            sizes = [m["size_used_bits"] for m in json.load(fh)]
        self.assertEqual(sizes, [256, 16])

    def test_strict_fails_on_validation_problems(self):
        with open(self.findings, "w") as fh:
            json.dump([{"project": "P"}], fh)
        code, text = self.run_main(self.findings, self.out, "--strict")
        self.assertEqual(code, 1)
        self.assertIn("VALIDATION:", text)

    def test_overrides_flag_without_path_is_a_usage_error(self):
        code, _ = self.run_main(self.findings, self.out, "--overrides")
        self.assertEqual(code, 2)

    def test_manual_facts_file_in_repo_is_valid(self):
        path = os.path.join(ROOT, "data", "manual_facts.json")
        if not os.path.exists(path):
            self.skipTest("data/manual_facts.json not present")
        overrides = qm.load_overrides(path)
        self.assertTrue(overrides)
        for ov in overrides:
            self.assertIn("match", ov)
            self.assertIn("set", ov)


@unittest.skipUnless(os.path.exists(REAL_FINDINGS), "outputs/findings.json not present")
class TestRealFindings(unittest.TestCase):
    """Contract checks against Tarun's real findings.json v1."""

    @classmethod
    def setUpClass(cls):
        cls.findings = qm.load_findings(REAL_FINDINGS)

    def test_file_is_structurally_valid(self):
        self.assertEqual(qm.validate_findings(self.findings), [])

    def test_every_finding_has_the_agreed_schema(self):
        for item in self.findings:
            with self.subTest(file=item.get("file"), line=item.get("line")):
                self.assertTrue(SCHEMA_FIELDS <= set(item), SCHEMA_FIELDS - set(item))

    def test_every_finding_maps_without_error(self):
        mapped = qm.map_findings(self.findings)
        self.assertEqual(len(mapped), len(self.findings))
        for m in mapped:
            self.assertIn("post_quantum_security_bits", m)


if __name__ == "__main__":
    unittest.main()
