# AI-Powered PQC Migration Advisor — Quantum-Vulnerability Testing Pipeline

Final-year B.Tech CSE project · Hindustan College of Science and Technology, Mathura (AKTU)

## Overview
A pipeline that scans codebases for quantum-vulnerable cryptography, maps each
primitive to the quantum algorithm that breaks it (Shor's / Grover's), estimates
the qubit cost, and recommends a post-quantum migration path (ML-KEM-768).

## Pipeline Stages
1. **Detection** — `src/scanner.py`, `src/edge_cases.py`
2. **Quantum mapping** — `src/quantum_mapper.py`
3. **Risk scoring & qubit-cost** — `src/qubit_estimator.py`, risk report, CBOM
4. **Demo** — Shor's algorithm on Qiskit simulator (N = 15, 21)

## Team
| Member | Role |
|---|---|
| Tarun Saxena | Detection Engine Lead & Repository Owner |
| Vaibhav Gautam | Edge-Case & Vulnerability Detection Specialist |
| Uday Pratap Singh | Migration Advisor & Reporting Engineer |
| Yatharth Raghuvanshi | Risk Scoring & ML Engineer |

## Setup
```bash
python -m venv venv
venv\Scripts\activate          # Windows (Linux/macOS: source venv/bin/activate)
pip install -r requirements.txt
```

## Usage
```bash
python src/scanner.py <path-to-target-repo> --out outputs/findings.json
```

## Commit Convention
`type: short description (fixes #N)` — types: feat / fix / docs / refactor / test / chore

## Progress
Tracked on the GitHub Kanban board and Issues. Weekly summaries will be added here.
