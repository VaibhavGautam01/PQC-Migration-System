# Final Report: Stage 1 (Detection) and Stage 2 (Quantum Mapping)

**Project:** AI-Powered PQC Migration Advisor, Quantum-Vulnerability Testing Pipeline
**Institution:** Hindustan College of Science and Technology, Mathura (AKTU)
**Team:** Tarun Saxena, Vaibhav Gautam, Uday Pratap Singh, Yatharth Raghuvanshi

This report covers Stages 1 and 2 of the pipeline. Stage 3 (risk scoring, qubit cost) is summarised in section 5 and detailed in `risk_report.md`.

## 1. Overview

Public-key cryptography (RSA, ECC, DSA, Diffie-Hellman) is broken by Shor's algorithm on a large quantum computer. Symmetric primitives (AES, SHA) are only weakened by Grover's algorithm. The pipeline finds such cryptography in source code, maps each finding to the quantum algorithm that threatens it, estimates the qubit cost, and recommends a post-quantum replacement (ML-KEM).

| Stage | Purpose | Main files |
|---|---|---|
| 1. Detection | Find crypto in source code and read its key size | `scanner.py`, `extra_patterns.py`, `key_size.py`, `run_all.py`, `edge_cases.py` |
| 2. Quantum mapping | Map each primitive to Shor or Grover | `quantum_mapper.py` |
| 3. Risk and qubit cost | Qubit estimate, padding flags, risk report | `risk_report.md` and the estimator in `notebook/` |

## 2. Stage 1: Detection engine

### 2.1 Scanner

A static, regex-based scanner walks a codebase line by line and records every match.

- **47 detection patterns** across six families: RSA, ECC, DSA, DH, AES, SHA.
- RSA covers library key generation (PyCryptodome, `cryptography`, python-rsa, Java, `openssl genrsa`) and **hand-written textbook RSA**: `phi = (p-1)*(q-1)`, `pow(m, e, n)`, modular-inverse helpers, `65537`, and prime selection with `randprime`, `nextprime` or `isprime`.
- Each pattern has a confidence level (high, medium, low). Generic helpers such as `isprime()` are low confidence because they can also appear in non-crypto code.
- Patterns live in `scanner.py` (RSA) and `extra_patterns.py` (ECC, DSA, DH, AES, SHA, keypair wrapper calls).

### 2.2 Key-size extraction (`key_size.py`)

The key size decides the qubit cost, so it is extracted carefully:

- Reads literals (`RSA.generate(2048)`), keyword arguments (`key_size=4096`) and **variables resolved inside the same file** (`getPrime(half)` resolves through `half = key_size // 2` to a default value).
- Separates the **per-prime size** from the **modulus size** (modulus = 2 x prime size).
- Reads only the current call, so it never borrows a number from a neighbouring function (an early bug: `randprime(low, high)` once picked up `bits=256` from the next function).
- Rejects numbers that cannot be key sizes, such as the exponent 65537.

### 2.3 Combined output: `findings.json` (schema 1.1)

`run_all.py` scans both target projects and writes one file. Each finding records: project, file, line, primitive, pattern_id, confidence, key_size, modulus_bits, size_basis, snippet, **is_default**. Each project also stores the **git commit hash** of the scanned code, so the scan is reproducible.

`is_default` is true when a key size comes only from a function default value (for example `def generate_keypair(bits=256)`), not from a size that is really used.

### 2.4 Validation

| Check | Method | Result |
|---|---|---|
| Line check | Every finding compared with the real source line (`crosscheck.py`) | All findings match |
| Miss hunt | 166 crypto-looking lines without a finding triaged by hand | 109 comments, docstrings or UI text; 36 other code; 21 candidates read manually |
| Real gap found | `isprime()` prime selection in `r_channel_stego.py` | Fixed with pattern `RSA-MANUAL-PRIME-ISPRIME` |
| Not bugs | `GCD(e, phi)` and `phi % e` loops | Public-exponent helpers with no size or algorithm information |
| Tests | `run_tests.py` and the files in `tests/` | 92 tests, all pass |

## 3. Stage 1 results on the target projects

Scanner output (`findings.json`): **26 findings**, RSA 25 and SHA 1.

| Project | Findings | Primitives | Key observation |
|---|---|---|---|
| Secure-Video-Steganography | 9 | RSA 8, SHA 1 | Textbook RSA; size chosen in the UI (1024, 2048, 3072; default 2048); SHA-256 used for frame selection |
| Final-Year-project-part1 | 17 | RSA 17 | Textbook RSA; real use is `generate_keypair(bits=128)`, a 256-bit modulus; one module uses n < 256 |

### Key sizes found

| Project | Location | Modulus (bits) | Status |
|---|---|---|---|
| Part1 | `app.py:239, 385`, `main.py:101` | 256 | Really used, breakable by an ordinary computer today |
| Part1 | `rsa_utils.py:27, 28, 30` | 512 | **Default value only** (`is_default`); callers pass `bits=128` |
| Steganography | `rsa_crypto.py:48, 49` | 1024 | **Default value only**; the UI default is 2048 |
| Part1 | `r_channel_stego.py` | n < 256 (about 8 bits) | Manual note, the scanner cannot read it |

**Caveat:** `risk_report.md` lists the 512-bit and 1024-bit rows as real sizes. They are defaults, so the figures for these rows (1027 and 2051 qubits) describe unused defaults, not the sizes in actual use.

### Two kinds of risk

- **Quantum risk:** every RSA key here falls to Shor's algorithm, whatever its size.
- **Classical risk:** a 256-bit modulus can be factored on an ordinary computer today, without any quantum computer.

## 4. Stage 2: Quantum mapping

`quantum_mapper.py` maps each primitive to the algorithm that threatens it. This is a theoretical mapping: it says which attack applies, not that the attack is practical today.

| Primitive | Quantum algorithm | Impact | PQC replacement |
|---|---|---|---|
| RSA | Shor's | Broken | ML-KEM (encryption, key exchange), ML-DSA (signatures) |
| ECC | Shor's | Broken | ML-KEM (ECDH), ML-DSA (ECDSA, EdDSA) |
| DSA | Shor's | Broken | ML-DSA |
| DH | Shor's | Broken | ML-KEM |
| AES | Grover's | Weakened | Keep AES, use 256-bit keys |
| SHA | Grover's | Weakened | Keep SHA-2 or SHA-3 with 256-bit or larger output |

**Applied to our findings:** RSA (25 findings) maps to Shor's and is broken. SHA-256 (1 finding) maps to Grover's and keeps about 128 bits of security.

**Status:** the final mapping report is built from the real `findings.json` (26 findings, 2 projects) and saved as `mapping_report.md`. `mapping_report_draft.md` is kept only as the early dummy-data draft.

## 5. Stage 3 summary (details in `risk_report.md`)

Shor's algorithm needs about 2n + 3 logical qubits for an n-bit modulus:

| Modulus (bits) | Logical qubits | Source |
|---|---|---|
| 256 | 515 | Part1, real use |
| 512 | 1027 | Part1, default value |
| 1024 | 2051 | Steganography, default value |

All counts are **logical** qubits. A real attack would need far more physical qubits for error correction.

Padding and indirect usage (edge-case module): 2 no-padding flags in each project (textbook RSA without OAEP or PKCS1), and 6 (Part1) and 4 (Steganography) indirect-usage flags, where crypto is defined in one file and called from another.

## 6. Limitations

- Detection is static and regex-based: it can miss dynamically built code and can over-match comments and strings (low-confidence findings are labelled).
- Key sizes chosen at runtime (UI input, config files) are reported as unknown.
- `bits=N` is assumed to be the per-prime size, based on the docstring in `rsa_utils.py`.
- ECC, DSA, DH and AES patterns were verified on test fixtures only, because the target projects contain just RSA and SHA.

## 7. Pending

- Risk report: mark default-value sizes separately.
- CBOM and the classical key-strength check (not found in the repository at the time of writing).
