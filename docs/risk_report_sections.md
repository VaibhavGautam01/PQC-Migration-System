# Risk report sections (generated)

## Risk percentages by layer

The percentage is a transparent weighted score from 0 to 100. It is not the probability of an attack.

### Image project (pinned commit bb6d944)

| Layer | Component | Quantum % | Classical % | Overall % | Band |
|---|---|---|---|---|---|
| L1 | RSA (textbook, no padding) | 86.6 | 100.0 | 91.9 | Critical |

Project score (0.7 x worst layer + 0.3 x average): 91.9

### Video project (pinned commit 4514806)

| Layer | Component | Quantum % | Classical % | Overall % | Band |
|---|---|---|---|---|---|
| L1 | RSA (textbook, no padding) | 79.1 | 61.0 | 71.8 | High |
| L2 | SHA-256 of passphrase (frame-selection key) | 9.0 | 76.0 | 35.8 | Moderate |
| L3 | CRC32 (integrity, key-check oracle) | not yet scored | not yet scored | not yet scored | not yet scored |

Project score (0.7 x worst layer + 0.3 x average): 66.4

## PQC advisor

ML-KEM, ML-DSA and AES-GCM are classical algorithms that resist quantum attacks. The prototype libraries are educational, not production crypto.

| Layer | Today | Recommended | Standard | Sizes (bytes) |
|---|---|---|---|---|
| L1 | RSA, no padding | ML-KEM-768 + HKDF + AES-256-GCM | FIPS 203 | public_key: 1,184, ciphertext: 1,088 |
| L2 | SHA-256 of a passphrase, frames 0 to 255 only | 256-bit random key with HKDF or HMAC-SHA256 to pick frames | RFC 5869 / FIPS 198-1 | key: 32 |
| L3 | none or CRC32 | AES-GCM authentication tag | NIST SP 800-38D | nonce: 12, tag: 16 |
| L5 | none | ML-DSA-65 signature (optional) | FIPS 204 | public_key: 1,952, signature: 3,309 |
| HIDING | fixed start, no secret | key-dependent pixel order (not a PQC question) | n/a | n/a |

## Before and after migration

Same scoring engine for both columns. Any remaining floor is explained in the validation chapter.

### Image project

| Layer | Overall % before | Overall % after | Recommendation |
|---|---|---|---|
| L1 | 91.9 | 4.7 | ML-KEM-768 + HKDF + AES-256-GCM |

### Video project

| Layer | Overall % before | Overall % after | Recommendation |
|---|---|---|---|
| L1 | 71.8 | not yet scored | ML-KEM-768 + HKDF + AES-256-GCM |
| L2 | 35.8 | not yet scored | 256-bit random key with HKDF or HMAC-SHA256 to pick frames |
| L3 | not yet scored | not yet scored | AES-GCM authentication tag |

## Worked reference values (from the risk model specification)

These cases are defined by the model, with X = 5, Y = 2, Z = 10 years. The engine must reproduce them. They are not measurements of our projects.

| Case | Quantum % | Classical % | Overall % |
|---|---|---|---|
| RSA-512 without padding | 84.1 | 100.0 | 90.4 |
| RSA-1024 without padding | 81.6 | 80.0 | 80.9 |
| RSA-2048 with OAEP | 79.1 | 8.5 | 50.8 |
| ML-KEM-768 + AES-256-GCM | 4.5 | 5.0 | 4.7 |
