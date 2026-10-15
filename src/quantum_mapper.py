"""quantum_mapper.py - Stage 2 of the PQC Migration Advisor pipeline.

Pipeline position:
    scanner (findings.json) -> quantum_mapper -> qubit_estimator -> CBOM / risk report

Takes the classical-crypto findings from the Stage 1 scanner and attaches, to
each one, the quantum algorithm that threatens it, the post-quantum security
level, and a recommended PQC replacement.

    Asymmetric (RSA, ECC, DSA, DH)  -> Shor's algorithm   -> broken
    Symmetric / hash (AES, SHA)     -> Grover's algorithm -> security roughly halved

Input
    A list of dicts (or {"findings": [...]}) with at least project, file,
    line and primitive. Optional: "modulus_bits" and "key_size". For
    RSA/DSA/DH, modulus_bits is preferred, because the scanner's key_size can
    be the PRIME size rather than the modulus size.

Manual overrides
    Some facts cannot be read from source code (for example the key size a
    function is actually called with). data/manual_facts.json lists them as
    "size_overrides". An override is applied only if "confirmed" is true, so
    facts the team has not agreed on never change results silently. Applied
    overrides are recorded in each finding's "override_ids".

Output
    The same dicts plus: canonical_primitive, family, quantum_algorithm,
    hard_problem, impact, pqc_replacement, post_quantum_security_bits,
    size_used_bits, size_warning, grover_assessment, classically_weak,
    mapper_note. Legacy ciphers (3DES, DES, RC4, Blowfish) are recognised: they
    route to Grover's and are marked classically_weak.

Command line
    python src/quantum_mapper.py                          demo with dummy data
    python src/quantum_mapper.py IN.json OUT.json [REPORT.md]
        --overrides FILE   apply confirmed manual overrides
        --draft            label the report as built from sample data
        --strict           exit 1 if the findings fail validation

Limits
    This is a theory-level mapping: it says which quantum attack applies, not
    that the attack is practical today. Padding weaknesses (e.g. textbook RSA)
    and classical key-strength problems are separate findings, reported
    elsewhere. Standard library only. See docs/quantum_mapper.md.
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
    "REQUIRED_FIELDS", "validate_findings", "load_overrides", "apply_overrides",
    "prepare_findings", "write_json", "collect_caveats",
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
    # Legacy ciphers: Grover's applies, but they are already weak classically,
    # so the right advice is "replace", not "wait for quantum".
    "3DES": {
        "family": "symmetric",
        "quantum_algorithm": GROVER,
        "hard_problem": "Exhaustive key search",
        "impact": "WEAKENED",
        "pqc_replacement": "Replace with AES-256 (3DES is deprecated)",
        "note": "About 112-bit effective strength and a 64-bit block size "
                "(Sweet32 birthday attacks); deprecated by NIST. Replace it "
                "with AES-256.",
        "effective_bits": 112,
        "classically_weak": True,
    },
    "DES": {
        "family": "symmetric",
        "quantum_algorithm": GROVER,
        "hard_problem": "Exhaustive key search",
        "impact": "WEAKENED",
        "pqc_replacement": "Replace with AES-256",
        "note": "A 56-bit key can be brute-forced on ordinary hardware; DES "
                "is classically broken.",
        "effective_bits": 56,
        "classically_weak": True,
    },
    "RC4": {
        "family": "symmetric",
        "quantum_algorithm": GROVER,
        "hard_problem": "Exhaustive key search",
        "impact": "WEAKENED",
        "pqc_replacement": "Replace with AES-256-GCM",
        "note": "Stream cipher with known keystream biases; prohibited in "
                "TLS (RFC 7465). Classically weak.",
        "classically_weak": True,
    },
    "BLOWFISH": {
        "family": "symmetric",
        "quantum_algorithm": GROVER,
        "hard_problem": "Exhaustive key search",
        "impact": "WEAKENED",
        "pqc_replacement": "Replace with AES-256",
        "note": "A 64-bit block size makes long sessions vulnerable to "
                "birthday-bound (Sweet32) attacks. Treat as a legacy cipher.",
        "classically_weak": True,
    },
}

LEGACY_CIPHERS = ("3DES", "DES", "RC4", "BLOWFISH")

# Names the scanner might emit -> canonical key in PRIMITIVE_TABLE.
ALIASES = {
    "RSA": "RSA",
    "ECC": "ECC", "ECDSA": "ECC", "ECDH": "ECC", "EDDSA": "ECC",
    "ED25519": "ECC", "X25519": "ECC",
    "DSA": "DSA",
    "DH": "DH", "DIFFIEHELLMAN": "DH",
    "AES": "AES",
    "SHA": "SHA",
    "3DES": "3DES", "TRIPLEDES": "3DES", "TDES": "3DES", "DES3": "3DES",
    "DESEDE": "3DES",
    "DES": "DES",
    "RC4": "RC4", "ARCFOUR": "RC4",
    "BLOWFISH": "BLOWFISH",
}

_SIZE_PATTERN = re.compile(r"(128|192|224|256|384|448|512|521)")
_MODULUS_PATTERN = re.compile(r"(1024|2048|3072|4096|7680|8192|15360)")
_SHA_PATTERN = re.compile(r"^(SHA(\d|KE|$)|HMACSHA)")

# Named curves -> curve size in bits (used for size inference and as ECC names).
_CURVE_BITS = {
    "P224": 224, "P256": 256, "P384": 384, "P521": 521,
    "ED25519": 256, "X25519": 256, "CURVE25519": 256,
    "ED448": 448, "X448": 448, "CURVE448": 448,
}
_CURVE_PREFIXES = ("SECP", "PRIME", "BRAINPOOL", "ECDSA", "ECDH", "ECIES", "EDDSA")

# Legacy-cipher name prefixes (checked after the exact aliases above).
_LEGACY_PREFIXES = (
    ("3DES", "3DES"), ("TRIPLEDES", "3DES"), ("TDES", "3DES"), ("DES3", "3DES"),
    ("DESEDE", "3DES"),
    ("DESCBC", "DES"), ("DESECB", "DES"), ("DESCFB", "DES"), ("DESOFB", "DES"),
    ("DESCTR", "DES"),
    ("RC4", "RC4"), ("ARCFOUR", "RC4"), ("BLOWFISH", "BLOWFISH"),
)

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

    Handles aliases (ECDSA -> ECC), case and punctuation, key sizes in the
    name (RSA-2048), named curves (P-256, secp256r1, ED448), and families
    named by prefix (AES-256-GCM -> AES, HMAC-SHA256 -> SHA, FFDHE2048 -> DH,
    3DES-CBC -> 3DES).
    """
    norm = _normalise(name)
    if norm in ALIASES:
        return ALIASES[norm]
    if norm.startswith("AES"):
        return "AES"
    if _SHA_PATTERN.match(norm):
        return "SHA"
    if norm in _CURVE_BITS or norm.startswith(_CURVE_PREFIXES):
        return "ECC"
    if norm.startswith("RSA"):
        return "RSA"
    if norm.startswith(("FFDHE", "DHE")) or re.fullmatch(r"DH\d+", norm):
        return "DH"
    if norm.startswith("DSA"):
        return "DSA"
    for prefix, canonical in _LEGACY_PREFIXES:
        if norm.startswith(prefix):
            return canonical
    return None


def _infer_bits(name, canonical):
    """Pull a size (bits) out of a primitive name.

    Examples: 'AES-256' -> 256, 'SHA256' -> 256, 'RSA-2048' -> 2048,
    'P-256' -> 256, 'ED448' -> 448. SHA-1 is special-cased to its 160-bit
    output. Returns None if the name carries no size.
    """
    norm = _normalise(name)
    if canonical == "SHA" and norm in ("SHA1", "SHA"):
        return 160 if norm == "SHA1" else None
    if canonical == "ECC" and norm in _CURVE_BITS:
        return _CURVE_BITS[norm]
    if canonical in ("RSA", "DSA", "DH"):
        match = _MODULUS_PATTERN.search(norm)
        return int(match.group(1)) if match else None
    if canonical in ("3DES", "DES", "RC4"):
        return None
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
    """Plain-English reading of Grover's impact for AES, SHA and legacy ciphers.

    Returns None for primitives that Grover's does not target.

    AES-128 wording follows NIST: post-quantum security category 1 is defined
    relative to AES-128 key search, and NIST's call for proposals (2016,
    section 4.A.5) puts the quantum cost of that search at about 2^170 gates
    divided by a depth limit (MAXDEPTH), far above the naive 2^64.
    """
    if canonical in LEGACY_CIPHERS:
        return ("Grover's applies, but this cipher is already weak classically; "
                "replace it. The quantum speed-up is not the main problem.")
    if canonical not in ("AES", "SHA"):
        return None
    if not bits:
        return "Size unknown; Grover's impact cannot be quantified."
    half = bits // 2
    if half >= 128:
        text = f"About {half}-bit post-quantum security: comfortable margin."
    elif canonical == "AES" and bits == 128:
        text = ("About 64-bit by naive Grover halving, but this is not a break. "
                "NIST defines post-quantum security category 1 relative to AES-128 "
                "key search, and estimates the real quantum cost at about "
                "2^170/MAXDEPTH gates because Grover's parallelises poorly. "
                "AES-256 adds margin for long-lived data.")
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
            "classically_weak": None,
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
    else:
        # Grover's quadratic speed-up. Some legacy ciphers have a fixed
        # effective strength (e.g. 3DES = 112 bits) that overrides the key size.
        basis = entry.get("effective_bits") or bits
        post_quantum_bits = basis // 2 if basis else None  # None = size unknown

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
        "classically_weak": entry.get("classically_weak", False),
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


REQUIRED_FIELDS = ("project", "file", "line", "primitive")


def validate_findings(findings):
    """Check a findings list for structural problems.

    Returns a list of human-readable problem strings (empty list = clean).
    Checks: list shape, required fields present, and duplicate findings.
    """
    if not isinstance(findings, list):
        return ["findings is not a list"]
    problems, seen = [], set()
    for i, item in enumerate(findings):
        if not isinstance(item, dict):
            problems.append(f"#{i}: not an object")
            continue
        missing = [k for k in REQUIRED_FIELDS if item.get(k) in (None, "")]
        if missing:
            problems.append(f"#{i} ({item.get('file', '?')}): missing {', '.join(missing)}")
        key = (item.get("project"), item.get("file"), item.get("line"), item.get("primitive"))
        if key in seen:
            problems.append(f"#{i}: duplicate finding {key}")
        seen.add(key)
    return problems


def load_overrides(path):
    """Load manual size overrides from a JSON file.

    Accepts a bare list or an object with a "size_overrides" list (the
    layout of data/manual_facts.json).
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data.get("size_overrides", []) if isinstance(data, dict) else data


def _override_matches(finding, match):
    """True if a finding satisfies every condition in an override's 'match'.

    Conditions: project, file_contains, line, lines (a list of line numbers),
    primitive, and has_size (true = only findings that already carry a size
    from the scanner, so lines without any size are left alone).
    """
    if "project" in match and finding.get("project") != match["project"]:
        return False
    if "file_contains" in match and match["file_contains"] not in str(finding.get("file", "")):
        return False
    if "line" in match and finding.get("line") != match["line"]:
        return False
    if "lines" in match and finding.get("line") not in match["lines"]:
        return False
    if match.get("has_size") and not (finding.get("modulus_bits") or finding.get("key_size")):
        return False
    if "primitive" in match:
        wanted = canonical_primitive(match["primitive"])
        if wanted is None or canonical_primitive(finding.get("primitive", "")) != wanted:
            return False
    return True


def apply_overrides(findings, overrides):
    """Apply CONFIRMED manual overrides to findings (e.g. real modulus sizes).

    An override is applied only when it has "confirmed": true, so facts the
    team has not yet agreed on can sit in the file without changing results.

    Returns (new_findings, report). The input list is not modified. The
    report has one dict per override: id, confirmed, matched, source.
    """
    result = [dict(f) for f in findings]
    report = []
    for ov in overrides:
        confirmed = bool(ov.get("confirmed"))
        match = ov.get("match", {})
        matched = 0
        for item in result:
            if _override_matches(item, match):
                matched += 1
                if confirmed:
                    item.update(ov.get("set", {}))
                    item["override_ids"] = list(item.get("override_ids", [])) + [ov.get("id", "?")]
        report.append({"id": ov.get("id", "?"), "confirmed": confirmed,
                       "matched": matched, "source": ov.get("source")})
    return result, report


def prepare_findings(in_path, overrides_path=None):
    """Load findings, validate them, and apply confirmed overrides.

    Returns (findings, problems, override_report).
    """
    findings = load_findings(in_path)
    problems = validate_findings(findings)
    report = []
    if overrides_path:
        findings, report = apply_overrides(findings, load_overrides(overrides_path))
    return findings, problems, report


def write_json(path, data):
    """Write data as indented UTF-8 JSON with a trailing newline."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def map_findings_file(in_path, out_path, overrides_path=None):
    """Read a findings file, map every finding, write the enriched JSON.

    Confirmed overrides (if a path is given) are applied before mapping.
    Returns the mapped list so callers can chain into report generation.
    """
    findings, _problems, _report = prepare_findings(in_path, overrides_path)
    mapped = map_findings(findings)
    write_json(out_path, mapped)
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


def _flag_text(value):
    """Text of an edge-case padding flag (string or structure); None if absent."""
    if value in (None, "", [], {}):
        return None
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def collect_caveats(mapped, override_report=None):
    """List the data-quality caveats a reader of the report must know about.

    Covers: size warnings (a size that may be a prime size), findings with no
    size at all for sized primitives, unrecognised primitives, and manual
    overrides that are unconfirmed or matched nothing.
    """
    caveats = []
    for item in mapped:
        where = f"{item.get('project')} {item.get('file')}:{item.get('line')}"
        if item.get("size_warning"):
            caveats.append(f"{where}: {item['size_warning']} (size used: {item.get('size_used_bits')}).")
        elif item.get("size_used_bits") is None and item.get("canonical_primitive") in ("RSA", "DSA", "DH", "ECC", "AES"):
            caveats.append(f"{where}: {item['primitive']} has no size information.")
        if item.get("canonical_primitive") is None:
            caveats.append(f"{where}: unrecognised primitive {item.get('primitive')!r}; needs manual review.")
    for ov in override_report or []:
        if not ov["confirmed"]:
            caveats.append(f"Override '{ov['id']}' is unconfirmed and was NOT applied "
                           f"(would change {ov['matched']} finding(s)); source: {ov.get('source') or 'n/a'}.")
        elif ov["matched"] == 0:
            caveats.append(f"Override '{ov['id']}' is confirmed but matched no findings; check its 'match' rule.")
    return caveats


def generate_mapping_report(mapped, out_path, draft=False, caveats=None):
    """Write mapping_report.md: per-project summary, detail table, caveats.

    With draft=True a banner marks the report as built from sample data.
    `caveats` (see collect_caveats) is rendered as a "Data caveats" section.
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
                  "| File:Line | Primitive | Size (bits) | Size basis | PQ-security (bits) | Warning | Padding flag |",
                  "|---|---|---|---|---|---|---|"]
        for it in items:
            loc = f"{it.get('file', '?')}:{it.get('line', '?')}"
            lines.append(
                f"| {_cell(loc)} | {_cell(it.get('primitive'))} | "
                f"{_cell(it.get('size_used_bits'))} | {_cell(it.get('size_basis'))} | "
                f"{_cell(it.get('post_quantum_security_bits'))} | {_cell(it.get('size_warning'))} | "
                f"{_cell(_flag_text(it.get('edge_flag')))} |")
        lines.append("")

    if caveats:
        lines += ["## Data caveats", "",
                  "Resolve these before treating the sizes above as final.", ""]
        lines += [f"- {c}" for c in caveats]
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
        "separately. The 'Padding flag' column comes from the edge-case module "
        "(edge_flag in findings.json) and is not part of the quantum result.",
        "- Legacy ciphers (3DES, DES, RC4, Blowfish) are weakened by Grover's "
        "but already weak classically: replace them.",
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
        {"primitive": "3DES"},
        {"primitive": "ROT13"},
    ]
    for item in map_findings(dummy_findings):
        print(f"{item['primitive']:<16} -> {item['quantum_algorithm']:<18} "
              f"{item['impact']:<9} PQ-security bits: {item['post_quantum_security_bits']}")


def main(argv=None):
    """CLI entry point.

    python quantum_mapper.py                              demo with dummy data
    python quantum_mapper.py IN.json OUT.json [REPORT.md] [options]

    Options:
        --overrides FILE   apply confirmed manual size overrides (manual_facts.json)
        --draft            mark the report as built from sample data
        --strict           exit with status 1 if the findings fail validation
    """
    args = list(sys.argv[1:] if argv is None else argv)
    draft = strict = False
    overrides_path = None
    paths = []
    it = iter(args)
    for arg in it:
        if arg == "--draft":
            draft = True
        elif arg == "--strict":
            strict = True
        elif arg == "--overrides":
            overrides_path = next(it, None)
            if not overrides_path:
                print("--overrides needs a file path")
                return 2
        else:
            paths.append(arg)
    if not paths:
        _demo()
        return 0
    if len(paths) not in (2, 3):
        print("usage: quantum_mapper.py IN.json OUT.json [REPORT.md] "
              "[--overrides FILE] [--draft] [--strict]")
        return 2

    findings, problems, ov_report = prepare_findings(paths[0], overrides_path)
    for problem in problems:
        print(f"VALIDATION: {problem}")
    for ov in ov_report:
        state = "applied" if ov["confirmed"] else "NOT applied (unconfirmed)"
        print(f"OVERRIDE {ov['id']}: matched {ov['matched']} finding(s), {state}")
    mapped = map_findings(findings)
    write_json(paths[1], mapped)
    summarise(mapped)
    if len(paths) == 3:
        generate_mapping_report(mapped, paths[2], draft=draft,
                                caveats=collect_caveats(mapped, ov_report))
        print(f"Report written to {paths[2]}")
    return 1 if (strict and problems) else 0


if __name__ == "__main__":

    sys.exit(main())
    sys.exit(main())
