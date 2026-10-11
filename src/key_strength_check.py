"""
key_strength_check.py - Classical key-strength check for the PQC Migration
Advisor. Independent of the quantum risk score: a short RSA/DSA/DH key is
breakable by ordinary computers, with no quantum computer involved.

Usage:
  python src/key_strength_check.py outputs/findings.json [--out flags.json]
"""
import json
import sys

MIN_BITS = 2048                      # NIST minimum for RSA/DSA/DH (112-bit security)
ASYMMETRIC = {"RSA", "DSA", "DH"}


def classify(bits):
    """Return (level, reason) for an asymmetric modulus size in bits."""
    if bits is None:
        return "UNKNOWN_SIZE", "no modulus size in the finding"
    if bits <= 512:
        return "CRITICAL", "breakable on ordinary hardware today (RSA-512 was factored in 1999)"
    if bits < 1024:
        return "HIGH", "within reach of academic-scale factoring (RSA-768 was factored in 2009)"
    if bits < MIN_BITS:
        return "MEDIUM", "below the 2048-bit NIST minimum; weak classical margin"
    return "OK", "meets the classical minimum"


def check_finding(f):
    """Return a flag dict for one finding, or None if it is not RSA/DSA/DH."""
    if f.get("primitive") not in ASYMMETRIC:
        return None
    bits = f.get("modulus_bits")
    note = ""
    if bits is None and f.get("key_size"):
        note = f"key_size={f['key_size']} may be a prime size, not the modulus"
    level, reason = classify(bits)
    return {
        "project": f.get("project"), "file": f.get("file"), "line": f.get("line"),
        "primitive": f["primitive"], "modulus_bits": bits,
        "level": level, "reason": reason, "note": note,
    }


def check_findings(findings):
    """Check every finding; return the list of flags."""
    return [x for x in (check_finding(f) for f in findings) if x]


def main():
    if len(sys.argv) < 2:
        print("usage: key_strength_check.py findings.json [--out flags.json]")
        return 2
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    flags = check_findings(data["findings"] if isinstance(data, dict) else data)

    sized = [x for x in flags if x["modulus_bits"] is not None]
    print(f"{len(flags)} RSA/DSA/DH findings, {len(sized)} with a modulus size")
    for x in sorted(sized, key=lambda x: (x["project"] or "", x["modulus_bits"])):
        print(f"  {x['level']:<9} {x['project']} {x['file']}:{x['line']} "
              f"{x['modulus_bits']} bits - {x['reason']}")
    unknown = len(flags) - len(sized)
    if unknown:
        print(f"  {unknown} findings have no modulus size, so they are not rated")

    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
        json.dump(flags, open(out, "w", encoding="utf-8"), indent=2)
        print("saved ->", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())