## Recommendation: Migrate to ML-KEM-768

### Summary

Replace RSA key exchange and key encryption in both audited projects with
**ML-KEM-768**, the lattice-based key-encapsulation mechanism standardized in
NIST FIPS 203 (2024). Where RSA is used for digital signatures, replace it
with **ML-DSA** (FIPS 204) instead, since ML-KEM does not sign.

### Why RSA must be replaced

Shor's algorithm breaks RSA completely (see the qubit estimates above).
Increasing the key size does not fix this, because the attack runs in
polynomial time. Only a different mathematical problem helps.

### Why ML-KEM-768

| Reason | Detail |
|---|---|
| Standardized | NIST FIPS 203, so it is no longer experimental |
| Quantum-resistant | Based on the Module-LWE lattice problem, with no known efficient quantum attack |
| Security level | NIST Category 3, comparable to AES-192 |
| Balanced choice | ML-KEM-512 is the minimum level; ML-KEM-1024 gives more margin at higher cost; 768 is the usual default |
| Practical | Public keys and ciphertexts are about 1.2 KB and 1.1 KB, and operations are fast |

### Per-project guidance

| Project | Finding | Action |
|---|---|---|
| Secure-Video-Steganography | RSA, 1024-bit modulus | Replace with ML-KEM-768 for key protection. Also weak classically by current standards |
| Final-Year-project-part1 | RSA, 32-bit and 256-bit moduli | Replace with ML-KEM-768. Breakable today on a normal computer, so migrate as a priority |
| Secure-Video-Steganography | SHA-256 | No change needed. About 128-bit effective security under Grover's |

### Migration notes

- Consider a **hybrid** deployment (for example classical X25519 combined
  with ML-KEM-768) during the transition, so security does not depend on a
  single new algorithm.
- Use a vetted library (for example liboqs or a maintained binding) rather
  than implementing ML-KEM manually. The audited projects implement RSA by
  hand, and the same mistake must not be repeated.
- Standardized key and ciphertext sizes are larger than RSA's, so check
  storage and message-size limits.

### Limitations

This recommendation is based on static scanning. Confirm the role RSA plays
in each project before migrating, since signatures and encryption need
different replacements.