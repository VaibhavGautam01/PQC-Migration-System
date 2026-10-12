# CBOM entry schema

One entry per **(project, primitive, key size)**. Quantum risk, classical risk and
padding risk are separate blocks on purpose: textbook RSA is dangerous because it
is deterministic, not because of Shor's algorithm.

```json
{
  "id": "CBOM-001",
  "project": "Secure-Video-Steganography",
  "primitive": "RSA",
  "key_size_bits": 1024,
  "size_basis": "where the size came from",
  "size_status": "override-confirmed | scanner-reported | unverified | unknown",
  "files": ["path/to/file.py:42"],
  "quantum_risk": {
    "algorithm": "Shor's algorithm",
    "impact": "BROKEN | WEAKENED",
    "logical_qubits_estimate": 2051,
    "estimate_basis": "how the number was computed and what it excludes",
    "post_quantum_security_bits": 0
  },
  "classical_risk": {
    "status": "practically-breakable | below-minimum | meets-minimum | weak-collision-resistance | unknown",
    "basis": "why",
    "evidence": []
  },
  "padding_risk": {
    "status": "none (textbook RSA) | flagged | unknown | not-applicable",
    "weakness": "what is wrong, or null",
    "source": "who confirmed it",
    "automated_flag": "edge_flag text from findings.json, or null"
  },
  "recommended_pqc": {
    "algorithm": "ML-KEM-768",
    "standard": "NIST FIPS 203",
    "rationale": "why this algorithm"
  },
  "notes": []
}
```

## Rules

- `key_size_bits` is the **modulus** size for RSA/DSA/DH, never the prime size.
- `logical_qubits_estimate` is only computed for RSA (2n+3, Beauregard 2003). It is
  `null` for other primitives. It counts logical qubits only; error-correction
  overhead is excluded.
- `size_status` says how far to trust the size. `unverified` and `unknown` entries
  are listed under "Open data questions" in the Markdown output.
- `quantum_risk` must never contain padding fields (checked by `validate_entry`).
- `primitive` is one of RSA, ECC, DSA, DH, AES, SHA or a legacy cipher (3DES, DES, RC4, BLOWFISH). Legacy ciphers route to Grover's and are marked classically weak.
- `automated_flag` is the edge-case module's flag (`edge_flag`). It sits beside the manually confirmed status and never feeds the quantum score.
- `experiments` (top level) lists results from **local small-key copies**, which are not
  the projects of record. Each target must say "not the project of record". They are never
  attached to an entry and are not evidence about the real key sizes.
- RSA entries can carry `size_notes` from `data/manual_facts.json` in `notes` (for example
  "user-selectable, UI default 2048").
- The CBOM has no timestamp, so re-running the generator on the same input gives
  byte-identical output.

A machine-readable JSON Schema is in `schemas/cbom.schema.json`.
