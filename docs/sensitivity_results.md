# Sensitivity Results (weights v0.1)

Script: `src/sensitivity.py`, seed 42, 1,000 draws per random run.
Weights fingerprint: see `data/risk_weights.lock.json`.
Scope: the four reference cases only. Image vs video and before vs after need
the layer map and are added when it exists. Weighted score, not a probability.

## Baseline (X = 5, Y = 2, Z = 10)

| Case | Overall % |
|---|---|
| RSA-512 no padding | 90.4 |
| RSA-1024 no padding | 80.9 |
| RSA-2048 OAEP | 50.8 |
| ML-KEM-768 + AES-256-GCM | 4.7 |

## Ranges

| Case | Narrow random (x0.8 to x1.2): min to max | Wide random (Dirichlet): min to max |
|---|---|---|
| RSA-512 no padding | 87.5 to 92.9 | 69.6 to 100.0 |
| RSA-1024 no padding | 78.0 to 84.0 | 55.6 to 98.8 |
| RSA-2048 OAEP | 43.6 to 58.2 | 7.2 to 95.9 |
| ML-KEM-768 + AES-256-GCM | 4.6 to 4.8 | 3.5 to 5.0 |

## Ranking stability

- Reference order RSA-512 > RSA-1024 > RSA-2048+OAEP > ML-KEM holds in 100.0
  percent of narrow draws, 100.0 percent of wide draws, and in all 20
  one-at-a-time cases.
- Decision rule (at least 95 percent of narrow draws and every one-at-a-time
  case): met. **No weight change. v0.1 stays.**
- Largest single-weight effects: overall quantum weight x0.8 (3.8 points),
  overall classical weight x0.8 (3.7), overall classical weight x1.2 (3.1).

## What the result does not show

- This ordering follows from the inputs: a bigger key or added padding lowers
  every factor, so any positive weights keep the order. A stable ordering here
  is expected and is weak evidence on its own. The meaningful tests are image
  vs video and before vs after at project level.
- The **band is not stable**. RSA-2048 with OAEP is High in 590 and Moderate in
  410 of the 1,000 narrow draws; under the wide draws it ranges from Low to
  Critical. The absolute percentage depends on the weights. The dashboard
  shows a range, not one number.

## Assumption grid (overall %, v0.1 weights)

| X | Z | RSA-512 | RSA-1024 | RSA-2048 OAEP | ML-KEM |
|---|---|---|---|---|---|
| 2 | 5 | 91.9 | 82.4 | 52.3 (High) | 4.8 |
| 2 | 10 | 85.9 | 76.4 | 46.3 (Moderate) | 4.4 |
| 2 | 20 | 82.9 | 73.4 (High) | 43.3 (Moderate) | 4.2 |
| 5 | 5 | 94.9 | 85.4 | 55.3 (High) | 5.0 |
| 5 | 10 | 90.4 | 80.9 | 50.8 (High) | 4.7 |
| 5 | 20 | 85.2 | 75.7 | 45.6 (Moderate) | 4.3 |
| 10 | 5 | 94.9 | 85.4 | 55.3 (High) | 5.0 |
| 10 | 10 | 94.9 | 85.4 | 55.3 (High) | 5.0 |
| 10 | 20 | 88.9 | 79.4 | 49.3 (Moderate) | 4.6 |

Unmarked cells are Critical (RSA-512, RSA-1024) or Low (ML-KEM). At X = 10 and
Z of 5 or 10 the lifetime factor F5 is capped at 100.

## Limits

The weights are our choice and are not fitted to data. X, Y and Z are
assumptions to be agreed with sir. Nothing here validates the absolute
percentage.