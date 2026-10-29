# Q14: published resource estimates for factoring RSA-2048 (estimates, not measurements)

Checked on: <date>. Primary source needed for every row before it is quoted in the report.

| Source | Logical qubits | Toffoli gates | Physical qubits | Runtime | Assumptions | Verified? |
|---|---|---|---|---|---|---|
| Beauregard 2n+3 (our F2 formula) | 4,099 for n = 2048 | VERIFY | n/a | n/a | textbook circuit, no error correction | formula only |
| Gidney and Ekera (arXiv 2019; journal year VERIFY) | VERIFY | VERIFY | 20 million | 8 hours | square grid, 0.1% gate error, 1 us cycle, 10 us reaction | abstract of 2025 paper |
| Gidney, arXiv 2505.15917 (21 May 2025) | VERIFY | VERIFY | under 1 million | under 1 week | same assumptions as 2019 | abstract checked |
| Newer architecture claims (2026) | VERIFY | VERIFY | VERIFY | VERIFY | VERIFY | secondary source only, unverified |
| Our Q4 measured circuits | measured, n = 4 to 8 | n/a | n/a | n/a | Aer simulator, toy size | after Q4 |

## Notes
- All rows are published estimates under stated hardware assumptions. None is a measurement of ours.
- This table feeds F2 and the Z = 5, 10, 20 scenarios. It says nothing about when such a machine will exist.
- Optional: run Qualtran or the Azure Quantum Resource Estimator and add the result as a row.
