# Q14: published resource estimates for factoring RSA-2048 (estimates, not measurements)

Checked on: <date>. Every row needs a primary source (arXiv or journal) before it is quoted.

| Source | Logical qubits | Toffoli gates | Physical qubits | Runtime | Assumptions | Verified? |
|---|---|---|---|---|---|---|
| Beauregard 2n+3 (our formula, F2) | 4,099 | n/a | n/a | n/a | textbook circuit, no error correction | VERIFY |
| Gidney and Ekera (arXiv 2019, journal year VERIFY) | about 3n | 3 billion | 20 million | 8 hours | grid, 0.1% error, 1 us cycle, 10 us reaction | VERIFY |
| Gidney, arXiv 2505.15917 (May 2025) | about 0.5n | 2 trillion | under 1 million | under 1 week | same as above | VERIFY |
| Iceberg Quantum (Feb 2026, secondary source only) | VERIFY | VERIFY | under 100,000 | VERIFY | different architecture | VERIFY |
| Our Q4 measured circuits (Yatharth) | measured, n = 4 to 8 | n/a | n/a | n/a | Aer simulator, toy size | after Q4 |

## Notes
- All rows are published estimates under stated hardware assumptions. None is a measurement of ours.
- This table feeds F2 and the Z = 5, 10, 20 scenarios. It says nothing about when such a machine will exist.
- Optional: run Qualtran or the Azure Quantum Resource Estimator and add the result as a row.
