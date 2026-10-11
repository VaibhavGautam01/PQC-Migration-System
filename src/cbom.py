"""cbom.py - Cryptographic Bill of Materials (CBOM) for the PQC Migration Advisor.

Pipeline position:
    findings.json -> quantum_mapper -> cbom -> CBOM (JSON + Markdown)

A CBOM entry describes one cryptographic component: which primitive, what key
size, and three SEPARATE risk blocks plus a recommendation.

    quantum_risk     which quantum algorithm applies, logical-qubit estimate
    classical_risk   strength against ordinary computers (no quantum needed)
    padding_risk     padding / construction weaknesses such as textbook RSA
    recommended_pqc  what to migrate to

The blocks are kept apart on purpose: textbook RSA is dangerous because it is
deterministic, not because of Shor's algorithm.

Standard library only (plus quantum_mapper from this repo).
"""

import json
import sys

import quantum_mapper as qm

CBOM_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
ENTRY_FIELDS = ("id", "project", "primitive", "key_size_bits", "size_basis",
                "size_status", "files", "quantum_risk", "classical_risk",
                "padding_risk", "recommended_pqc", "notes")

BLOCK_FIELDS = {
    "quantum_risk": ("algorithm", "impact", "logical_qubits_estimate",
                     "estimate_basis", "post_quantum_security_bits"),
    "classical_risk": ("status", "basis", "evidence"),
    "padding_risk": ("status", "weakness", "source"),
    "recommended_pqc": ("algorithm", "standard", "rationale"),
}

CBOM_FIELDS = ("cbom_version", "project_count", "entry_count", "finding_count",
               "entries", "unmapped", "references", "notes")

SIZE_STATUSES = ("override-confirmed", "scanner-reported", "unverified", "unknown")
CLASSICAL_STATUSES = ("practically-breakable", "below-minimum", "meets-minimum",
                      "weak-collision-resistance", "unknown")

# Padding words must never appear inside the quantum block.
_PADDING_KEYS = ("padding", "padding_status", "weakness")

REFERENCES = [
    "Shor, P. W. (1997). Polynomial-time algorithms for prime factorization and "
    "discrete logarithms on a quantum computer. SIAM J. Comput. 26(5), 1484-1509.",
    "Grover, L. K. (1996). A fast quantum mechanical algorithm for database "
    "search. Proc. 28th ACM STOC, 212-219.",
    "Beauregard, S. (2003). Circuit for Shor's algorithm using 2n+3 qubits. "
    "Quantum Information & Computation 3(2), 175-185. arXiv:quant-ph/0205095.",
    "Gidney, C. and Ekera, M. (2021). How to factor 2048 bit RSA integers in 8 "
    "hours using 20 million noisy qubits. Quantum 5, 433. arXiv:1905.09749.",
    "NIST FIPS 203 (2024). Module-Lattice-Based Key-Encapsulation Mechanism "
    "Standard (ML-KEM).",
    "NIST FIPS 204 (2024). Module-Lattice-Based Digital Signature Standard "
    "(ML-DSA).",
]

NOTES = [
    "Quantum risk, classical risk and padding risk are reported separately. "
    "Padding weaknesses such as textbook RSA are classical problems, not "
    "consequences of Shor's algorithm.",
    "Logical-qubit estimates use the 2n+3 circuit for factoring an n-bit "
    "modulus. They exclude error-correction overhead, so physical qubit counts "
    "are much larger.",
    "All quantum demonstrations in this project run on a simulator at toy "
    "sizes. Resource figures for RSA-1024/2048 are published estimates, not "
    "measurements.",
    "Grover's algorithm is a quadratic speed-up, not a full break: symmetric "
    "and hash primitives keep about half their classical security bits.",
]


def shor_logical_qubits(n_bits):
    """Logical qubits to factor an n-bit modulus with the 2n+3 circuit.

    This is the project's estimate formula (Beauregard 2003). It counts logical
    qubits only and excludes error-correction overhead.
    """
    if not isinstance(n_bits, int) or isinstance(n_bits, bool) or n_bits <= 0:
        raise ValueError("n_bits must be a positive integer")
    return 2 * n_bits + 3


def validate_entry(entry):
    """Check one CBOM entry against the schema.

    Returns a list of problem strings (empty list = valid).
    """
    if not isinstance(entry, dict):
        return ["entry is not an object"]
    problems = [f"missing field '{f}'" for f in ENTRY_FIELDS if f not in entry]
    if problems:
        return problems
    if not entry["id"] or not isinstance(entry["id"], str):
        problems.append("id must be a non-empty string")
    if entry["primitive"] not in qm.PRIMITIVE_TABLE:
        problems.append(f"unknown primitive {entry['primitive']!r}")
    size = entry["key_size_bits"]
    if size is not None and (not isinstance(size, int) or isinstance(size, bool) or size <= 0):
        problems.append("key_size_bits must be a positive integer or null")
    if entry["size_status"] not in SIZE_STATUSES:
        problems.append(f"bad size_status {entry['size_status']!r}")
    if not isinstance(entry["files"], list) or not entry["files"]:
        problems.append("files must be a non-empty list")
    if not isinstance(entry["notes"], list):
        problems.append("notes must be a list")
    for block, fields in BLOCK_FIELDS.items():
        data = entry[block]
        if not isinstance(data, dict):
            problems.append(f"{block} must be an object")
            continue
        problems += [f"{block}: missing '{f}'" for f in fields if f not in data]
    if problems:
        return problems
    if entry["classical_risk"]["status"] not in CLASSICAL_STATUSES:
        problems.append(f"bad classical_risk status {entry['classical_risk']['status']!r}")
    if not isinstance(entry["classical_risk"]["evidence"], list):
        problems.append("classical_risk.evidence must be a list")
    qubits = entry["quantum_risk"]["logical_qubits_estimate"]
    if qubits is not None and (not isinstance(qubits, int) or qubits <= 0):
        problems.append("logical_qubits_estimate must be a positive integer or null")
    leaked = [k for k in _PADDING_KEYS if k in entry["quantum_risk"]]
    if leaked:
        problems.append(f"quantum_risk must not contain padding keys: {leaked}")
    return problems


def validate_cbom(cbom):
    """Check a whole CBOM: top-level fields, counts, unique ids, every entry."""
    if not isinstance(cbom, dict):
        return ["CBOM is not an object"]
    problems = [f"missing top-level field '{f}'" for f in CBOM_FIELDS if f not in cbom]
    if problems:
        return problems
    entries = cbom["entries"]
    if cbom["entry_count"] != len(entries):
        problems.append(f"entry_count {cbom['entry_count']} != {len(entries)} entries")
    ids = [e.get("id") if isinstance(e, dict) else None for e in entries]
    if len(set(ids)) != len(ids):
        problems.append("entry ids are not unique")
    for i, entry in enumerate(entries):
        label = ids[i] or f"entry #{i}"
        problems += [f"{label}: {p}" for p in validate_entry(entry)]
    return problems

# ---------------------------------------------------------------------------
# Building the CBOM from mapped findings
# ---------------------------------------------------------------------------
PQC_RECOMMENDATIONS = {
    "RSA": {
        "algorithm": "ML-KEM-768",
        "standard": "NIST FIPS 203",
        "rationale": "ML-KEM is a key-encapsulation mechanism: use it to establish "
                     "a shared secret, then encrypt the data with AES-256-GCM "
                     "(do not use bare RSA-style encryption). Parameter set 768 "
                     "targets NIST security category 3. If this RSA is used for "
                     "signatures instead, use ML-DSA-65 (FIPS 204).",
    },
    "ECC": {
        "algorithm": "ML-KEM-768 (key exchange) / ML-DSA-65 (signatures)",
        "standard": "NIST FIPS 203 / FIPS 204",
        "rationale": "ECDH-style key agreement maps to ML-KEM; ECDSA/EdDSA-style "
                     "signatures map to ML-DSA. Shor's algorithm breaks the "
                     "elliptic-curve discrete log.",
    },
    "DSA": {
        "algorithm": "ML-DSA-65",
        "standard": "NIST FIPS 204",
        "rationale": "DSA signatures rely on the discrete log problem, which "
                     "Shor's algorithm solves.",
    },
    "DH": {
        "algorithm": "ML-KEM-768",
        "standard": "NIST FIPS 203",
        "rationale": "Diffie-Hellman key exchange relies on the discrete log "
                     "problem; ML-KEM replaces it. Recorded traffic is exposed to "
                     "harvest-now-decrypt-later attacks.",
    },
    "AES": {
        "algorithm": "AES-256 (no PQC replacement needed)",
        "standard": "NIST FIPS 197",
        "rationale": "Grover's algorithm only halves the effective key size, so "
                     "AES-256 keeps about 128-bit security.",
    },
    "SHA": {
        "algorithm": "SHA-256 or larger (SHA-2 / SHA-3)",
        "standard": "NIST FIPS 180-4 / FIPS 202",
        "rationale": "Grover's algorithm halves preimage resistance; a 256-bit "
                     "or larger output keeps about 128-bit security.",
    },
}

# Field names under which the edge-case module might store a padding flag.
PADDING_FLAG_KEYS = ("padding", "padding_status", "padding_flag", "edge_flags",
                     "edge_case_flags", "flags")


def load_facts(path):
    """Load data/manual_facts.json (per-project padding facts, attack evidence)."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def classical_assessment(canonical, bits, primitive_name=""):
    """Classical (non-quantum) strength of a primitive at its size.

    Returns {"status": one of CLASSICAL_STATUSES, "basis": explanation}.
    """
    def result(status, basis):
        return {"status": status, "basis": basis}

    if canonical in ("RSA", "DSA", "DH"):
        if not bits:
            return result("unknown", "Size unknown, so classical strength cannot be assessed.")
        if bits <= 512:
            return result("practically-breakable",
                          f"A {bits}-bit modulus can be attacked with ordinary hardware "
                          "or rented cloud time. No quantum computer is needed.")
        if bits < 2048:
            return result("below-minimum",
                          f"A {bits}-bit modulus is below the 2048-bit minimum (this "
                          "project flags RSA under 2048 bits; NIST guidance agrees). "
                          "This is a classical finding, separate from the quantum threat.")
        return result("meets-minimum",
                      f"A {bits}-bit modulus meets the 2048-bit minimum against classical attacks.")
    if canonical == "ECC":
        if not bits:
            return result("unknown", "Curve size unknown.")
        if bits < 224:
            return result("below-minimum", f"A {bits}-bit curve gives under 112-bit classical security.")
        return result("meets-minimum", f"A {bits}-bit curve meets the 224-bit minimum.")
    if canonical == "AES":
        if not bits:
            return result("unknown", "Key size unknown.")
        if bits < 128:
            return result("below-minimum", f"A {bits}-bit AES key is below 128 bits.")
        return result("meets-minimum", f"A {bits}-bit AES key meets the 128-bit minimum.")
    if canonical == "SHA":
        if bits == 160 or qm._normalise(primitive_name) == "SHA1":
            return result("weak-collision-resistance",
                          "SHA-1 has practical collision attacks; use SHA-256 or larger.")
        if not bits:
            return result("unknown", "Output size unknown.")
        if bits < 224:
            return result("below-minimum", f"A {bits}-bit hash output is below 224 bits.")
        return result("meets-minimum", f"A {bits}-bit hash output is adequate classically.")
    return result("unknown", "Primitive not assessed.")


def padding_assessment(canonical, group, project_facts):
    """Padding / construction risk. Only meaningful for RSA.

    Priority: manually confirmed project facts, then the edge-case flags that
    were merged into findings.json, then 'unknown'.
    Returns {"status", "weakness", "source"}.
    """
    if canonical != "RSA":
        return {"status": "not-applicable", "weakness": None,
                "source": "Padding schemes apply to RSA encryption and signatures."}
    manual = (project_facts or {}).get("padding")
    if manual:
        return {"status": manual.get("status", "unknown"),
                "weakness": manual.get("weakness"),
                "source": manual.get("source", "manual facts")}
    for item in group:
        for key in PADDING_FLAG_KEYS:
            value = item.get(key)
            if value:
                text = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
                return {"status": "flagged", "weakness": text,
                        "source": f"edge-case flag '{key}' in findings.json"}
    return {"status": "unknown", "weakness": None,
            "source": "No padding information in findings or manual facts."}


def _size_status(group):
    """How trustworthy the size of a group of findings is."""
    if any(item.get("override_ids") for item in group):
        return "override-confirmed"
    if any(item.get("size_warning") for item in group):
        return "unverified"
    if group[0].get("size_used_bits") is None:
        return "unknown"
    return "scanner-reported"


def _group_findings(mapped):
    """Group mapped findings by (project, primitive, size). Returns (groups, unmapped)."""
    groups, unmapped = {}, []
    for item in mapped:
        canonical = item.get("canonical_primitive")
        if canonical is None:
            unmapped.append({"project": item.get("project"), "file": item.get("file"),
                             "line": item.get("line"), "primitive": item.get("primitive")})
            continue
        key = (item.get("project"), canonical, item.get("size_used_bits"))
        groups.setdefault(key, []).append(item)
    return groups, unmapped


def _file_refs(group):
    """Sorted, de-duplicated 'file:line' references for a group."""
    pairs = {(str(g.get("file")), g.get("line") if isinstance(g.get("line"), int) else 0)
             for g in group}
    return [f"{file}:{line}" for file, line in sorted(pairs)]


def _build_entry(entry_id, key, group, project_facts):
    """Build one CBOM entry from a group of findings."""
    project, canonical, bits = key
    first = group[0]
    bases = sorted({str(g["size_basis"]) for g in group if g.get("size_basis")})
    status = _size_status(group)
    qubits = shor_logical_qubits(bits) if canonical == "RSA" and bits else None
    if qubits:
        estimate_basis = (f"Logical qubits to factor a {bits}-bit modulus with the 2n+3 circuit "
                          "(Beauregard 2003). Logical qubits only: error-correction overhead is "
                          "excluded, so physical qubit counts are far higher.")
    else:
        estimate_basis = "No qubit estimate is computed for this primitive."
    classical = classical_assessment(canonical, bits, first.get("primitive", ""))
    if status == "unverified" and bits:
        caution = "UNVERIFIED SIZE (the scanner value may be a prime size, not the modulus size). "
        estimate_basis = caution + estimate_basis
        classical["basis"] = caution + classical["basis"]
    classical["evidence"] = list((project_facts or {}).get("attack_evidence", [])) if canonical == "RSA" else []
    notes = []
    if status in ("unverified", "unknown"):
        notes.append("Key size is not verified; the qubit estimate and classical "
                     "assessment depend on it.")
    return {
        "id": entry_id,
        "project": project,
        "primitive": canonical,
        "key_size_bits": bits,
        "size_basis": "; ".join(bases) if bases else "scanner field or primitive name",
        "size_status": status,
        "files": _file_refs(group),
        "quantum_risk": {
            "algorithm": first["quantum_algorithm"],
            "impact": first["impact"],
            "logical_qubits_estimate": qubits,
            "estimate_basis": estimate_basis,
            "post_quantum_security_bits": first["post_quantum_security_bits"],
        },
        "classical_risk": classical,
        "padding_risk": padding_assessment(canonical, group, project_facts),
        "recommended_pqc": dict(PQC_RECOMMENDATIONS[canonical]),
        "notes": notes,
    }


def build_cbom(mapped, facts=None):
    """Build the CBOM dict from mapped findings (quantum_mapper output).

    One entry per (project, primitive, size). Output is deterministic: no
    timestamps, stable ordering and ids.
    """
    project_facts = (facts or {}).get("projects", {})
    groups, unmapped = _group_findings(mapped)
    order = list(qm.PRIMITIVE_TABLE)

    def sort_key(key):
        project, canonical, bits = key
        return (str(project), order.index(canonical), -1 if bits is None else bits)

    entries = [
        _build_entry(f"CBOM-{n:03d}", key, groups[key], project_facts.get(key[0], {}))
        for n, key in enumerate(sorted(groups, key=sort_key), start=1)
    ]
    return {
        "cbom_version": CBOM_VERSION,
        "project_count": len({e["project"] for e in entries}),
        "entry_count": len(entries),
        "finding_count": len(mapped),
        "entries": entries,
        "unmapped": unmapped,
        "references": list(REFERENCES),
        "notes": list(NOTES),
    }


def build_cbom_from_files(findings_path, facts_path=None):
    """Read findings (+ optional manual facts), map them, build the CBOM.

    Confirmed size overrides in the facts file are applied before mapping.
    Returns (cbom, mapped).
    """
    findings, _problems, _report = qm.prepare_findings(findings_path, facts_path)
    mapped = qm.map_findings(findings)
    facts = load_facts(facts_path) if facts_path else None
    return build_cbom(mapped, facts), mapped


def write_cbom_json(cbom, path):
    """Write the CBOM as indented UTF-8 JSON (machine-readable output)."""
    qm.write_json(path, cbom)


def _parse(args, value_flags, bool_flags=()):
    """Tiny argument parser. Returns (paths, values, bools) or None on error."""
    values = {flag: None for flag in value_flags}
    bools = {flag: False for flag in bool_flags}
    paths = []
    it = iter(args)
    for arg in it:
        if arg in values:
            value = next(it, None)
            if value is None:
                return None
            values[arg] = value
        elif arg in bools:
            bools[arg] = True
        else:
            paths.append(arg)
    return paths, values, bools

# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def _md(value):
    """Format a value for a Markdown table cell ('-' for empty, '|' escaped)."""
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_markdown(cbom):
    """Render the CBOM as a human-readable Markdown document (deterministic)."""
    lines = [
        "# Cryptographic Bill of Materials (CBOM)", "",
        f"Entries: {cbom['entry_count']} | Projects: {cbom['project_count']} | "
        f"Findings covered: {cbom['finding_count']} | Unmapped: {len(cbom['unmapped'])}", "",
        "Quantum risk, classical risk and padding risk are shown separately on "
        "purpose: textbook RSA is dangerous because it is deterministic, not "
        "because of Shor's algorithm.", "",
        "| ID | Project | Primitive | Size (bits) | Size status | Quantum threat | "
        "Logical qubits (est.) | Classical risk | Padding | Recommended PQC |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in cbom["entries"]:
        q = e["quantum_risk"]
        lines.append(
            f"| {_md(e['id'])} | {_md(e['project'])} | {_md(e['primitive'])} | "
            f"{_md(e['key_size_bits'])} | {_md(e['size_status'])} | "
            f"{_md(q['algorithm'] + ' (' + q['impact'] + ')')} | "
            f"{_md(q['logical_qubits_estimate'])} | {_md(e['classical_risk']['status'])} | "
            f"{_md(e['padding_risk']['status'])} | {_md(e['recommended_pqc']['algorithm'])} |")
    lines.append("")

    lines += ["## Evidence", ""]
    for e in cbom["entries"]:
        lines.append(f"- {e['id']}: {', '.join(e['files'])}")
    lines.append("")

    open_items = [e for e in cbom["entries"] if e["size_status"] in ("unverified", "unknown")]
    if open_items:
        lines += ["## Open data questions", "",
                  "These sizes are not verified. Qubit estimates and classical "
                  "assessments for them may change.", ""]
        lines += [f"- {e['id']} ({e['project']}, {e['primitive']}): size "
                  f"{_md(e['key_size_bits'])} is {e['size_status']}." for e in open_items]
        lines.append("")

    if cbom["unmapped"]:
        lines += ["## Unmapped findings", ""]
        lines += [f"- {u['project']} {u['file']}:{u['line']}: {u['primitive']}"
                  for u in cbom["unmapped"]]
        lines.append("")

    lines += ["## Notes", ""] + [f"- {n}" for n in cbom["notes"]] + [""]
    lines += ["## References", ""] + [f"- {r}" for r in cbom["references"]] + [""]
    return "\n".join(lines)


def write_cbom_markdown(cbom, path):
    """Write the Markdown rendering of the CBOM to a file."""
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(cbom))

# ---------------------------------------------------------------------------
# Consistency check
# ---------------------------------------------------------------------------
def check_consistency(cbom, mapped, json_path=None, md_path=None):
    """Verify the CBOM agrees with its source data and with its output files.

    Checks: schema validity, entry/finding counts against the mapped
    findings, each entry's size, algorithm and file references against its
    source group, and (if paths are given) that the JSON and Markdown files on
    disk match the in-memory CBOM exactly. Returns a list of problems.
    """
    problems = list(validate_cbom(cbom))
    groups, unmapped = _group_findings(mapped)
    if cbom.get("finding_count") != len(mapped):
        problems.append(f"finding_count {cbom.get('finding_count')} != {len(mapped)} mapped findings")
    if len(cbom.get("unmapped", [])) != len(unmapped):
        problems.append("unmapped count differs from the mapped findings")
    entries = cbom.get("entries", [])
    if len(entries) != len(groups):
        problems.append(f"{len(entries)} entries but {len(groups)} source groups")
    for entry in entries:
        key = (entry.get("project"), entry.get("primitive"), entry.get("key_size_bits"))
        group = groups.get(key)
        if group is None:
            problems.append(f"{entry.get('id')}: no source findings for {key}")
            continue
        if entry["quantum_risk"]["algorithm"] != group[0]["quantum_algorithm"]:
            problems.append(f"{entry['id']}: quantum algorithm differs from the mapper output")
        if entry["files"] != _file_refs(group):
            problems.append(f"{entry['id']}: file references differ from the source findings")
    if json_path:
        with open(json_path, "r", encoding="utf-8") as fh:
            if json.load(fh) != cbom:
                problems.append(f"{json_path} does not match the CBOM")
    if md_path:
        with open(md_path, "r", encoding="utf-8") as fh:
            if fh.read() != render_markdown(cbom):
                problems.append(f"{md_path} does not match the CBOM")
    return problems


USAGE = ("usage: cbom.py FINDINGS.json [--facts FILE] [--json OUT.json] "
         "[--md OUT.md] [--check]")


def main(argv=None):
    """CLI entry point.

    python cbom.py FINDINGS.json [--facts FILE] [--json OUT.json] [--md OUT.md] [--check]

    --check re-reads the written JSON and Markdown files and verifies they
    agree with each other and with the source findings (exit 1 if not).
    """
    parsed = _parse(list(sys.argv[1:] if argv is None else argv),
                    ("--facts", "--json", "--md"), ("--check",))
    if parsed is None or len(parsed[0]) != 1:
        print(USAGE)
        return 2
    paths, values, flags = parsed
    cbom, mapped = build_cbom_from_files(paths[0], values["--facts"])
    problems = validate_cbom(cbom)
    for problem in problems:
        print(f"CBOM INVALID: {problem}")
    print(f"CBOM: {cbom['entry_count']} entries from {cbom['finding_count']} findings "
          f"({len(cbom['unmapped'])} unmapped)")
    if values["--json"]:
        write_cbom_json(cbom, values["--json"])
        print(f"JSON written to {values['--json']}")
    if values["--md"]:
        write_cbom_markdown(cbom, values["--md"])
        print(f"Markdown written to {values['--md']}")
    if flags["--check"]:
        found = check_consistency(cbom, mapped, values["--json"], values["--md"])
        for problem in found:
            print(f"CONSISTENCY: {problem}")
        print("CONSISTENCY: OK" if not found else f"CONSISTENCY: {len(found)} problem(s)")
        problems += found
    return 1 if problems else 0

if __name__ == "__main__":
    sys.exit(main())
