"""Tests for building the CBOM from mapped findings (Issue #8).

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
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import cbom  # noqa: E402
import quantum_mapper as qm  # noqa: E402

SAMPLE = os.path.join(HERE, "data", "sample_findings.json")
FACTS = {"projects": {
    "P": {"padding": {"status": "none (textbook RSA)", "weakness": "deterministic", "source": "Vaibhav"},
          "attack_evidence": ["factored in 0.0002s (test evidence)"]}}}


def f(primitive, project="P", file="a.py", line=1, **kw):
    item = {"project": project, "file": file, "line": line, "primitive": primitive}
    item.update(kw)
    return item


def build(findings, facts=FACTS):
    return cbom.build_cbom(qm.map_findings(findings), facts)


class TestBuildFromSample(unittest.TestCase):
    def setUp(self):
        self.mapped = qm.map_findings(qm.load_findings(SAMPLE))
        self.doc = cbom.build_cbom(self.mapped, None)

    def test_cbom_is_valid(self):
        self.assertEqual(cbom.validate_cbom(self.doc), [])

    def test_counts(self):
        self.assertEqual(self.doc["finding_count"], 10)
        self.assertEqual(len(self.doc["unmapped"]), 1)
        self.assertEqual(self.doc["unmapped"][0]["primitive"], "Blowfish")

    def test_every_finding_is_accounted_for(self):
        covered = sum(len(e["files"]) for e in self.doc["entries"])
        self.assertEqual(covered + len(self.doc["unmapped"]), 10)

    def test_ids_are_sequential(self):
        ids = [e["id"] for e in self.doc["entries"]]
        self.assertEqual(ids, [f"CBOM-{n:03d}" for n in range(1, len(ids) + 1)])

    def test_every_primitive_family_has_a_recommendation(self):
        for e in self.doc["entries"]:
            with self.subTest(entry=e["id"]):
                self.assertTrue(e["recommended_pqc"]["algorithm"])

    def test_output_is_deterministic(self):
        again = cbom.build_cbom(qm.map_findings(qm.load_findings(SAMPLE)), None)
        self.assertEqual(json.dumps(self.doc, sort_keys=True), json.dumps(again, sort_keys=True))


class TestRsaEntries(unittest.TestCase):
    def test_qubit_estimate_uses_2n_plus_3(self):
        doc = build([f("RSA", modulus_bits=1024)])
        self.assertEqual(doc["entries"][0]["quantum_risk"]["logical_qubits_estimate"], 2051)

    def test_recommendation_is_ml_kem_768(self):
        entry = build([f("RSA", modulus_bits=1024)])["entries"][0]
        self.assertEqual(entry["recommended_pqc"]["algorithm"], "ML-KEM-768")
        self.assertIn("AES-256-GCM", entry["recommended_pqc"]["rationale"])

    def test_padding_comes_from_manual_facts_and_stays_out_of_quantum_block(self):
        entry = build([f("RSA", modulus_bits=1024)])["entries"][0]
        self.assertEqual(entry["padding_risk"]["status"], "none (textbook RSA)")
        self.assertNotIn("padding_status", entry["quantum_risk"])
        self.assertNotIn("weakness", entry["quantum_risk"])

    def test_attack_evidence_is_attached_to_rsa_only(self):
        doc = build([f("RSA", modulus_bits=1024), f("AES-256", line=2)])
        rsa, aes = doc["entries"]
        self.assertEqual(rsa["classical_risk"]["evidence"], ["factored in 0.0002s (test evidence)"])
        self.assertEqual(aes["classical_risk"]["evidence"], [])

    def test_padding_falls_back_to_edge_case_flag_in_findings(self):
        doc = cbom.build_cbom(qm.map_findings([f("RSA", project="Q", modulus_bits=1024,
                                                 padding_flag="no OAEP/PKCS1 call near RSA use")]), FACTS)
        padding = doc["entries"][0]["padding_risk"]
        self.assertEqual(padding["status"], "flagged")
        self.assertIn("no OAEP", padding["weakness"])
        self.assertIn("padding_flag", padding["source"])

    def test_padding_unknown_when_nothing_is_known(self):
        doc = cbom.build_cbom(qm.map_findings([f("RSA", project="Q", modulus_bits=1024)]), FACTS)
        self.assertEqual(doc["entries"][0]["padding_risk"]["status"], "unknown")

    def test_different_sizes_in_one_project_give_separate_entries(self):
        doc = build([f("RSA", modulus_bits=256, file="a.py"), f("RSA", modulus_bits=8, file="b.py")])
        sizes = sorted(e["key_size_bits"] for e in doc["entries"])
        self.assertEqual(sizes, [8, 256])

    def test_findings_with_same_size_are_merged_into_one_entry(self):
        doc = build([f("RSA", modulus_bits=256, line=1), f("RSA", modulus_bits=256, line=2)])
        self.assertEqual(len(doc["entries"]), 1)
        self.assertEqual(doc["entries"][0]["files"], ["a.py:1", "a.py:2"])


class TestSizeStatus(unittest.TestCase):
    def test_scanner_reported(self):
        self.assertEqual(build([f("RSA", modulus_bits=2048)])["entries"][0]["size_status"], "scanner-reported")

    def test_prime_size_warning_makes_it_unverified(self):
        entry = build([f("RSA", key_size=16, modulus_bits=None)])["entries"][0]
        self.assertEqual(entry["size_status"], "unverified")
        self.assertTrue(entry["notes"])

    def test_unverified_size_labels_its_own_estimates(self):
        entry = build([f("RSA", key_size=16, modulus_bits=None)])["entries"][0]
        self.assertIn("UNVERIFIED SIZE", entry["quantum_risk"]["estimate_basis"])
        self.assertIn("UNVERIFIED SIZE", entry["classical_risk"]["basis"])

    def test_verified_size_has_no_unverified_label(self):
        entry = build([f("RSA", modulus_bits=2048)])["entries"][0]
        self.assertNotIn("UNVERIFIED", entry["quantum_risk"]["estimate_basis"])

    def test_missing_size_is_unknown(self):
        self.assertEqual(build([f("AES")])["entries"][0]["size_status"], "unknown")

    def test_confirmed_override_makes_it_override_confirmed(self):
        findings = [f("RSA", file="rsa_utils.py", key_size=16, modulus_bits=None)]
        overridden, _ = qm.apply_overrides(findings, [
            {"id": "o", "confirmed": True, "match": {"file_contains": "rsa_utils"}, "set": {"modulus_bits": 256}}])
        entry = cbom.build_cbom(qm.map_findings(overridden), FACTS)["entries"][0]
        self.assertEqual(entry["size_status"], "override-confirmed")
        self.assertEqual(entry["key_size_bits"], 256)


class TestClassicalAssessment(unittest.TestCase):
    def test_rsa_thresholds(self):
        cases = {8: "practically-breakable", 256: "practically-breakable", 512: "practically-breakable",
                 1024: "below-minimum", 2047: "below-minimum", 2048: "meets-minimum", 3072: "meets-minimum"}
        for bits, status in cases.items():
            with self.subTest(bits=bits):
                self.assertEqual(cbom.classical_assessment("RSA", bits)["status"], status)

    def test_rsa_unknown_size(self):
        self.assertEqual(cbom.classical_assessment("RSA", None)["status"], "unknown")

    def test_other_primitives(self):
        self.assertEqual(cbom.classical_assessment("ECC", 256)["status"], "meets-minimum")
        self.assertEqual(cbom.classical_assessment("ECC", 160)["status"], "below-minimum")
        self.assertEqual(cbom.classical_assessment("AES", 128)["status"], "meets-minimum")
        self.assertEqual(cbom.classical_assessment("AES", 64)["status"], "below-minimum")
        self.assertEqual(cbom.classical_assessment("SHA", 256, "SHA-256")["status"], "meets-minimum")
        self.assertEqual(cbom.classical_assessment("SHA", 160, "SHA-1")["status"], "weak-collision-resistance")

    def test_small_rsa_key_is_a_classical_finding_not_only_a_quantum_one(self):
        entry = build([f("RSA", modulus_bits=256)])["entries"][0]
        self.assertEqual(entry["classical_risk"]["status"], "practically-breakable")
        self.assertEqual(entry["quantum_risk"]["algorithm"], qm.SHOR)


class TestNonRsaEntries(unittest.TestCase):
    def test_no_qubit_estimate_for_non_rsa(self):
        for name in ("ECDSA", "DSA", "DH", "AES-256", "SHA-256"):
            with self.subTest(name=name):
                entry = build([f(name, modulus_bits=2048 if name in ("DSA", "DH") else None, key_size=256)])["entries"][0]
                self.assertIsNone(entry["quantum_risk"]["logical_qubits_estimate"])

    def test_padding_not_applicable_outside_rsa(self):
        entry = build([f("ECDSA", key_size=256)])["entries"][0]
        self.assertEqual(entry["padding_risk"]["status"], "not-applicable")

    def test_symmetric_entries_report_grover_halving(self):
        entry = build([f("AES-256")])["entries"][0]
        self.assertEqual(entry["quantum_risk"]["algorithm"], qm.GROVER)
        self.assertEqual(entry["quantum_risk"]["post_quantum_security_bits"], 128)


class TestFilesAndCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.out = os.path.join(self.tmp.name, "cbom.json")

    def test_build_from_files_and_json_round_trip(self):
        doc, mapped = cbom.build_cbom_from_files(SAMPLE)
        cbom.write_cbom_json(doc, self.out)
        with open(self.out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), doc)
        self.assertEqual(len(mapped), 10)

    def test_cli_writes_json_and_returns_zero(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = cbom.main([SAMPLE, "--json", self.out])
        self.assertEqual(code, 0)
        self.assertIn("JSON written", buf.getvalue())
        self.assertTrue(os.path.exists(self.out))

    def test_cli_usage_errors(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cbom.main([]), 2)
            self.assertEqual(cbom.main([SAMPLE, "--json"]), 2)

    def test_repo_manual_facts_file_works_with_the_builder(self):
        facts = os.path.join(HERE, "..", "data", "manual_facts.json")
        if not os.path.exists(facts):
            self.skipTest("data/manual_facts.json not present")
        doc, _ = cbom.build_cbom_from_files(SAMPLE, facts)
        self.assertEqual(cbom.validate_cbom(doc), [])


if __name__ == "__main__":
    unittest.main()
