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
