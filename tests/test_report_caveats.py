"""Tests for the 'Data caveats' section of the mapping report (Issue #6).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import quantum_mapper as qm  # noqa: E402


def finding(**kw):
    base = {"project": "P", "file": "a.py", "line": 1, "primitive": "RSA", "modulus_bits": 256}
    base.update(kw)
    return base


class TestCollectCaveats(unittest.TestCase):
    def test_clean_data_has_no_caveats(self):
        self.assertEqual(qm.collect_caveats(qm.map_findings([finding()])), [])

    def test_prime_size_warning_becomes_a_caveat(self):
        mapped = qm.map_findings([finding(modulus_bits=None, key_size=16)])
        caveats = qm.collect_caveats(mapped)
        self.assertEqual(len(caveats), 1)
        self.assertIn("prime size", caveats[0])
        self.assertIn("a.py:1", caveats[0])

    def test_missing_size_is_a_caveat_for_sized_primitives_only(self):
        mapped = qm.map_findings([finding(primitive="AES", modulus_bits=None),
                                  finding(primitive="SHA-256", modulus_bits=None, line=2)])
        caveats = qm.collect_caveats(mapped)
        self.assertEqual(len(caveats), 1)
        self.assertIn("AES", caveats[0])

    def test_unknown_primitive_is_a_caveat(self):
        caveats = qm.collect_caveats(qm.map_findings([finding(primitive="ROT13")]))
        self.assertTrue(any("ROT13" in c for c in caveats))
        caveats = qm.collect_caveats(qm.map_findings([finding(primitive="ROT13")]))
        self.assertTrue(any("ROT13" in c for c in caveats))

    def test_unconfirmed_override_is_listed(self):
        report = [{"id": "o1", "confirmed": False, "matched": 2, "source": "Tarun"}]
        caveats = qm.collect_caveats([], report)
        self.assertIn("unconfirmed", caveats[0])
        self.assertIn("Tarun", caveats[0])

    def test_confirmed_override_matching_nothing_is_listed(self):
        report = [{"id": "o2", "confirmed": True, "matched": 0, "source": None}]
        self.assertIn("matched no findings", qm.collect_caveats([], report)[0])

    def test_confirmed_matching_override_is_not_a_caveat(self):
        report = [{"id": "o3", "confirmed": True, "matched": 1, "source": None}]
        self.assertEqual(qm.collect_caveats([], report), [])


class TestReportCaveatSection(unittest.TestCase):
    def render(self, caveats):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "r.md")
            qm.generate_mapping_report(qm.map_findings([finding()]), path, caveats=caveats)
            with open(path, encoding="utf-8") as fh:
                return fh.read()

    def test_section_present_when_caveats_exist(self):
        text = self.render(["Something is unverified."])
        self.assertIn("## Data caveats", text)
        self.assertIn("- Something is unverified.", text)

    def test_section_absent_without_caveats(self):
        self.assertNotIn("## Data caveats", self.render(None))
        self.assertNotIn("## Data caveats", self.render([]))

    def test_caveats_come_before_the_notes_section(self):
        text = self.render(["x"])
        self.assertLess(text.index("## Data caveats"), text.index("## Notes and limitations"))


if __name__ == "__main__":
    unittest.main()
