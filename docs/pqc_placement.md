# PQC placement (draft)

Measured with: kyber-py <ver>, dilithium-py <ver> (educational, not hardened; production route is liboqs-python).

| Layer | Today | Recommended | Standard | Sizes | Why |
|---|---|---|---|---|---|
| L1 Message encryption | RSA, no padding | ML-KEM-768 + AES-256-GCM (HKDF between) | FIPS 203 | pk 1,184 B, ct 1,088 B | ML-KEM transports the key; it does not encrypt the message |
| L2 Frame-selection key | SHA-256 of passphrase, frames 0-255 only | 256-bit random key + HKDF / HMAC-SHA-256 | none needed | 32 B | Grover halves 256 bits to about 128, acceptable |
| L3 Integrity | none / CRC32 | AES-GCM tag | NIST SP 800-38D | 16 B tag | removes the CRC32 key-check oracle |
| L5 Signature | none | ML-DSA-65 (optional) | FIPS 204 | pk 1,952 B, sig 3,309 B | SLH-DSA (FIPS 205) is the conservative alternative |
| Hiding | LSB / XOR-LSB | not a PQC question | n/a | n/a | key-dependent pixel order; measure steganalysis |

## Status of NIST IR 8547
The official NIST page lists it as an initial public draft (12 Nov 2024). The 2030 / 2035 dates are PROPOSED.
Checked on: <date>. Source: csrc.nist.gov/pubs/ir/8547

## Approval-deck references checked
See docs/deck_check.md.
