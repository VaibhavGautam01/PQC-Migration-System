# Quantum-Algorithm Mapping Report

> **DRAFT: generated from SAMPLE (dummy) findings, not from real scanner output.**

Each finding from the Stage 1 scanner is mapped to the quantum algorithm that threatens it. This is a theoretical mapping; it says which attack applies, not that the attack is practical today.

**Total findings:** 10  
**Projects:** 1

## SAMPLE-DUMMY-DATA

### Summary

| Primitive | Findings | Quantum algorithm | Impact | PQC replacement |
|---|---|---|---|---|
| AES | 2 | Grover's algorithm | WEAKENED | Keep AES, use 256-bit keys (no new algorithm needed) |
| DH | 1 | Shor's algorithm | BROKEN | ML-KEM |
| DSA | 1 | Shor's algorithm | BROKEN | ML-DSA |
| ECC | 1 | Shor's algorithm | BROKEN | ML-KEM (ECDH replacement), ML-DSA (ECDSA/EdDSA replacement) |
| RSA | 2 | Shor's algorithm | BROKEN | ML-KEM (encryption/key exchange), ML-DSA (signatures) |
| SHA | 2 | Grover's algorithm | WEAKENED | Keep SHA-2/SHA-3 with 256-bit or larger output |
| - | 1 | UNKNOWN | UNKNOWN | Manual review required |

### Findings

| File:Line | Primitive | Size (bits) | Size basis | PQ-security (bits) | Warning |
|---|---|---|---|---|---|
| sample/rsa_demo.py:10 | RSA | 1024 | sample | 0 | - |
| sample/rsa_small.py:4 | RSA | 16 | prime size (modulus unknown) | 0 | modulus_bits missing; key_size may be the prime size, not the modulus size |
| sample/ecc_demo.py:22 | ECDSA | 256 | sample | 0 | - |
| sample/dsa_demo.py:8 | DSA | 2048 | sample | 0 | - |
| sample/dh_demo.py:15 | Diffie-Hellman | 2048 | sample | 0 | - |
| sample/aes_demo.py:30 | AES-128 | 128 | sample | 64 | - |
| sample/aes_demo.py:45 | AES-256 | 256 | sample | 128 | - |
| sample/hash_demo.py:6 | SHA-256 | 256 | sample | 128 | - |
| sample/hash_demo.py:12 | SHA-1 | 160 | sample | 80 | - |
| sample/other.py:3 | Blowfish | - | sample | - | - |

## Notes and limitations

- Asymmetric primitives (RSA, ECC, DSA, DH) are broken by Shor's algorithm once a large enough fault-tolerant quantum computer exists. PQ-security is shown as 0 for these.
- Symmetric and hash primitives are only weakened by Grover's algorithm (a quadratic speed-up, not a full break); PQ-security is about half the classical bits.
- Padding weaknesses (e.g. textbook RSA) and classical key-strength problems are separate from the quantum threat and are reported separately.
- Size warnings: 1. Unrecognised primitives: 1.
