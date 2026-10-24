# Chapter: Risk score

## 1. Purpose and scope
Sir asked for a system that takes a project and reports how vulnerable it is to quantum attacks as a percentage.
One score for any project is not realistic, so the risk system covers our two projects only: the image steganography
project (final-year-part1, pinned at bb6d944) and the video steganography project (Secure-Video-Steganography, pinned at 4514806).
[FILL: date and wording of what sir agreed about the scope.]

The percentage is a transparent weighted score from 0 to 100. It is not the probability that someone attacks us.
Every factor, weight and threshold is written down in data/risk_weights.json and tested for stability.

## 2. Layers scored
| Layer | Image project | Video project |
|---|---|---|
| L1 Message encryption | RSA, textbook | RSA, textbook |
| L2 Frame-selection key | none (keyless embedding) | SHA-256 of a passphrase |
| L3 Integrity | none | CRC32 (not cryptographic; works as a key-check oracle) |
| L5 Signature | none | none |
The hiding layer (LSB, XOR-LSB) is measured by steganalysis and is not part of the quantum percentage.

## 3. Factors
Six factors, each 0 to 100, higher means riskier: F1 quantum exposure, F2 qubit cost, F3 classical key weakness,
F4 construction weakness, F5 data lifetime (harvest now, decrypt later), F6 exposure.
F5 is gated by F1 (the lifetime test only matters for quantum-vulnerable algorithms).
F6 is gated by the layer's weakness (showing a ciphertext is only a risk when the encryption can be attacked).
[FILL: one sentence per factor on how it was scored, copied from docs/risk_model.md.]

## 4. Formulas
- Quantum % = 0.50 x F1 + 0.25 x F2 + 0.25 x F5_eff
- Classical weakness % = 0.40 x F3 + 0.30 x F4 + 0.30 x F6_eff
- Overall % = 0.60 x Quantum + 0.40 x Classical
- Project score = 0.7 x (worst layer) + 0.3 x (average of layers)
- Bands: below 25 Low, 25 to 49 Moderate, 50 to 74 High, 75 and above Critical
Weights version: [FILL: frozen version from docs/risk_model.md].

## 5. Assumptions that drive the answer
F5 depends on three numbers nobody can measure: X (years the message must stay secret), Y (years to migrate),
Z (years until a large quantum computer exists). Agreed values: [FILL: X, Y, Z and the date agreed with sir].
The score is shown as a range over Z = 5, 10, 20, never as a single number.

## 6. Worked reference values
| Case | Quantum % | Classical % | Overall % |
|---|---|---|---|
| RSA-512 without padding | 84.1 | 100.0 | 90.4 |
| RSA-1024 without padding | 81.6 | 80.0 | 80.9 |
| RSA-2048 with OAEP | 79.1 | 8.5 | 50.8 |
| ML-KEM-768 + AES-256-GCM | 4.5 | 5.0 | 4.7 |
These are defined by the model (X = 5, Y = 2, Z = 10) and reproduced by the code. They are not measurements of our projects.
RSA-2048 with OAEP still scores High because Shor's algorithm breaks it: padding fixes classical weaknesses only.

## 7. Results for our projects
[FILL: table from outputs/risk_scores.json: per layer quantum %, classical %, overall %, band, sensitivity range, Z = 5, 10, 20.]

## 8. Validation
[FILL: results from docs/risk_validation.md: reference order, monotonic tests, sensitivity (weights changed by 20 percent and
random draws, ranking stable or not), consistency with the attacks we really ran.]

## 9. Limits
- The weights are our choice and are not fitted to data. There is no ground truth for a probability.
- The F5 inputs are assumptions agreed with sir; the sensitivity study shows how far the answer moves.
- Quantum results elsewhere in this project are simulator, toy size. Resource figures for real sizes are published estimates.