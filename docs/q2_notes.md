# Q2 Notes: gate-level Shor (Aer simulator, toy size)

Versions: qiskit <version>, qiskit-aer <version> (from the run record).
Seeds: simulator 12345, transpiler 12345.

## One controlled-multiplication iteration (a = 2)

| N | Qubits (2n+3) | Gates before / after transpile | Run seconds | Estimated seconds per shot (ESTIMATE) |
|---|---|---|---|---|
| 15 | 11 | <fill> | <fill> | <fill> |
| 21 | 13 | <fill> | <fill> | <fill> |
| 35 | 15 | <fill> | <fill> | <fill> |

The estimate is 2n iterations times the one-iteration run time. It is an
estimate, not a measurement.

## Full runs

| N | a | Shots | Run seconds | Factors | Success rate |
|---|---|---|---|---|---|
| 15 | 7 | <fill> | <fill> | <fill> | <fill> |
| 21 | 2 | <fill> | <fill> | <fill> | <fill> |

The success rate is higher than in the Phase 1 demo because this
post-processing also tries multiples of the guessed period (standard Shor).

## Rule status after today

| Rule | Status |
|---|---|
| 1, 2 Real gates, result from measurement | met |
| 3 No classical shortcut | met in the builders; second reviewer to confirm |
| 7, 11 Labels | met in the run record |
| 9 Truth tables | met for every Q2 building block; second-simulator cross-check pending |
| 10 Seeds and versions | recorded in each run record |
| 4 Evidence in data/quantum_runs.json | pending: schema to agree with Tarun |
| 5 Chi-square | pending |
| 6 Change-the-question comparison | circuit builds for other (a, N); measured comparison pending |
| 8 Static guard | simple name scan only; Tarun's guard pending |