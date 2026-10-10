"""quantum_mapper.py - Stage 2 of the PQC Migration Advisor pipeline.

Pipeline position:
    scanner (findings.json) -> quantum_mapper -> qubit_estimator -> risk report

Takes the classical-crypto findings from the Stage 1 scanner and attaches, to
each one, the quantum algorithm that threatens it, the post-quantum security
level, and a recommended PQC replacement.

    Asymmetric (RSA, ECC, DSA, DH)  -> Shor's algorithm   -> broken
    Symmetric / hash (AES, SHA)     -> Grover's algorithm -> security roughly halved

Input
    A list of dicts with at least "primitive". Optional: "modulus_bits" and
    "key_size". For RSA/DSA/DH, modulus_bits is preferred, because the
    scanner's key_size can be the PRIME size rather than the modulus size.

Output
    The same dicts plus: canonical_primitive, family, quantum_algorithm,
    hard_problem, impact, pqc_replacement, post_quantum_security_bits,
    size_used_bits, size_warning, grover_assessment, mapper_note.

Usage
    python src/quantum_mapper.py                          demo with dummy data
    python src/quantum_mapper.py IN.json OUT.json         map a findings file
    python src/quantum_mapper.py IN.json OUT.json REPORT.md [--draft]

Limits
    This is a theory-level mapping: it says which quantum attack applies, not
    that the attack is practical today. Padding weaknesses (e.g. textbook RSA)
    and classical key-strength problems are separate findings, reported
    elsewhere. Standard library only.
"""

import json
import re
import sys
from copy import deepcopy

__all__ = [
    "SHOR", "GROVER", "PRIMITIVE_TABLE", "ALIASES", "FAMILY_TO_ALGORITHM",
    "canonical_primitive", "map_primitive", "route_algorithm", "grover_assessment",
    "map_finding", "map_findings", "load_findings", "map_findings_file",
    "summarise", "generate_mapping_report", "main",
]

# Quantum algorithm labels used throughout the pipeline.
SHOR = "Shor's algorithm"
GROVER = "Grover's algorithm"

# ---------------------------------------------------------------------------
# The mapping table
# ---------------------------------------------------------------------------
PRIMITIVE_TABLE = {
    "RSA": {
        "family": "asymmetric",
        "quantum_algorithm": SHOR,
        "hard_problem": "Integer factorisation",
        "impact": "BROKEN",
        "pqc_replacement": "ML-KEM (encryption/key exchange), ML-DSA (signatures)",
        "note": "Shor's algorithm factors N in polynomial time; any key size "
                "falls once a large enough fault-tolerant quantum computer exists.",
    },
    "ECC": {
        "family": "asymmetric",
        "quantum_algorithm": SHOR,
        "hard_problem": "Elliptic-curve discrete logarithm (ECDLP)",
        "impact": "BROKEN",
        "pqc_replacement": "ML-KEM (ECDH replacement), ML-DSA (ECDSA/EdDSA replacement)",
        "note": "Shor's variant for ECDLP; ECC needs fewer qubits than RSA "
                "for comparable classical strength.",
    },
    "DSA": {
        "family": "asymmetric",
        "quantum_algorithm": SHOR,
        "hard_problem": "Discrete logarithm (finite field)",
        "impact": "BROKEN",
        "pqc_replacement": "ML-DSA",
        "note": "Signature scheme based on discrete log; broken by Shor's.",
    },
    "DH": {
        "family": "asymmetric",
        "quantum_algorithm": SHOR,
        "hard_problem": "Discrete logarithm (finite field)",
        "impact": "BROKEN",
        "pqc_replacement": "ML-KEM",
        "note": "Diffie-Hellman key exchange; recorded traffic is exposed to "
                "'harvest now, decrypt later' attacks.",
    },
    "AES": {
        "family": "symmetric",
        "quantum_algorithm": GROVER,
        "hard_problem": "Exhaustive key search",
        "impact": "WEAKENED",
        "pqc_replacement": "Keep AES, use 256-bit keys (no new algorithm needed)",
        "note": "Grover's gives a quadratic speed-up: effective security is "
                "about half the key bits (AES-128 -> ~64, AES-256 -> ~128).",
    },
    "SHA": {
        "family": "hash",
        "quantum_algorithm": GROVER,
        "hard_problem": "Preimage search",
        "impact": "WEAKENED",
        "pqc_replacement": "Keep SHA-2/SHA-3 with 256-bit or larger output",
        "note": "Grover's halves preimage resistance (SHA-256 -> ~128 bits). "
                "Collision resistance is largely unaffected in practice.",
    },
}

# Names the scanner might emit -> canonical key in PRIMITIVE_TABLE.
ALIASES = {
    "RSA": "RSA",
    "ECC": "ECC", "ECDSA": "ECC", "ECDH": "ECC", "EDDSA": "ECC",
    "ED25519": "ECC", "X25519": "ECC",
    "DSA": "DSA",
    "DH": "DH", "DIFFIEHELLMAN": "DH",
    "AES": "AES",
    "SHA": "SHA",
}

_SIZE_PATTERN = re.compile(r"(128|192|224|256|384|512)")

# Routing rule: which quantum algorithm attacks which primitive family.
FAMILY_TO_ALGORITHM = {
    "asymmetric": SHOR,    # factoring / discrete log -> full break
    "symmetric": GROVER,   # key search -> quadratic speed-up only
    "hash": GROVER,        # preimage search -> quadratic speed-up only
}


def _validate_table():
    """Fail fast if a table entry disagrees with the routing rule."""
    for name, entry in PRIMITIVE_TABLE.items():
        expected = FAMILY_TO_ALGORITHM[entry["family"]]
        if entry["quantum_algorithm"] != expected:
            raise ValueError(f"{name}: {entry['family']} must route to {expected}")


_validate_table()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _normalise(name):
    """Uppercase and strip everything except letters and digits."""
    return re.sub(r"[^A-Za-z0-9]", "", str(name)).upper()


def canonical_primitive(name):
    """Return the canonical primitive ('RSA', 'ECC', ...) or None if unknown.

    Handles aliases (ECDSA -> ECC), case and punctuation, and families named
    by prefix (AES-256-GCM -> AES, HMAC-SHA256 -> SHA).
    """
    norm = _normalise(name)
    if norm in ALIASES:
        return ALIASES[norm]
    if norm.startswith("AES"):
        return "AES"
    if norm.startswith(("SHA", "HMACSHA")):
        return "SHA"
    return None


def _infer_bits(name, canonical):
    """Pull a size (bits) out of names like 'AES-256' or 'SHA256'.

    SHA-1 is special-cased to its 160-bit output. Returns None if no size is
    present in the name.
    """
    norm = _normalise(name)
    if canonical == "SHA" and norm in ("SHA1", "SHA"):
        return 160 if norm == "SHA1" else None
    match = _SIZE_PATTERN.search(norm)
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def map_primitive(name):
    """Look up the quantum threat profile for one primitive name.

    Returns a copy of the table entry, or None if the primitive is unknown.
    """
    canonical = canonical_primitive(name)
    if canonical is None:
        return None
    entry = deepcopy(PRIMITIVE_TABLE[canonical])
    entry["canonical_primitive"] = canonical
    return entry


def route_algorithm(name):
    """Return the quantum algorithm (SHOR / GROVER) for a primitive name.

    Returns None if the primitive is not recognised.
    """
    entry = map_primitive(name)
    return entry["quantum_algorithm"] if entry else None


def grover_assessment(canonical, bits):
    """Plain-English reading of Grover's impact for AES/SHA findings.

    Returns None for primitives that Grover's does not target.
    """
    if canonical not in ("AES", "SHA"):
        return None
    if not bits:
        return "Size unknown; Grover's impact cannot be quantified."
    half = bits // 2
    if half >= 128:
        text = f"About {half}-bit post-quantum security: comfortable margin."
    else:
        text = (f"About {half}-bit by naive Grover halving: reduced margin, not a "
                "break. A larger size (AES-256, SHA-384 or longer) adds headroom.")
    if canonical == "SHA" and bits == 160:
        text += " SHA-1 is also classically weak (practical collisions exist)."
    return text


def map_finding(finding):
    """Enrich one scanner finding with its quantum-threat information.

    Args:
        finding: dict with a 'primitive' key and, optionally, 'modulus_bits'
            and/or 'key_size' (bits). 'modulus_bits' wins when both exist.

    Returns:
        A new dict (the input is not modified) holding every original field
        plus the quantum-threat fields listed in the module docstring.
        post_quantum_security_bits is 0 for Shor-broken primitives, half the
        size for Grover-weakened ones, and None when the size is unknown.
        size_warning is set when an RSA/DSA/DH size may be a prime size.
    """
    result = dict(finding)
    name = finding.get("primitive", "")
    entry = map_primitive(name)

    if entry is None:
        result.update({
            "canonical_primitive": None,
            "family": None,
            "quantum_algorithm": "UNKNOWN",
            "hard_problem": None,
            "impact": "UNKNOWN",
            "pqc_replacement": "Manual review required",
            "post_quantum_security_bits": None,
            "size_used_bits": finding.get("modulus_bits") or finding.get("key_size"),
            "size_warning": None,
            "grover_assessment": None,
            "mapper_note": f"Unrecognised primitive: {name!r}",
        })
        return result

    canonical = entry["canonical_primitive"]
    # For RSA/DH/DSA the scanner's key_size can be the PRIME size, so the
    # modulus size (modulus_bits) must win when it is present.
    bits = (finding.get("modulus_bits") or finding.get("key_size")
            or _infer_bits(name, canonical))
    size_warning = None
    if (canonical in ("RSA", "DSA", "DH") and not finding.get("modulus_bits")
            and finding.get("key_size")):
        size_warning = ("modulus_bits missing; key_size may be the prime size, "
                        "not the modulus size")

    if entry["family"] == "asymmetric":
        post_quantum_bits = 0  # fully broken once Shor's is practical
    elif bits:
        post_quantum_bits = bits // 2  # Grover's quadratic speed-up
    else:
        post_quantum_bits = None  # size unknown

    result.update({
        "canonical_primitive": canonical,
        "family": entry["family"],
        "quantum_algorithm": entry["quantum_algorithm"],
        "hard_problem": entry["hard_problem"],
        "impact": entry["impact"],
        "pqc_replacement": entry["pqc_replacement"],
        "post_quantum_security_bits": post_quantum_bits,
        "size_used_bits": bits,
        "size_warning": size_warning,
        "grover_assessment": grover_assessment(canonical, bits),
        "mapper_note": entry["note"],
    })
    return result


def map_findings(findings):
    """Map a list of findings (e.g. the contents of findings.json).

    Order and length are preserved; unrecognised primitives are flagged as
    UNKNOWN rather than dropped.
    """
    return [map_finding(f) for f in findings]


def load_findings(path):
    """Load findings from a JSON file.

    Accepts either a bare list or an object of the form {"findings": [...]}.
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data["findings"] if isinstance(data, dict) else data


def map_findings_file(in_path, out_path):
    """Read a findings file, map every finding, write the enriched JSON.

    Returns the mapped list so callers can chain into report generation.
    """
    mapped = map_findings(load_findings(in_path))
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(mapped, fh, indent=2)
    return mapped


def summarise(mapped):
    """Print per-project / per-primitive counts, then totals, warnings, unknowns."""
    counts = {}
    for item in mapped:
        key = (item.get("project"), item.get("canonical_primitive"))
        counts[key] = counts.get(key, 0) + 1
    for (project, prim), n in sorted(counts.items(), key=str):
        print(f"{project}: {prim} x{n}")
    warned = [m for m in mapped if m.get("size_warning")]
    unknown = [m for m in mapped if m.get("canonical_primitive") is None]
    print(f"Total: {len(mapped)} | size warnings: {len(warned)} | unknown: {len(unknown)}")


def _cell(value):
    """Format a value for a Markdown table cell ('-' for empty, '|' escaped)."""
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def generate_mapping_report(mapped, out_path, draft=False):
    """Write mapping_report.md: per-project summary, detail table, caveats.

    With draft=True a banner marks the report as built from sample data.
    """
    projects = {}
    for item in mapped:
        projects.setdefault(item.get("project") or "(unknown project)", []).append(item)

    lines = [
        "# Quantum-Algorithm Mapping Report",
        "",
        "Each finding from the Stage 1 scanner is mapped to the quantum "
        "algorithm that threatens it. This is a theoretical mapping; it says "
        "which attack applies, not that the attack is practical today.",
        "",
        f"**Total findings:** {len(mapped)}  ",
        f"**Projects:** {len(projects)}",
        "",
    ]

    if draft:
        lines[2:2] = ["> **DRAFT: generated from SAMPLE (dummy) findings, "
                      "not from real scanner output.**", ""]

    for project, items in sorted(projects.items()):
        lines += [f"## {project}", "", "### Summary", "",
                  "| Primitive | Findings | Quantum algorithm | Impact | PQC replacement |",
                  "|---|---|---|---|---|"]
        groups = {}
        for it in items:
            key = (it.get("canonical_primitive"), it["quantum_algorithm"],
                   it["impact"], it["pqc_replacement"])
            groups[key] = groups.get(key, 0) + 1
        for (prim, algo, impact, pqc), n in sorted(groups.items(), key=str):
            lines.append(f"| {_cell(prim)} | {n} | {_cell(algo)} | {_cell(impact)} | {_cell(pqc)} |")

        lines += ["", "### Findings", "",
                  "| File:Line | Primitive | Size (bits) | Size basis | PQ-security (bits) | Warning |",
                  "|---|---|---|---|---|---|"]
        for it in items:
            loc = f"{it.get('file', '?')}:{it.get('line', '?')}"
            lines.append(
                f"| {_cell(loc)} | {_cell(it.get('primitive'))} | "
                f"{_cell(it.get('size_used_bits'))} | {_cell(it.get('size_basis'))} | "
                f"{_cell(it.get('post_quantum_security_bits'))} | {_cell(it.get('size_warning'))} |")
        lines.append("")

    warned = sum(1 for m in mapped if m.get("size_warning"))
    unknown = sum(1 for m in mapped if m.get("canonical_primitive") is None)
    lines += [
        "## Notes and limitations", "",
        "- Asymmetric primitives (RSA, ECC, DSA, DH) are broken by Shor's "
        "algorithm once a large enough fault-tolerant quantum computer exists. "
        "PQ-security is shown as 0 for these.",
        "- Symmetric and hash primitives are only weakened by Grover's "
        "algorithm (a quadratic speed-up, not a full break); PQ-security is "
        "about half the classical bits.",
        "- Padding weaknesses (e.g. textbook RSA) and classical key-strength "
        "problems are separate from the quantum threat and are reported "
        "separately.",
        f"- Size warnings: {warned}. Unrecognised primitives: {unknown}.",
        "",
    ]
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------
def _demo():
    """Print the mapping for a handful of dummy findings."""
    dummy_findings = [
        {"primitive": "RSA", "key_size": 1024},
        {"primitive": "ECDSA", "key_size": 256},
        {"primitive": "DSA", "key_size": 2048},
        {"primitive": "Diffie-Hellman", "key_size": 2048},
        {"primitive": "AES-128"},
        {"primitive": "SHA-256"},
        {"primitive": "Blowfish"},
    ]
    for item in map_findings(dummy_findings):
        print(f"{item['primitive']:<16} -> {item['quantum_algorithm']:<18} "
              f"{item['impact']:<9} PQ-security bits: {item['post_quantum_security_bits']}")


def main(argv=None):
    """CLI entry point.

    python quantum_mapper.py                              demo with dummy data
    python quantum_mapper.py IN.json OUT.json             map a findings file
    python quantum_mapper.py IN.json OUT.json REPORT.md [--draft]
    """
    args = list(sys.argv[1:] if argv is None else argv)
    draft = "--draft" in args
    paths = [a for a in args if a != "--draft"]
    if not paths:
        _demo()
        return 0
    if len(paths) not in (2, 3):
        print("usage: quantum_mapper.py IN.json OUT.json [REPORT.md] [--draft]")
        return 2
    mapped = map_findings_file(paths[0], paths[1])
    summarise(mapped)
    if len(paths) == 3:
        generate_mapping_report(mapped, paths[2], draft=draft)
        print(f"Report written to {paths[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
