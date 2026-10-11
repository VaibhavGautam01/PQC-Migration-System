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
