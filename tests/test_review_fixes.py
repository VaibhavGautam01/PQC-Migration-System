"""Tests for the code-review follow-ups: AES-128 wording, padding flag, legacy CBOM.

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

import cbom  # noqa: E402
import quantum_mapper as qm  # noqa: E402


def f(primitive, project="P", file="a.py", line=1, **kw):
    item = {"project": project, "file": file, "line": line, "primitive": primitive}
    item.update(kw)
    return item


class TestAes128Wording(unittest.TestCase):
    def setUp(self):
        self.text = qm.map_finding({"primitive": "AES-128"})["grover_assessment"]

    def test_does_not_overstate_the_risk(self):
        self.assertNotIn("reduced margin", self.text)
        self.assertIn("not a break", self.text)

    def test_cites_nist_category_1_and_the_gate_estimate(self):
        self.assertIn("category 1", self.text)
        self.assertIn("AES-128 key search", self.text)
        self.assertIn("2^170/MAXDEPTH", self.text)

    def test_other_sizes_keep_their_own_wording(self):
        self.assertIn("comfortable margin", qm.map_finding({"primitive": "AES-256"})["grover_assessment"])
        self.assertIn("reduced margin", qm.map_finding({"primitive": "AES-192"})["grover_assessment"])
        self.assertIn("reduced margin", qm.map_finding({"primitive": "SHA-1"})["grover_assessment"])


class TestPaddingFlagColumn(unittest.TestCase):
    def render(self, findings):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.md")
            qm.generate_mapping_report(qm.map_findings(findings), path)
            with open(path, encoding="utf-8") as fh:
                return fh.read()

    def test_column_header_is_present(self):
        self.assertIn("| Padding flag |", self.render([f("RSA", modulus_bits=1024)]))

    def test_string_flag_is_shown_on_its_row(self):
        text = self.render([f("RSA", modulus_bits=1024, edge_flag="no OAEP/PKCS1 near RSA use")])
        row = [ln for ln in text.splitlines() if ln.startswith("| a.py:1 |")][0]
        self.assertTrue(row.endswith("| no OAEP/PKCS1 near RSA use |"))

    def test_structured_flag_is_shown_as_json(self):
        text = self.render([f("RSA", modulus_bits=1024, edge_flag={"padding": "none"})])
        row = [ln for ln in text.splitlines() if ln.startswith("| a.py:1 |")][0]
        self.assertTrue(row.endswith('| {"padding": "none"} |'))

    def test_missing_flag_shows_a_dash(self):
        row = [ln for ln in self.render([f("RSA", modulus_bits=1024)]).splitlines()
               if ln.startswith("| a.py:1 |")][0]
        self.assertTrue(row.endswith("| - |"))

    def test_flag_does_not_change_the_quantum_result(self):
        plain = qm.map_finding(f("RSA", modulus_bits=1024))
        flagged = qm.map_finding(f("RSA", modulus_bits=1024, edge_flag="textbook RSA"))
        for key in ("quantum_algorithm", "impact", "post_quantum_security_bits", "size_used_bits"):
            self.assertEqual(plain[key], flagged[key])

    def test_report_says_the_flag_is_not_part_of_the_quantum_result(self):
        self.assertIn("not part of the quantum result", self.render([f("RSA", modulus_bits=1024)]))


class TestEdgeFlagInCbom(unittest.TestCase):
    FACTS = {"projects": {"P": {"padding": {"status": "none (textbook RSA)",
                                            "weakness": "deterministic", "source": "Vaibhav"}}}}

    def padding(self, findings, facts=None):
        doc = cbom.build_cbom(qm.map_findings(findings), facts)
        return doc["entries"][0]["padding_risk"]

    def test_edge_flag_is_used_when_there_are_no_manual_facts(self):
        p = self.padding([f("RSA", modulus_bits=1024, edge_flag="no padding found")])
        self.assertEqual(p["status"], "flagged")
        self.assertEqual(p["weakness"], "no padding found")
        self.assertIn("edge_flag", p["source"])
        self.assertEqual(p["automated_flag"], "no padding found")

    def test_manual_facts_win_but_the_automated_flag_is_still_shown(self):
        p = self.padding([f("RSA", modulus_bits=1024, edge_flag="no padding found")], self.FACTS)
        self.assertEqual(p["status"], "none (textbook RSA)")
        self.assertEqual(p["automated_flag"], "no padding found")

    def test_no_flag_means_none_for_automated_flag(self):
        self.assertIsNone(self.padding([f("RSA", modulus_bits=1024)], self.FACTS)["automated_flag"])

    def test_non_rsa_has_no_padding_and_no_flag(self):
        p = self.padding([f("AES-256", edge_flag="ignored")])
        self.assertEqual(p["status"], "not-applicable")
        self.assertIsNone(p["automated_flag"])

    def test_flag_never_leaks_into_the_quantum_block(self):
        doc = cbom.build_cbom(qm.map_findings([f("RSA", modulus_bits=1024, edge_flag="x")]), None)
        entry = doc["entries"][0]
        self.assertEqual(cbom.validate_entry(entry), [])
        self.assertNotIn("automated_flag", entry["quantum_risk"])
        self.assertEqual(entry["quantum_risk"]["logical_qubits_estimate"], 2051)

    def test_structured_flag_is_serialised(self):
        p = self.padding([f("RSA", modulus_bits=1024, edge_flag={"padding": "none"})])
        self.assertEqual(p["automated_flag"], '{"padding": "none"}')


class TestLegacyInCbom(unittest.TestCase):
    def entry(self, name, **kw):
        doc = cbom.build_cbom(qm.map_findings([f(name, **kw)]), None)
        self.assertEqual(cbom.validate_cbom(doc), [])
        return doc["entries"][0]

    def test_legacy_ciphers_get_entries_not_unmapped(self):
        for name in ("3DES", "DES", "RC4", "Blowfish"):
            with self.subTest(name=name):
                doc = cbom.build_cbom(qm.map_findings([f(name)]), None)
                self.assertEqual(doc["entry_count"], 1)
                self.assertEqual(doc["unmapped"], [])

    def test_classical_status_and_recommendation(self):
        self.assertEqual(self.entry("DES")["classical_risk"]["status"], "practically-breakable")
        for name in ("3DES", "RC4", "Blowfish"):
            with self.subTest(name=name):
                e = self.entry(name)
                self.assertEqual(e["classical_risk"]["status"], "below-minimum")
        self.assertIn("AES-256-GCM", self.entry("3DES")["recommended_pqc"]["algorithm"])

    def test_no_qubit_estimate_and_grover_algorithm(self):
        e = self.entry("3DES")
        self.assertIsNone(e["quantum_risk"]["logical_qubits_estimate"])
        self.assertEqual(e["quantum_risk"]["algorithm"], qm.GROVER)
        self.assertEqual(e["quantum_risk"]["post_quantum_security_bits"], 56)

    def test_every_table_primitive_has_a_recommendation(self):
        self.assertEqual(set(cbom.PQC_RECOMMENDATIONS), set(qm.PRIMITIVE_TABLE))

    def test_markdown_renders_legacy_rows(self):
        doc = cbom.build_cbom(qm.map_findings([f("RC4")]), None)
        self.assertIn("| RC4 |", cbom.render_markdown(doc))


if __name__ == "__main__":
    unittest.main()
