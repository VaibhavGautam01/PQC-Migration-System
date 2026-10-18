# Risk Model Review, Week 1 Day 4

Reviewer: Yatharth Raghuvanshi. Model version: weights v0.1.
Method: `python src/risk_review.py` (checks) and a row-by-row comparison with
`outputs/risk_scores.json`. Quantum numbers are logical-qubit formulas; no
simulator result is used here.

## Checks run

| Check | Result |
|---|---|
| Worked values (84.1 / 81.6 / 79.1 / 4.5 quantum; 100.0 / 80.0 / 8.5 / 5.0 classical; 90.4 / 80.9 / 50.8 / 4.7 overall) | pass |
| Reference order RSA-512 > RSA-1024 > RSA-2048+OAEP > ML-KEM+AES-GCM | pass |
| Bigger key never raises the score | pass |
| Added padding never raises the score | pass |
| Bigger Z never raises the quantum risk | pass |
| F5 gating (NIST PQC level: F5_eff = 5 percent of F5) | pass |
| F6 gating (follows max(F3, F4); F4 alone when F3 does not apply) | pass |

## Z scenarios (X = 5, Y = 2), overall %

| Case | Z = 5 | Z = 10 | Z = 20 |
|---|---|---|---|
| RSA-512 no padding | 94.9 | 90.4 | 85.2 |
| RSA-1024 no padding | 85.4 | 80.9 | 75.7 |
| RSA-2048 OAEP | 55.3 | 50.8 | 45.6 |
| ML-KEM-768 + AES-256-GCM | 5.0 | 4.7 | 4.3 |

RSA-2048 with OAEP changes band with Z (High at Z = 5 and 10, Moderate at
Z = 20), so the dashboard must show the range and not one number.

## Comparison with Tarun's first scores

| Project / layer | Input used | Model value | Tarun's value | Match |
|---|---|---|---|---|
| <fill from outputs/risk_scores.json> | | | | |

Commit of the scores file reviewed: <fill>

## Findings and open questions

1. **SHA-256 frame-selection key (video L2).** It scores Moderate (35.8) with
   F4 = `deterministic_or_oracle`. The real weakness is a guessable passphrase,
   which the model does not measure. Decide, with Tarun, whether to keep this
   F4 choice and say so in the report.
2. **Layers with no cryptography** (image L2, L3, L5; video L5). The model has
   no category for them, and the project score uses the average of layers.
   Proposal: leave absent layers out of the average and list them as "no
   protection". Needs a team decision before Week 2 Day 1.
3. **Textbook RSA stays Critical for every Z tested.** RSA-1024 is 75.7 even at
   Z = 20. This is consistent with Shor's breaking RSA at any size.
4. **Video vs image at 1024 bits.** The video layer scores slightly lower (79.7
   vs 80.9) because its exposure is keyed. Expected.
5. <add any row where Tarun's value did not match, with the cause>

## Changes to the model

None. Weights v0.1 are unchanged. Any change is proposed here first, and made
only if the Week 2 sensitivity study shows an unstable ranking.