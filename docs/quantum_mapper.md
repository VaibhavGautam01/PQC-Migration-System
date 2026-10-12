# quantum_mapper.py

Stage 2 of the pipeline. It reads the scanner's findings and, for each one, says
which quantum algorithm threatens it and what to migrate to.

```
scanner -> findings.json -> quantum_mapper -> mapped findings + mapping_report.md -> CBOM
```

## Mapping table

| Primitive | Family | Quantum algorithm | Impact | Hard problem | Recommended replacement |
|---|---|---|---|---|---|
| RSA | asymmetric | Shor's | BROKEN | Integer factorisation | ML-KEM (encryption / key exchange), ML-DSA (signatures) |
| ECC (ECDSA, ECDH, Ed25519, X25519) | asymmetric | Shor's | BROKEN | Elliptic-curve discrete log | ML-KEM / ML-DSA |
| DSA | asymmetric | Shor's | BROKEN | Discrete log | ML-DSA |
| DH | asymmetric | Shor's | BROKEN | Discrete log | ML-KEM |
| AES | symmetric | Grover's | WEAKENED | Key search | Keep AES, use 256-bit keys |
| SHA (SHA-1/2/3, HMAC-SHA) | hash | Grover's | WEAKENED | Preimage search | Keep SHA-2/SHA-3 with 256-bit or larger output |
| 3DES, DES, RC4, Blowfish (legacy) | symmetric | Grover's | WEAKENED | Key search | Replace with AES-256: already weak classically |

Routing rule: asymmetric goes to Shor's, symmetric and hash go to Grover's. The
module checks this rule against the table when it is imported.

Shor's is a full break. Grover's is a quadratic speed-up, not a break: the key or
output size is roughly halved (AES-128 about 64 bits by naive halving, AES-256 about
128 bits).

**AES-128 and NIST.** The 64-bit figure is a naive reading. NIST's post-quantum security
category 1 is defined relative to AES-128 key search, and NIST's call for proposals
(2016, section 4.A.5) estimates the quantum cost of that search at about 2^170 gates
divided by a depth limit (MAXDEPTH), far above 2^64, because Grover's parallelises
poorly. So the mapper says "not a break" for AES-128 and recommends AES-256 only for
extra margin on long-lived data.

**Legacy ciphers** (3DES, DES, RC4, Blowfish) are recognised and routed to Grover's,
but they are already weak classically (small effective key, 64-bit blocks, known
biases), so the advice is "replace", not "wait for quantum". 3DES and DES use a fixed
effective strength (112 and 56 bits) instead of the scanner's key size.

## Names the mapper understands

Case, hyphens and underscores are ignored. Examples: `RSA-2048` and `RSA-OAEP` (RSA),
`P-256`, `secp256r1`, `prime256v1`, `Ed25519`, `ED448`, `ECDHE` (ECC), `FFDHE2048`
and `DHE` (DH), `DSA-2048` (DSA), `AES-256-GCM`, `SHA3-512`, `HMAC-SHA256`,
`TripleDES`, `DES-EDE3`, `ARCFOUR`. A size in the name (`RSA-2048`, `P-256`) is used
only when the finding has no `modulus_bits` or `key_size`. Anything else becomes
UNKNOWN and is listed for manual review.

## Input

A JSON list (or `{"findings": [...]}`). Fields used:

| Field | Required | Meaning |
|---|---|---|
| project, file, line | yes | Where the finding is |
| primitive | yes | Name from the scanner (RSA, ECDSA, AES-256, SHA-256 ...) |
| modulus_bits | no | Modulus size for RSA/DSA/DH. **Preferred over key_size.** |
| key_size | no | Size reported by the scanner. For RSA this may be the prime size. |

`validate_findings()` reports missing fields, non-object entries and duplicates.

## Output fields added to each finding

| Field | Meaning |
|---|---|
| canonical_primitive | RSA, ECC, DSA, DH, AES, SHA, or None if unrecognised |
| family | asymmetric / symmetric / hash |
| quantum_algorithm | Shor's, Grover's, or UNKNOWN |
| impact | BROKEN, WEAKENED or UNKNOWN |
| pqc_replacement | Replacement text from the table |
| post_quantum_security_bits | 0 for Shor-broken primitives; half the size for Grover; None if size unknown |
| size_used_bits | The size actually used (modulus_bits, then key_size, then the size in the name) |
| size_warning | Set when an RSA/DSA/DH size may be a prime size |
| grover_assessment | Plain-English reading for AES, SHA and legacy-cipher findings |
| classically_weak | True for legacy ciphers, False for the rest, None if unrecognised |
| override_ids | Ids of confirmed manual overrides applied to this finding |

## Manual overrides

`data/manual_facts.json` holds facts the scanner cannot see. An override has a
`match` rule (project, file_contains, primitive, optional line), a `set` block
(usually modulus_bits and size_basis), a `source`, and a `confirmed` flag.

A `match` rule can use: `project`, `file_contains`, `line`, `lines` (a list of line
numbers), `primitive`, and `has_size: true` (only findings that already carry a size
from the scanner, so lines with no size are left alone). Use `lines` or `has_size` so an
override does not stamp a size onto operation lines such as `phi` or `pow`.

Only `"confirmed": true` overrides are applied. Unconfirmed ones are listed in
the report's **Data caveats** section so nobody forgets them.

## Commands

```bash
# map real findings and write the report
python src/quantum_mapper.py outputs/findings.json outputs/mapped_findings.json docs/mapping_report.md --overrides data/manual_facts.json

# fail if findings.json is malformed
python src/quantum_mapper.py outputs/findings.json outputs/mapped_findings.json --strict

# run the tests
python -m unittest discover -s tests -v
```

`outputs/mapped_findings.json` is generated data: do not commit it.

## Limits

- The mapping says which attack applies, not that the attack is practical today.
- Padding weaknesses (textbook RSA) and classical weaknesses (small keys) are
  not quantum findings and are reported separately. The mapping report shows the
  edge-case module's `edge_flag` in a "Padding flag" column beside each finding, but
  it never changes the quantum result.
- Sizes are only as good as the scanner plus the confirmed overrides; check the
  Data caveats section of the report.
- Everything quantum in this project runs on a simulator at toy sizes.
