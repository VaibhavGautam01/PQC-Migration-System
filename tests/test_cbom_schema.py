"""Tests for the CBOM entry schema and the qubit formula (Issue #8).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import cbom  # noqa: E402


def good_entry():
    return {
        "id": "CBOM-001",
        "project": "P",
        "primitive": "RSA",
        "key_size_bits": 1024,
        "size_basis": "manual",
        "size_status": "override-confirmed",
        "files": ["a.py:10"],
        "quantum_risk": {"algorithm": "Shor's algorithm", "impact": "BROKEN",
                         "logical_qubits_estimate": 2051, "estimate_basis": "2n+3",
                         "post_quantum_security_bits": 0},
        "classical_risk": {"status": "below-minimum", "basis": "x", "evidence": []},
        "padding_risk": {"status": "none (textbook RSA)", "weakness": "deterministic", "source": "Vaibhav"},
        "recommended_pqc": {"algorithm": "ML-KEM-768", "standard": "FIPS 203", "rationale": "x"},
        "notes": [],
    }


def good_cbom():
    return {"cbom_version": "1.0", "project_count": 1, "entry_count": 1, "finding_count": 1,
            "entries": [good_entry()], "unmapped": [], "references": [], "notes": []}


class TestShorQubits(unittest.TestCase):
    def test_known_values(self):
        for bits, expected in {8: 19, 31: 65, 256: 515, 512: 1027, 1024: 2051, 2048: 4099}.items():
            with self.subTest(bits=bits):
                self.assertEqual(cbom.shor_logical_qubits(bits), expected)

    def test_rejects_bad_input(self):
        for bad in (0, -5, 1.5, "1024", None, True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    cbom.shor_logical_qubits(bad)


class TestValidateEntry(unittest.TestCase):
    def test_good_entry_is_valid(self):
        self.assertEqual(cbom.validate_entry(good_entry()), [])

    def test_each_top_level_field_is_required(self):
        for field in cbom.ENTRY_FIELDS:
            with self.subTest(field=field):
                entry = good_entry()
                del entry[field]
                self.assertTrue(any(field in p for p in cbom.validate_entry(entry)))

    def test_each_block_field_is_required(self):
        for block, fields in cbom.BLOCK_FIELDS.items():
            for field in fields:
                with self.subTest(block=block, field=field):
                    entry = good_entry()
                    del entry[block][field]
                    self.assertTrue(any(field in p for p in cbom.validate_entry(entry)))

    def test_bad_values_are_rejected(self):
        cases = {
            "primitive": ("primitive", "ROT13"),
            "size_status": ("size_status", "maybe"),
            "key_size_bits": ("key_size_bits", -4),
            "files": ("files", []),
        }
        for label, (field, value) in cases.items():
            with self.subTest(label=label):
                entry = good_entry()
                entry[field] = value
                self.assertTrue(cbom.validate_entry(entry))

    def test_bad_classical_status_and_qubit_value(self):
        entry = good_entry()
        entry["classical_risk"]["status"] = "kinda-weak"
        self.assertTrue(cbom.validate_entry(entry))
        entry = good_entry()
        entry["quantum_risk"]["logical_qubits_estimate"] = 0
        self.assertTrue(cbom.validate_entry(entry))

    def test_null_size_and_null_qubits_are_allowed(self):
        entry = good_entry()
        entry["key_size_bits"] = None
        entry["quantum_risk"]["logical_qubits_estimate"] = None
        self.assertEqual(cbom.validate_entry(entry), [])

    def test_padding_must_not_leak_into_quantum_risk(self):
        entry = good_entry()
        entry["quantum_risk"]["padding_status"] = "none"
        self.assertTrue(any("padding" in p for p in cbom.validate_entry(entry)))

    def test_risk_blocks_are_separate_objects(self):
        entry = good_entry()
        self.assertTrue({"quantum_risk", "classical_risk", "padding_risk"} <= set(entry))
        self.assertNotIn("status", entry["quantum_risk"])

    def test_non_object_entry(self):
        self.assertEqual(cbom.validate_entry("x"), ["entry is not an object"])


class TestValidateCbom(unittest.TestCase):
    def test_good_cbom_is_valid(self):
        self.assertEqual(cbom.validate_cbom(good_cbom()), [])

    def test_entry_count_mismatch(self):
        doc = good_cbom()
        doc["entry_count"] = 2
        self.assertTrue(any("entry_count" in p for p in cbom.validate_cbom(doc)))

    def test_duplicate_ids(self):
        doc = good_cbom()
        doc["entries"].append(copy.deepcopy(doc["entries"][0]))
        doc["entry_count"] = 2
        self.assertTrue(any("unique" in p for p in cbom.validate_cbom(doc)))

    def test_missing_top_level_field(self):
        doc = good_cbom()
        del doc["references"]
        self.assertTrue(any("references" in p for p in cbom.validate_cbom(doc)))

    def test_entry_problems_are_labelled_with_the_entry_id(self):
        doc = good_cbom()
        doc["entries"][0]["primitive"] = "ROT13"
        self.assertTrue(any(p.startswith("CBOM-001:") for p in cbom.validate_cbom(doc)))


if __name__ == "__main__":
    unittest.main()
