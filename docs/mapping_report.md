# Quantum-Algorithm Mapping Report

Each finding from the Stage 1 scanner is mapped to the quantum algorithm that threatens it. This is a theoretical mapping; it says which attack applies, not that the attack is practical today.

**Total findings:** 26  
**Projects:** 2

## Final-Year-project-part1

### Summary

| Primitive | Findings | Quantum algorithm | Impact | PQC replacement |
|---|---|---|---|---|
| RSA | 17 | Shor's algorithm | BROKEN | ML-KEM (encryption/key exchange), ML-DSA (signatures) |

### Findings

| File:Line | Primitive | Size (bits) | Size basis | PQ-security (bits) | Warning |
|---|---|---|---|---|---|
| app.py:239 | RSA | 256 | keyword argument (per-prime assumed, modulus = 2 x) | 0 | - |
| app.py:385 | RSA | 256 | keyword argument (per-prime assumed, modulus = 2 x) | 0 | - |
| main.py:101 | RSA | 256 | keyword argument (per-prime assumed, modulus = 2 x) | 0 | - |
| r_channel_stego.py:42 | RSA | - | - | 0 | - |
| r_channel_stego.py:52 | RSA | - | - | 0 | - |
| r_channel_stego.py:54 | RSA | - | - | 0 | - |
| r_channel_stego.py:59 | RSA | - | - | 0 | - |
| rsa_utils.py:22 | RSA | - | - | 0 | - |
| rsa_utils.py:27 | RSA | 512 | resolved from 'bits' (per-prime, modulus = 2 x) | 0 | - |
| rsa_utils.py:28 | RSA | 512 | resolved from 'bits' (per-prime, modulus = 2 x) | 0 | - |
| rsa_utils.py:30 | RSA | 512 | resolved from 'bits' (per-prime, modulus = 2 x) | 0 | - |
| rsa_utils.py:33 | RSA | - | - | 0 | - |
| rsa_utils.py:35 | RSA | - | - | 0 | - |
| rsa_utils.py:37 | RSA | - | - | 0 | - |
| rsa_utils.py:39 | RSA | - | - | 0 | - |
| rsa_utils.py:45 | RSA | - | - | 0 | - |
| rsa_utils.py:50 | RSA | - | - | 0 | - |

## Secure-Video-Steganography

### Summary

| Primitive | Findings | Quantum algorithm | Impact | PQC replacement |
|---|---|---|---|---|
| RSA | 8 | Shor's algorithm | BROKEN | ML-KEM (encryption/key exchange), ML-DSA (signatures) |
| SHA | 1 | Grover's algorithm | WEAKENED | Keep SHA-2/SHA-3 with 256-bit or larger output |

### Findings

| File:Line | Primitive | Size (bits) | Size basis | PQ-security (bits) | Warning |
|---|---|---|---|---|---|
| app.py:263 | RSA | - | - | 0 | - |
| frame_selector.py:32 | SHA | 256 | literal in call | 128 | - |
| rsa_crypto.py:45 | RSA | - | - | 0 | - |
| rsa_crypto.py:48 | RSA | 1024 | resolved from 'half' (per-prime, modulus = 2 x) | 0 | - |
| rsa_crypto.py:49 | RSA | 1024 | resolved from 'half' (per-prime, modulus = 2 x) | 0 | - |
| rsa_crypto.py:53 | RSA | - | - | 0 | - |
| rsa_crypto.py:56 | RSA | - | - | 0 | - |
| rsa_crypto.py:142 | RSA | - | - | 0 | - |
| rsa_crypto.py:170 | RSA | - | - | 0 | - |

## Notes and limitations

- Asymmetric primitives (RSA, ECC, DSA, DH) are broken by Shor's algorithm once a large enough fault-tolerant quantum computer exists. PQ-security is shown as 0 for these.
- Symmetric and hash primitives are only weakened by Grover's algorithm (a quadratic speed-up, not a full break); PQ-security is about half the classical bits.
- Padding weaknesses (e.g. textbook RSA) and classical key-strength problems are separate from the quantum threat and are reported separately.
- Size warnings: 0. Unrecognised primitives: 0.
