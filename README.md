# AI-Powered PQC Migration Advisor: Quantum-Vulnerability Testing Pipeline

Final-year B.Tech CSE project, Hindustan College of Science and Technology, Mathura (AKTU).

The pipeline scans a codebase for classical cryptography, works out which quantum algorithm threatens each finding, estimates the logical-qubit cost, and produces a Cryptographic Bill of Materials (CBOM) with a post-quantum migration recommendation for every component. It was run on two target projects: `Final-Year-project-part1` and `Secure-Video-Steganography`.

## Team

| Member | Role |
|---|---|
| Tarun Saxena | Detection engine lead and repository owner |
| Vaibhav Gautam | Edge-case and vulnerability detection |
| Uday Pratap Singh | Migration advisor and reporting |
| Yatharth Raghuvanshi | Risk scoring and ML (qubit estimates, Shor's demo) |

## How it works

```
scanner -> findings.json -> edge-case flags merged in
                          -> quantum_mapper (Shor's / Grover's, PQC replacement)
                          -> qubit estimates (Shor 2n+3, logical qubits)
                          -> cbom (JSON + Markdown)
                          -> final_dashboard.md
```

| Stage | What it does |
|---|---|
| Scanner | Finds RSA, ECC, AES and SHA usage and key sizes (`findings.json`) |
| Edge cases | Flags missing padding (textbook RSA) and indirect crypto usage |
| Mapper | Maps asymmetric crypto to Shor's algorithm and symmetric/hash to Grover's |
| CBOM | One entry per component with separate quantum, classical and padding risk |
| Dashboard | Summary, Detection, Mapping, Risk, Demo, Conclusion, all generated from data |
| Shor's demo | Order-finding circuit on a Qiskit simulator at toy sizes (N = 15 and 21) |

## Run it

Requirements: Python 3.10+, `pip install -r requirements.txt` (the mapper, CBOM and dashboard use only the standard library).

```bash
# 1. Map findings to quantum algorithms and write the mapping report
python src/quantum_mapper.py outputs/findings.json outputs/mapped_findings.json docs/mapping_report.md --overrides data/manual_facts.json

# 2. Build the CBOM (JSON + Markdown) and verify the outputs agree
python src/cbom.py outputs/findings.json --facts data/manual_facts.json --json docs/cbom.json --md docs/cbom.md --check

# 3. Build the final dashboard
python src/build_dashboard.py outputs/findings.json --facts data/manual_facts.json --demo data/demo_results.json --out docs/final_dashboard.md

# 4. Run all tests
python -m unittest discover -s tests -v
```

The scanner, edge-case module and Shor's demo have their own usage notes at the top of their source files.

## Results

See `docs/final_dashboard.md` (all numbers are generated from the data), `docs/cbom.md` / `docs/cbom.json`, and `docs/mapping_report.md`.

## Be honest about what this shows

- All quantum work runs on a **simulator at toy sizes**. It is not evidence that RSA-1024 or RSA-2048 can be broken today.
- Qubit counts are **logical-qubit estimates** (2n+3 circuit) without error-correction overhead. Published physical-qubit estimates for RSA-2048 are far larger.
- Grover's algorithm is a **quadratic speed-up, not a full break**.
- Padding and small-key weaknesses are **classical problems**, reported separately from the quantum score. Textbook RSA is dangerous because it is deterministic, not because of Shor's algorithm.
- Key sizes the scanner cannot see come from manual review (`data/manual_facts.json`). Unverified sizes are labelled as such.

## Repository layout

```
src/        scanner, edge cases, quantum_mapper, qubit estimator, cbom, build_dashboard, Shor's demo
tests/      unit tests (python -m unittest discover -s tests)
data/       manual facts, demo results template
docs/       mapping report, CBOM, dashboard, schema, weekly summaries
schemas/    JSON Schema for the CBOM
```

Development log: `docs/week2_summary.md`, `docs/week3_summary.md`.

## References

- Shor, P. W. (1997). Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer. SIAM J. Comput. 26(5).
- Grover, L. K. (1996). A fast quantum mechanical algorithm for database search. STOC.
- Beauregard, S. (2003). Circuit for Shor's algorithm using 2n+3 qubits. Quantum Information & Computation 3(2).
- Gidney, C. and Ekera, M. (2021). How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits. Quantum 5, 433.
- NIST FIPS 203 (ML-KEM) and FIPS 204 (ML-DSA), 2024.
