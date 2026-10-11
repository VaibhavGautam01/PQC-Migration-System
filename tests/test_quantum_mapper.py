"""Unit tests for src/quantum_mapper.py (issues #5, #6)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from quantum_mapper import (  # noqa: E402
    GROVER, SHOR, canonical_primitive, generate_mapping_report,
    map_finding, map_findings,
)


@pytest.mark.parametrize("name,expected", [
    ("RSA", "RSA"), ("RSA-2048", "RSA"), ("rsa_2048", "RSA"),
    ("P256", "ECC"), ("P-256", "ECC"), ("secp256r1", "ECC"),
    ("ED448", "ECC"), ("Ed25519", "ECC"), ("ECDSA", "ECC"),
    ("DSA", "DSA"), ("DH2048", "DH"), ("Diffie-Hellman", "DH"),
    ("AES-256-GCM", "AES"), ("SHA-256", "SHA"), ("HMAC-SHA256", "SHA"),
    ("3DES", "LEGACY_SYMMETRIC"), ("DES-EDE3-CBC", "LEGACY_SYMMETRIC"),
    ("DES", "LEGACY_SYMMETRIC"), ("Blowfish", "LEGACY_SYMMETRIC"),
    ("RC4", "LEGACY_SYMMETRIC"),
    ("DHCP", None), ("DESCRIPTION", None), ("FOO", None),
    ("", None), (None, None),
])
def test_canonical_primitive(name, expected):
    assert canonical_primitive(name) == expected


def test_legacy_routes_to_grover():
    r = map_finding({"primitive": "3DES"})
    assert r["quantum_algorithm"] == GROVER
    assert r["post_quantum_security_bits"] is None
    assert "classically weak" in r["grover_assessment"]


def test_unknown_is_labelled_not_dropped():
    out = map_findings([{"primitive": "FOO"}, {"primitive": "RSA", "key_size": 1024}])
    assert len(out) == 2
    assert out[0]["quantum_algorithm"] == "UNKNOWN"
    assert out[0]["impact"] == "UNKNOWN"


# --- Synthetic ECC example: proves the mapper works beyond RSA ------------
def test_synthetic_ecc_findings():
    findings = [
        {"project": "synthetic", "primitive": "ECDSA", "key_size": 256},
        {"project": "synthetic", "primitive": "P-384"},
        {"project": "synthetic", "primitive": "X25519"},
    ]
    for r in map_findings(findings):
        assert r["canonical_primitive"] == "ECC"
        assert r["quantum_algorithm"] == SHOR
        assert r["impact"] == "BROKEN"
        assert r["post_quantum_security_bits"] == 0
        assert "ML-DSA" in r["pqc_replacement"] or "ML-KEM" in r["pqc_replacement"]


def test_mixed_primitives_route_correctly():
    r = {f["primitive"]: map_finding(f) for f in [
        {"primitive": "RSA", "modulus_bits": 2048},
        {"primitive": "AES-256"},
        {"primitive": "SHA-256"},
    ]}
    assert r["RSA"]["quantum_algorithm"] == SHOR
    assert r["AES-256"]["quantum_algorithm"] == GROVER
    assert r["AES-256"]["post_quantum_security_bits"] == 128
    assert r["SHA-256"]["quantum_algorithm"] == GROVER


def test_modulus_bits_wins_over_key_size():
    r = map_finding({"primitive": "RSA", "modulus_bits": 1024, "key_size": 512})
    assert r["size_used_bits"] == 1024
    assert r["size_warning"] is None


def test_key_size_only_gives_warning():
    r = map_finding({"primitive": "RSA", "key_size": 512})
    assert r["size_warning"]


def test_edge_flag_does_not_change_quantum_fields():
    base = {"primitive": "RSA", "modulus_bits": 1024}
    a = map_finding(base)
    b = map_finding({**base, "edge_flag": "NO_PADDING"})
    for k in ("impact", "quantum_algorithm", "post_quantum_security_bits"):
        assert a[k] == b[k]
    assert b["edge_flag"] == "NO_PADDING"


def test_report_has_padding_flag_column(tmp_path):
    mapped = map_findings([{"project": "P", "primitive": "RSA",
                            "modulus_bits": 1024, "edge_flag": "NO_PADDING",
                            "file": "a.py", "line": 3}])
    out = tmp_path / "report.md"
    generate_mapping_report(mapped, str(out))
    text = out.read_text(encoding="utf-8")
    assert "Padding flag" in text
    assert "NO_PADDING" in text

"""Unit tests for quantum_mapper.py (Issue #5).

Run from the repo root:
    python -m unittest discover -s tests -v
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import quantum_mapper as qm  # noqa: E402

SHOR = qm.SHOR
GROVER = qm.GROVER


class TestCanonicalPrimitive(unittest.TestCase):
    def test_every_primitive_and_alias_is_recognised(self):
        cases = {
            "RSA": "RSA",
            "ECC": "ECC", "ECDSA": "ECC", "ECDH": "ECC",
            "Ed25519": "ECC", "X25519": "ECC",
            "DSA": "DSA",
            "DH": "DH", "Diffie-Hellman": "DH",
            "AES": "AES", "AES-128": "AES", "aes_256_gcm": "AES",
            "SHA": "SHA", "SHA-256": "SHA", "sha1": "SHA", "SHA3-512": "SHA",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(qm.canonical_primitive(name), expected)

    def test_ecdsa_is_not_confused_with_dsa(self):
        self.assertEqual(qm.canonical_primitive("ECDSA"), "ECC")
        self.assertEqual(qm.canonical_primitive("DSA"), "DSA")

    def test_unknown_names_return_none(self):
        for name in ("Twofish", "", "ROT13"):
            with self.subTest(name=name):
                self.assertIsNone(qm.canonical_primitive(name))


class TestMapPrimitive(unittest.TestCase):
    def test_asymmetric_primitives_route_to_shor(self):
        for name in ("RSA", "ECC", "DSA", "DH"):
            with self.subTest(name=name):
                entry = qm.map_primitive(name)
                self.assertEqual(entry["quantum_algorithm"], SHOR)
                self.assertEqual(entry["impact"], "BROKEN")
                self.assertEqual(entry["family"], "asymmetric")

    def test_symmetric_and_hash_route_to_grover(self):
        for name in ("AES", "SHA"):
            with self.subTest(name=name):
                entry = qm.map_primitive(name)
                self.assertEqual(entry["quantum_algorithm"], GROVER)
                self.assertEqual(entry["impact"], "WEAKENED")

    def test_unknown_primitive_returns_none(self):
        self.assertIsNone(qm.map_primitive("ROT13"))

    def test_returned_entry_is_a_copy(self):
        entry = qm.map_primitive("RSA")
        entry["impact"] = "CHANGED"
        self.assertEqual(qm.PRIMITIVE_TABLE["RSA"]["impact"], "BROKEN")


class TestMapFinding(unittest.TestCase):
    def test_rsa(self):
        r = qm.map_finding({"primitive": "RSA", "key_size": 1024})
        self.assertEqual(r["quantum_algorithm"], SHOR)
        self.assertEqual(r["post_quantum_security_bits"], 0)
        self.assertEqual(r["size_used_bits"], 1024)

    def test_ecdsa(self):
        r = qm.map_finding({"primitive": "ECDSA", "key_size": 256})
        self.assertEqual(r["canonical_primitive"], "ECC")
        self.assertEqual(r["quantum_algorithm"], SHOR)

    def test_dsa(self):
        r = qm.map_finding({"primitive": "DSA", "key_size": 2048})
        self.assertEqual(r["canonical_primitive"], "DSA")
        self.assertEqual(r["impact"], "BROKEN")

    def test_diffie_hellman(self):
        r = qm.map_finding({"primitive": "Diffie-Hellman", "key_size": 2048})
        self.assertEqual(r["canonical_primitive"], "DH")
        self.assertEqual(r["quantum_algorithm"], SHOR)

    def test_aes_size_inferred_from_name(self):
        self.assertEqual(qm.map_finding({"primitive": "AES-128"})["post_quantum_security_bits"], 64)
        self.assertEqual(qm.map_finding({"primitive": "AES-256"})["post_quantum_security_bits"], 128)

    def test_aes_size_from_key_size_field(self):
        r = qm.map_finding({"primitive": "AES", "key_size": 192})
        self.assertEqual(r["post_quantum_security_bits"], 96)

    def test_aes_without_size_has_unknown_pq_bits(self):
        self.assertIsNone(qm.map_finding({"primitive": "AES"})["post_quantum_security_bits"])

    def test_sha256_halves_to_128(self):
        r = qm.map_finding({"primitive": "SHA-256"})
        self.assertEqual(r["quantum_algorithm"], GROVER)
        self.assertEqual(r["post_quantum_security_bits"], 128)

    def test_sha1_infers_160_bit_output(self):
        r = qm.map_finding({"primitive": "SHA-1"})
        self.assertEqual(r["size_used_bits"], 160)
        self.assertEqual(r["post_quantum_security_bits"], 80)

    def test_unknown_primitive_is_flagged_not_crashed(self):
        r = qm.map_finding({"primitive": "ROT13"})
        self.assertEqual(r["quantum_algorithm"], "UNKNOWN")
        self.assertEqual(r["impact"], "UNKNOWN")
        self.assertIn("Manual review", r["pqc_replacement"])

    def test_missing_primitive_key_is_treated_as_unknown(self):
        self.assertEqual(qm.map_finding({"file": "x.py"})["impact"], "UNKNOWN")

    def test_modulus_bits_wins_over_key_size(self):
        r = qm.map_finding({"primitive": "RSA", "key_size": 16, "modulus_bits": 256})
        self.assertEqual(r["size_used_bits"], 256)
        self.assertIsNone(r["size_warning"])

    def test_warning_when_only_key_size_is_given_for_rsa(self):
        r = qm.map_finding({"primitive": "RSA", "key_size": 16, "modulus_bits": None})
        self.assertEqual(r["size_used_bits"], 16)
        self.assertIsNotNone(r["size_warning"])

    def test_input_is_not_mutated_and_extra_fields_are_kept(self):
        original = {"primitive": "RSA", "key_size": 1024, "file": "a.py", "line": 7}
        snapshot = dict(original)
        r = qm.map_finding(original)
        self.assertEqual(original, snapshot)
        self.assertEqual(r["file"], "a.py")
        self.assertEqual(r["line"], 7)

    def test_map_findings_preserves_length_and_order(self):
        items = [{"primitive": p} for p in ("RSA", "AES-128", "ROT13", "DH")]
        out = qm.map_findings(items)
        self.assertEqual([o["primitive"] for o in out], ["RSA", "AES-128", "ROT13", "DH"])


class TestFileHelpers(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.findings = [
            {"project": "P1", "file": "a.py", "line": 1, "primitive": "RSA", "modulus_bits": 256},
            {"project": "P2", "file": "b.py", "line": 2, "primitive": "SHA-256"},
        ]

    def _write(self, name, data):
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return path

    def test_load_findings_accepts_list_and_dict_forms(self):
        as_list = self._write("list.json", self.findings)
        as_dict = self._write("dict.json", {"findings": self.findings})
        self.assertEqual(qm.load_findings(as_list), self.findings)
        self.assertEqual(qm.load_findings(as_dict), self.findings)

    def test_map_findings_file_round_trip(self):
        src = self._write("in.json", self.findings)
        dst = os.path.join(self.tmp.name, "out.json")
        mapped = qm.map_findings_file(src, dst)
        with open(dst, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh), mapped)
        self.assertEqual(len(mapped), 2)

    def test_report_is_written_with_expected_content(self):
        mapped = qm.map_findings(self.findings)
        report = os.path.join(self.tmp.name, "report.md")
        qm.generate_mapping_report(mapped, report)
        with open(report, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("# Quantum-Algorithm Mapping Report", text)
        self.assertIn("## P1", text)
        self.assertIn("## P2", text)
        self.assertIn("Shor's algorithm", text)
        self.assertIn("Grover's algorithm", text)


if __name__ == "__main__":
    unittest.main()

