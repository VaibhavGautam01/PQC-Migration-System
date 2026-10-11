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
