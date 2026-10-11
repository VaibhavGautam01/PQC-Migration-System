"""
key_strength_check.py - Classical key-strength check for the PQC Migration
Advisor. Independent of the quantum risk score: a short RSA/DSA/DH key is
breakable by ordinary computers, with no quantum computer involved.

For the risk report generator:
    from key_strength_check import check_findings, render_markdown
    section = render_markdown(check_findings(findings))

Usage:
  python src/key_strength_check.py outputs/findings.json [--out flags.json] [--md section.md]
"""
import argparse
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


def render_markdown(flags):
    """Return a 'Classical key strength' Markdown section for the risk report."""
    sized = [x for x in flags if x["modulus_bits"] is not None]
    unsized = len(flags) - len(sized)
    lines = [
        "## Classical key strength", "",
        "These ratings are independent of the quantum risk score. A short "
        "RSA/DSA/DH key can be broken by ordinary computers today, with no "
        "quantum computer involved.", "",
        "| Project | File:line | Modulus (bits) | Rating | Reason |",
        "|---|---|---|---|---|",
    ]
    for x in sorted(sized, key=lambda x: (x["project"] or "", x["file"] or "", x["line"] or 0)):
        lines.append(f"| {x['project']} | {x['file']}:{x['line']} | "
                     f"{x['modulus_bits']} | {x['level']} | {x['reason']} |")
    lines += [
        "",
        f"{unsized} further RSA/DSA/DH findings carry no modulus size and are not rated.",
        "",
        "Sizes are the modulus sizes resolved by the scanner's key-size extraction.",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings")
    ap.add_argument("--out", help="write the flags as JSON")
    ap.add_argument("--md", help="write the Markdown section")
    args = ap.parse_args()

    data = json.load(open(args.findings, encoding="utf-8"))
    flags = check_findings(data["findings"] if isinstance(data, dict) else data)

    sized = [x for x in flags if x["modulus_bits"] is not None]
    print(f"{len(flags)} RSA/DSA/DH findings, {len(sized)} with a modulus size")
    for x in sorted(sized, key=lambda x: (x["project"] or "", x["modulus_bits"])):
        print(f"  {x['level']:<9} {x['project']} {x['file']}:{x['line']} "
              f"{x['modulus_bits']} bits - {x['reason']}")
    unknown = len(flags) - len(sized)
    if unknown:
        print(f"  {unknown} findings have no modulus size, so they are not rated")

    if args.out:
        json.dump(flags, open(args.out, "w", encoding="utf-8"), indent=2)
        print("saved ->", args.out)
    if args.md:
        open(args.md, "w", encoding="utf-8").write(render_markdown(flags))
        print("saved ->", args.md)
    return 0


if __name__ == "__main__":
    sys.exit(main())