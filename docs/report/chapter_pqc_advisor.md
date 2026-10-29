# Chapter: PQC advisor

## 1. Quantum computing in this project, and where it is not
ML-KEM (FIPS 203), ML-DSA (FIPS 204), SLH-DSA (FIPS 205) and AES-GCM are classical algorithms built to resist quantum
attacks. They run on ordinary computers; "post-quantum" means safe against quantum attacks, not that a quantum computer is used.
Quantum computing appears in this project in two roles: attacks (Shor, Grover, simulated at toy size) and a defence
(BB84 key distribution, simulated). All quantum results are Aer simulator, toy size.

## 2. Where each technique goes
| Layer | Today | Recommended | Why |
|---|---|---|---|
| L1 Message encryption | RSA, no padding | ML-KEM-768 + HKDF + AES-256-GCM | Shor breaks RSA. ML-KEM replaces RSA's key-transport role; it does not encrypt the message. |
| L3 Integrity | none or CRC32 | AES-GCM tag | CRC32 is not cryptographic and works as a key-check oracle; the GCM tag makes tampering fail loudly. |
| L5 Sender authenticity | none | ML-DSA-65 (optional) | Proves who sent the payload; verification happens before decryption. SLH-DSA is the conservative alternative with much larger signatures. |
| L2 Frame-selection key | SHA-256 of a passphrase, frames 0 to 255 only | 256-bit random key, HKDF or HMAC-SHA256 | Symmetric: Grover halves 256 bits to about 128, which is acceptable. No PQC algorithm needed. |
| Hiding layer | LSB, fixed start, no secret | Not a PQC question | Add a key-dependent order and measure steganalysis. |

## 3. How the hybrid flow works
The sender encapsulates to the receiver's ML-KEM-768 public key. HKDF-SHA256 turns the shared secret into an AES-256 key.
AES-256-GCM encrypts the message and authenticates it. The hidden blob is KEM ciphertext (1,088 B) + nonce (12 B) +
tag (16 B) + AES ciphertext, so the overhead is 1,116 B. Optional signing adds an ML-DSA-65 signature of 3,309 B.

## 4. Parameter sets
| Set | NIST category | Public key (B) | Ciphertext or signature (B) |
|---|---|---|---|
| ML-KEM-512 | 1 | 800 | 768 |
| ML-KEM-768 | 3 | 1,184 | 1,088 |
| ML-KEM-1024 | 5 | 1,568 | 1,568 |
| ML-DSA-44 | 2 | 1,312 | 2,420 |
| ML-DSA-65 | 3 | 1,952 | 3,309 |
| ML-DSA-87 | 5 | 2,592 | 4,627 |
Default: ML-KEM-768 and ML-DSA-65. Choose ML-KEM-512 only when payload capacity is the binding limit: its KEM ciphertext is 768 B instead of 1,088 B, 320 B less. Choose ML-KEM-1024 for data that must stay secret longest: its ciphertext is 1,568 B, 480 B more. For signatures, ML-DSA-44 saves 889 B per payload (2,420 B against 3,309 B) and ML-DSA-87 adds 1,318 B (4,627 B). Sizes are from the FIPS parameter tables and are checked by tests/test_sizes_match_libraries.py

## 5. Cost of the larger payload
The ML-KEM blob is far bigger than an RSA ciphertext and may be easier to detect when hidden.
[FILL: steganalysis results from Vaibhav's evidence document (ones fraction, chi-square, header scan), with the version each was measured on.]
Migration fixes the encryption layer, not the hiding layer. In the video project the header scan can still find the data frames.

## 6. What the prototypes prove and what they do not
They round-trip a message and fail on a tampered payload or a wrong key. kyber-py and dilithium-py are educational and not
hardened against timing attacks; a native library such as liboqs-python is the production route.
[FILL: whether results were measured on the pinned code or on the reference backend.]

## 7. QKD
A key from BB84 could replace the ML-KEM step and cut the overhead from 1,116 B to 28 B, but it needs a live quantum link and
dedicated optical hardware and an authenticated classical channel (ML-DSA in our simulation). Our BB84 is simulated, has no
error correction, and only noiseless runs produce a key. ML-KEM stays the software-only recommendation.

## 8. Standards status
FIPS 203, 204 and 205 were published in August 2024. NIST IR 8547 (quantum-vulnerable public-key algorithms deprecated after 2030
and disallowed after 2035) was finalised on 27 October 2026 (csrc.nist.gov/pubs/ir/8547/final; last checked on 2026-10-29). Outside federal systems it is guidance.

## 9. Not shown
[FILL: list of what we did not do, from docs/attack_evidence.md.]