# Cryptographic Bill of Materials (CBOM)

Entries: 6 | Projects: 2 | Findings covered: 31 | Unmapped: 0

Quantum risk, classical risk and padding risk are shown separately on purpose: textbook RSA is dangerous because it is deterministic, not because of Shor's algorithm.

| ID | Project | Primitive | Size (bits) | Size status | Quantum threat | Logical qubits (est.) | Classical risk | Padding | Recommended PQC |
|---|---|---|---|---|---|---|---|---|---|
| CBOM-001 | Final-Year-project-part1 | RSA | - | unknown | Shor's algorithm (BROKEN) | - | unknown | none (textbook RSA) | ML-KEM-768 |
| CBOM-002 | Final-Year-project-part1 | RSA | 8 | override-confirmed | Shor's algorithm (BROKEN) | 19 | practically-breakable | none (textbook RSA) | ML-KEM-768 |
| CBOM-003 | Final-Year-project-part1 | RSA | 256 | override-confirmed | Shor's algorithm (BROKEN) | 515 | practically-breakable | none (textbook RSA) | ML-KEM-768 |
| CBOM-004 | Secure-Video-Steganography | RSA | - | unknown | Shor's algorithm (BROKEN) | - | unknown | none (textbook RSA) | ML-KEM-768 |
| CBOM-005 | Secure-Video-Steganography | RSA | 2048 | override-confirmed | Shor's algorithm (BROKEN) | 4099 | meets-minimum | none (textbook RSA) | ML-KEM-768 |
| CBOM-006 | Secure-Video-Steganography | SHA | 256 | scanner-reported | Grover's algorithm (WEAKENED) | - | meets-minimum | not-applicable | SHA-256 or larger (SHA-2 / SHA-3) |

## Evidence

- CBOM-001: rsa_utils.py:22, rsa_utils.py:32, rsa_utils.py:33, rsa_utils.py:35, rsa_utils.py:37, rsa_utils.py:39, rsa_utils.py:45, rsa_utils.py:50
- CBOM-002: app.py:229, app.py:373, main.py:83, r_channel_stego.py:42, r_channel_stego.py:52, r_channel_stego.py:54, r_channel_stego.py:59
- CBOM-003: app.py:239, app.py:385, main.py:101, rsa_utils.py:27, rsa_utils.py:28, rsa_utils.py:30
- CBOM-004: app.py:263, rsa_crypto.py:45, rsa_crypto.py:52, rsa_crypto.py:53, rsa_crypto.py:56, rsa_crypto.py:142, rsa_crypto.py:170
- CBOM-005: rsa_crypto.py:48, rsa_crypto.py:49
- CBOM-006: frame_selector.py:32

## Supporting experiments (local small-key snapshots)

These ran on local small-key copies of the projects, not on the projects of record. They show what a small modulus costs an attacker; they are not evidence about the key sizes in the table above.

- EXP-IMAGE-31: Image steganography attack end to end: extract the ciphertext, factor n, decrypt. Target: local small-key snapshot (Vaibhav's ZIP copy of the image project, whose generate_keypair defaults to bits=16); not the project of record. Result: 31-bit modulus factored in 0.0002 s. Source: Vaibhav.
- EXP-VIDEO-95: Video steganography attack at a reduced key. It does not need the secret frame key: it scans for the 16-bit length header. Target: local small-key snapshot (video_stego_project_updated, reduced key made with generate_keypair(key_size=96)); not the project of record. Result: 95-bit modulus factored in 0.23 s. Source: Vaibhav.

## Open data questions

These sizes are not verified. Qubit estimates and classical assessments for them may change.

- CBOM-001 (Final-Year-project-part1, RSA): size - is unknown.
- CBOM-004 (Secure-Video-Steganography, RSA): size - is unknown.

## Notes

- Quantum risk, classical risk and padding risk are reported separately. Padding weaknesses such as textbook RSA are classical problems, not consequences of Shor's algorithm.
- Logical-qubit estimates use the 2n+3 circuit for factoring an n-bit modulus. They exclude error-correction overhead, so physical qubit counts are much larger.
- All quantum demonstrations in this project run on a simulator at toy sizes. Resource figures for RSA-1024/2048 are published estimates, not measurements.
- Grover's algorithm is a quadratic speed-up, not a full break: symmetric and hash primitives keep about half their classical security bits.

## References

- Shor, P. W. (1997). Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer. SIAM J. Comput. 26(5), 1484-1509.
- Grover, L. K. (1996). A fast quantum mechanical algorithm for database search. Proc. 28th ACM STOC, 212-219.
- Beauregard, S. (2003). Circuit for Shor's algorithm using 2n+3 qubits. Quantum Information & Computation 3(2), 175-185. arXiv:quant-ph/0205095.
- Gidney, C. and Ekera, M. (2021). How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits. Quantum 5, 433. arXiv:1905.09749.
- NIST FIPS 203 (2024). Module-Lattice-Based Key-Encapsulation Mechanism Standard (ML-KEM).
- NIST FIPS 204 (2024). Module-Lattice-Based Digital Signature Standard (ML-DSA).
