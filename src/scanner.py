#!/usr/bin/env python3
"""
scanner.py - Stage 1 of the PQC Migration Advisor pipeline.

Day 1 scope: RSA signature detection.
(ECC / AES / SHA signatures are added in Week 1, Day 3.)

Usage:
    python src/scanner.py <path-to-repo> [--out outputs/findings.json]
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

SCANNER_VERSION = "0.3.0"

SCAN_EXTENSIONS = {
    ".py", ".java", ".js", ".ts", ".c", ".cpp", ".h", ".go", ".rs",
    ".php", ".rb", ".cs", ".sh", ".pem", ".key", ".pub",
}
SKIP_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", "build", "dist"}
MAX_FILE_BYTES = 1_000_000
KEY_SIZE_LOOKAHEAD = 3  # lines to look ahead for key_size= / bits= arguments

# Each pattern: id, regex, description, confidence, keygen (does it create a key?)
RSA_PATTERNS = [
    # --- Key generation (key size can usually be extracted) ---
    {"id": "RSA-GEN-PYCRYPTODOME",
     "regex": r"\bRSA\.generate\s*\(\s*(?P<bits>\d+)?",
     "desc": "RSA key generation (PyCryptodome)", "confidence": "high", "keygen": True},
    {"id": "RSA-GEN-CRYPTOGRAPHY",
     "regex": r"\brsa\.generate_private_key\s*\(",
     "desc": "RSA key generation (cryptography lib)", "confidence": "high", "keygen": True},
    {"id": "RSA-GEN-PYTHON-RSA",
     "regex": r"\brsa\.newkeys\s*\(\s*(?P<bits>\d+)?",
     "desc": "RSA key generation (python-rsa)", "confidence": "high", "keygen": True},
    {"id": "RSA-GEN-JAVA",
     "regex": r'KeyPairGenerator\.getInstance\(\s*"RSA"',
     "desc": "RSA key generation (Java KeyPairGenerator)", "confidence": "high", "keygen": True},
    {"id": "RSA-GEN-OPENSSL-CLI",
     "regex": r"openssl\s+genrsa(?:\s+-\w+)*\s+(?P<bits>\d+)",
     "desc": "RSA key generation (openssl genrsa)", "confidence": "high", "keygen": True},
    {"id": "RSA-GEN-SSHKEYGEN",
     "regex": r"ssh-keygen\s+.*-t\s+rsa",
     "desc": "RSA key generation (ssh-keygen)", "confidence": "high", "keygen": True},

    # --- Library imports ---
    {"id": "RSA-IMPORT-PYCRYPTODOME",
     "regex": r"from\s+Crypto(?:dome)?\.PublicKey\s+import\s+.*\bRSA\b",
     "desc": "Imports RSA from PyCryptodome", "confidence": "medium", "keygen": False},
    {"id": "RSA-IMPORT-PYTHON-RSA",
     "regex": r"^\s*import\s+rsa\b",
     "desc": "Imports python-rsa library", "confidence": "medium", "keygen": False},
    {"id": "RSA-IMPORT-CRYPTOGRAPHY",
     "regex": r"from\s+cryptography\.hazmat\.primitives\.asymmetric\s+import\s+.*\brsa\b",
     "desc": "Imports rsa from cryptography lib", "confidence": "medium", "keygen": False},
    {"id": "RSA-CIPHER-JAVA",
     "regex": r'Cipher\.getInstance\(\s*"RSA',
     "desc": "RSA cipher usage (Java Cipher)", "confidence": "high", "keygen": False},

    # --- Textbook / hand-rolled RSA ---
    {"id": "RSA-MANUAL-PRIME",
     "regex": r"\bgetPrime\s*\(\s*(?P<bits>\d+)",
     "desc": "Prime generation, possible hand-rolled RSA key", "confidence": "medium", "keygen": True},
    {"id": "RSA-MANUAL-PHI",
     "regex": r"\b(?:phi|totient)\w*\s*=\s*\(?\s*p\s*-\s*1\s*\)?\s*\*\s*\(?\s*q\s*-\s*1",
     "desc": "Euler totient (p-1)(q-1), textbook RSA key setup", "confidence": "high", "keygen": False},
    {"id": "RSA-MANUAL-MODINV",
     "regex": r"\bpow\s*\(\s*\w+\s*,\s*-1\s*,",
     "desc": "Modular inverse via pow(e,-1,phi), private-exponent computation", "confidence": "medium", "keygen": False},
    {"id": "RSA-MODEXP",
     "regex": r"\bpow\s*\((?!\s*\w+\s*,\s*-1\s*,).+,.+,.+\)",
     "desc": "3-argument modular exponentiation, possible textbook RSA encrypt/decrypt",
     "confidence": "low", "keygen": False},
    {"id": "RSA-MANUAL-PRIME-LIB",
     "regex": r"(?<!def )\b(?:randprime|nextprime|generate_prime)\s*\(\s*(?:2\s*\*\*\s*\d+\s*,\s*2\s*\*\*\s*(?P<bits>\d+))?",
     "desc": "Prime generation via library helper, possible hand-rolled RSA key",
     "confidence": "medium", "keygen": True},
    {"id": "RSA-MANUAL-INVFUNC",
     "regex": r"\b(?:mod_inverse|modinv|modinverse|invmod|inverse_mod)\s*\(",
     "desc": "Modular inverse helper call, private-exponent computation",
     "confidence": "medium", "keygen": False},
    {"id": "RSA-MANUAL-MODPOW-OP",
     "regex": r"\(?\s*[A-Za-z_]\w*\s*\*\*\s*[A-Za-z_]\w*\s*\)?\s*%\s*[A-Za-z_]\w*",
     "desc": "(x ** k) % n, textbook modular exponentiation without pow()",
     "confidence": "low", "keygen": False},
    {"id": "RSA-PUBLIC-EXP",
     "regex": r"\b(?:65537|0x10001)\b",
     "desc": "Common RSA public exponent e = 65537",
     "confidence": "low", "keygen": False},

    # --- Key material ---
    {"id": "RSA-PEM-KEY",
     "regex": r"-----BEGIN (?:RSA )?(?:PRIVATE|PUBLIC) KEY-----",
     "desc": "PEM-encoded RSA key material", "confidence": "high", "keygen": False},
]

KEY_SIZE_REGEXES = [
    re.compile(r"key_size\s*=\s*(\d+)"),
    re.compile(r"\bbits\s*=\s*(\d+)"),
    re.compile(r"\binitialize\s*\(\s*(\d+)"),
]

# Day 3: baaki primitives (ECC/DSA/DH/AES/SHA) alag file se aate hain
try:
    from extra_patterns import EXTRA_PATTERNS
except ImportError:
    from src.extra_patterns import EXTRA_PATTERNS

# Purane RSA patterns mein "primitive" key nahi thi, ab sab mein "RSA" lagao
for _p in RSA_PATTERNS:
    _p.setdefault("primitive", "RSA")

# Scanner ab is ek list par chalega: RSA + baaki sab
ALL_PATTERNS = RSA_PATTERNS + EXTRA_PATTERNS

# Regex ek baar compile karo (har line par dobara compile karna slow hota hai)
for _p in ALL_PATTERNS:
    _p["compiled"] = re.compile(_p["regex"])


def extract_key_size(lines, idx, match):
    """Return the key size (int) for a key-generation match, or None."""
    bits = match.groupdict().get("bits")
    if bits:
        return int(bits)
    window = " ".join(lines[idx: idx + 1 + KEY_SIZE_LOOKAHEAD])
    for rx in KEY_SIZE_REGEXES:
        m = rx.search(window)
        if m:
            return int(m.group(1))
    return None


def scan_file(path, root):
    """Scan one file and return a list of finding dicts."""
    try:
        if os.path.getsize(path) > MAX_FILE_BYTES:
            return []
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.read().splitlines()
    except OSError:
        return []

    rel_path = os.path.relpath(path, root).replace(os.sep, "/")
    findings = []
    for idx, line in enumerate(lines):
        for pat in ALL_PATTERNS:
            m = pat["compiled"].search(line)
            if not m:
                continue
            findings.append({
                "file": rel_path,
                "line": idx + 1,
                "primitive": pat["primitive"],
                "pattern_id": pat["id"],
                "description": pat["desc"],
                "confidence": pat["confidence"],
                "key_size": extract_key_size(lines, idx, m) if pat["keygen"] else None,
                "snippet": line.strip()[:200],
            })
    return findings


def scan_path(root):
    """Walk a directory (or single file) and scan every eligible source file."""
    root = os.path.abspath(root)
    findings = []
    if os.path.isfile(root):
        return scan_file(root, os.path.dirname(root))
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if os.path.splitext(name)[1].lower() in SCAN_EXTENSIONS:
                findings.extend(scan_file(os.path.join(dirpath, name), root))
    return findings


def build_report(root, findings):
    return {
        "scanner_version": SCANNER_VERSION,
        "scan_root": os.path.abspath(root),
        "summary": {
            "total_findings": len(findings),
            "files_with_findings": len({f["file"] for f in findings}),
            "by_pattern": dict(Counter(f["pattern_id"] for f in findings)),
            "by_primitive": dict(Counter(f["primitive"] for f in findings)),
        },
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description="Scan a codebase for quantum-vulnerable crypto (RSA).")
    parser.add_argument("path", help="Directory or file to scan")
    parser.add_argument("--out", help="Write findings JSON to this path")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"error: path not found: {args.path}", file=sys.stderr)
        return 1

    report = build_report(args.path, scan_path(args.path))
    s = report["summary"]
    print(f"Scanned: {report['scan_root']}")
    print(f"Findings: {s['total_findings']} in {s['files_with_findings']} file(s)")
    print("By primitive: " + ", ".join(f"{k}={v}" for k, v in sorted(s["by_primitive"].items())))
    for pid, n in sorted(s["by_pattern"].items()):
        print(f"  {pid}: {n}")

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"Saved -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
