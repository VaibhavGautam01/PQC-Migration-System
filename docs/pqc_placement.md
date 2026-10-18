# PQC placement: where ML-KEM, ML-DSA and the others go

Status: DRAFT (Week 1 Day 1). Check every size against the FIPS text before this is final.
ML-KEM, ML-DSA, SLH-DSA and AES-GCM are classical algorithms that resist quantum attacks. They are not quantum circuits.
All quantum attack results elsewhere in this project are Aer simulator, toy size.

## Layer recommendations

| Layer | Today | Recommended | Notes |
|---|---|---|---|
| L1 Message encryption | RSA, no padding | ML-KEM-768 (FIPS 203) + AES-256-GCM, HKDF between them | Sender encapsulates to the receiver's ML-KEM public key; the shared secret becomes the AES key. Payload = KEM ciphertext (1,088 B) + nonce + tag + AES ciphertext. ML-KEM replaces RSA's key-transport role; it does not encrypt the message. |
| L3 Integrity | none or CRC32 | AES-GCM tag | Removes the CRC key-check oracle; tampering fails loudly. |
| L5 Sender authenticity | none | ML-DSA-65 (FIPS 204), optional | Signature 3,309 B, public key 1,952 B. SLH-DSA (FIPS 205) is the conservative alternative with much larger signatures. |
| L2 Frame-selection key | SHA-256 of passphrase, frames 0-255 only | 256-bit random key, HKDF or HMAC-SHA256 to pick frames across the whole video | Symmetric: Grover halves 256 bits to about 128, which is acceptable. No PQC algorithm needed. |
| Hiding layer | LSB / XOR-LSB, fixed start | Not a PQC question | Add key-dependent pixel order and measure steganalysis. A bigger payload is easier to detect. |

## Parameter sets (bytes) - to verify against FIPS 203 / 204

| Parameter set | NIST category | Public key | Ciphertext or signature |
|---|---|---|---|
| ML-KEM-512 | 1 | 800 | 768 |
| ML-KEM-768 | 3 | 1,184 | 1,088 |
| ML-KEM-1024 | 5 | 1,568 | 1,568 |
| ML-DSA-44 | 2 | 1,312 | 2,420 |
| ML-DSA-65 | 3 | 1,952 | 3,309 |
| ML-DSA-87 | 5 | 2,592 | 4,627 |

Verification log:
- [ ] FIPS 203 (ML-KEM sizes) checked on: ____
- [ ] FIPS 204 (ML-DSA sizes) checked on: ____
- [ ] FIPS 205 (SLH-DSA signature sizes) noted on: ____

## Libraries
- kyber-py 1.2.0 (ML-KEM) and dilithium-py 1.5.1 (ML-DSA): pure Python, educational, not hardened against timing attacks.
- AES-GCM: PyCryptodome 4.0.0.
- Fine for a prototype and demo; NOT production crypto. Production route: liboqs-python.

## Standards status
- FIPS 203, 204, 205: published August 2024.
- NIST IR 8547 (quantum-vulnerable public-key algorithms deprecated after 2030, disallowed after 2035): initial public draft published 12 November 2024 (comment period closed January 2025). Call the dates "proposed" unless a final version is confirmed. Last checked: ____
## Sizes table (generated from data/pqc_recommendations.json)

| Layer | Technique | Parameter set | Sizes (bytes) |
|---|---|---|---|
| L1 | ML-KEM-768 + HKDF + AES-256-GCM | ML-KEM-768 | public_key: 1,184, ciphertext: 1,088 |
| L2 | 256-bit random key with HKDF or HMAC-SHA256 to pick frames | 256-bit key | key: 32 |
| L3 | AES-GCM authentication tag | 128-bit tag | nonce: 12, tag: 16 |
| L5 | ML-DSA-65 signature (optional) | ML-DSA-65 | public_key: 1,952, signature: 3,309 |
| HIDING | key-dependent pixel order (not a PQC question) | n/a | n/a |

## Payload size and capacity analysis

Computed by scripts/payload_capacity.py. Assumptions are stated at the top of the script (header size from the reference backend, not yet the pinned project).

Assumed header: 4 B. Hybrid overhead: 1116 B.

| Message (B) | RSA bits | RSA ciphertext (B) | Hybrid blob (B) | Blob / RSA |
|---|---|---|---|---|
| 16 | 512 | 64 | 1132 | 17.7x |
| 16 | 1024 | 128 | 1132 | 8.8x |
| 16 | 2048 | 256 | 1132 | 4.4x |
| 16 | 3072 | 384 | 1132 | 2.9x |
| 64 | 512 | 128 | 1180 | 9.2x |
| 64 | 1024 | 128 | 1180 | 9.2x |
| 64 | 2048 | 256 | 1180 | 4.6x |
| 64 | 3072 | 384 | 1180 | 3.1x |
| 256 | 512 | 320 | 1372 | 4.3x |
| 256 | 1024 | 384 | 1372 | 3.6x |
| 256 | 2048 | 512 | 1372 | 2.7x |
| 256 | 3072 | 384 | 1372 | 3.6x |
| 1024 | 512 | 1088 | 2140 | 2.0x |
| 1024 | 1024 | 1152 | 2140 | 1.9x |
| 1024 | 2048 | 1280 | 2140 | 1.7x |
| 1024 | 3072 | 1152 | 2140 | 1.9x |

| Payload | Mode | Smallest square image (pixels per side) |
|---|---|---|
| hybrid, message 16 B | 1 LSB, R channel only | 96 |
| hybrid, message 16 B | 1 LSB, RGB | 56 |
| RSA-1024, message 16 B | 1 LSB, RGB | 19 |
| RSA-2048, message 16 B | 1 LSB, RGB | 27 |
| hybrid, message 64 B | 1 LSB, R channel only | 98 |
| hybrid, message 64 B | 1 LSB, RGB | 57 |
| RSA-1024, message 64 B | 1 LSB, RGB | 19 |
| RSA-2048, message 64 B | 1 LSB, RGB | 27 |
| hybrid, message 256 B | 1 LSB, R channel only | 105 |
| hybrid, message 256 B | 1 LSB, RGB | 61 |
| RSA-1024, message 256 B | 1 LSB, RGB | 33 |
| RSA-2048, message 256 B | 1 LSB, RGB | 38 |
| hybrid, message 1024 B | 1 LSB, R channel only | 131 |
| hybrid, message 1024 B | 1 LSB, RGB | 76 |
| RSA-1024, message 1024 B | 1 LSB, RGB | 56 |
| RSA-2048, message 1024 B | 1 LSB, RGB | 59 |
