# PQC advisor (draft chapter)

## What the advisor does
For each layer of the two projects the advisor names a technique, a parameter set, the standard, the sizes and the reason.
It reads data/pqc_recommendations.json; the same engine that scores "before" scores "after".

## Where each technique goes
| Layer | Today | Recommended | Standard |
|---|---|---|---|
| L1 Message encryption | textbook RSA | ML-KEM-768 + AES-256-GCM, HKDF between | FIPS 203 |
| L2 Frame-selection key | SHA-256 of a passphrase | 256-bit random key, HKDF or HMAC-SHA-256 | none needed |
| L3 Integrity | none / CRC32 | AES-GCM tag | NIST SP 800-38D |
| L5 Sender authenticity | none | ML-DSA-65 (optional) | FIPS 204 |
| Hiding | LSB / XOR-LSB | not a PQC question; measure steganalysis | n/a |

Sizes (ML-KEM-768 public key 1,184 B, ciphertext 1,088 B; ML-DSA-65 public key 1,952 B, signature 3,309 B) are checked by tests/test_sizes_match_libraries.py.

## Quantum or not
ML-KEM, ML-DSA and AES-256-GCM are classical algorithms that resist quantum attacks. They run on ordinary computers.
Quantum computing appears only in our attack demonstrations (Shor, Grover) and the BB84 simulation, all on the Aer simulator, toy size.

## Standards status
NIST IR 8547 was finalised on 27 October 2026. It keeps deprecation after 2030 and disallowance after 2035 for quantum-vulnerable public-key algorithms; for non-federal systems it is guidance. FIPS 203, 204 and 205 date from August 2024.

## Measured effect
Before and after scores: insert from outputs/risk_scores.json (scripts/risk_report_sections.py).
The after score does not reach zero. State exactly which residual factors cause that.

## Limits
- kyber-py and dilithium-py are educational, not hardened against timing attacks; liboqs-python is the production route.
- A larger PQC payload is easier to detect; steganalysis results are in docs/attack_evidence.md.
- The risk percentage is a transparent weighted score, not a probability.
