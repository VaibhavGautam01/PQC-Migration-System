# Chapter: Risk score

## 1. Purpose and scope
Sir asked for a system that takes a project and reports how vulnerable it is to quantum attacks as a percentage.
One score for any project is not realistic, so the risk system covers our two projects only: the image steganography
project (final-year-part1, pinned at bb6d944) and the video steganography project (Secure-Video-Steganography, pinned at 4514806).
Sir agreed to limit the new risk system to our two projects (Plan v3, Section 1). The assumptions for F5 were agreed with him on 2026-10-17, and the six-week schedule and the analyzer flow on 2026-10-22. His confirmation of the analyzer scope line is still open (see the scope paragraph).

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
- F1 quantum exposure: 100 for Shor-broken public-key algorithms (RSA, ECC, DSA, DH); 5 for NIST post-quantum algorithms with AES-256; for symmetric and hash layers 10, 30 or 60 by the effective bits left after Grover (128 or more, 112 to 127, below 112).
- F2 qubit cost: q = 2n + 3 logical qubits, score = 100 x (1 - (log10(q) - 2) / 3), limited to 20 to 100; it applies only to Shor-broken layers.
- F3 classical key weakness: modulus up to 512 bits = 100, 513 to 1,023 = 80, 1,024 to 2,047 = 50, 2,048 and above = 10; it does not apply to ML-KEM.
- F4 construction weakness: no padding and deterministic = 100, deterministic framing or a key-check oracle = 80, padding without AEAD = 40, AES-GCM or OAEP about 5 (the plan allows 0 to 10).
- F5 data lifetime (harvest now, decrypt later): Mosca test 100 x (X + Y) / Z, limited to 100, then gated: F5_eff = F5 x F1 / 100.
- F6 exposure: keyless = 100, keyed but bypassable (the video header scan) = 90, keyed and not bypassable = 30, then gated: F6_eff = F6 x max(F3, F4) / 100 (F4 alone when F3 does not apply).

## 4. Formulas
- Quantum % = 0.50 x F1 + 0.25 x F2 + 0.25 x F5_eff
- Classical weakness % = 0.40 x F3 + 0.30 x F4 + 0.30 x F6_eff
- Overall % = 0.60 x Quantum + 0.40 x Classical
- Project score = 0.7 x (worst layer) + 0.3 x (average of layers)
- Bands: below 25 Low, 25 to 49 Moderate, 50 to 74 High, 75 and above Critical
Weights version: v1.0 (data/risk_weights.json).

## 5. Assumptions that drive the answer
F5 depends on three numbers nobody can measure: X (years the message must stay secret), Y (years to migrate),
Z (years until a large quantum computer exists). Agreed values: X = 5 years (scenarios 2, 5 and 10), Y = 2 years, Z = 10 years as the central value (scenarios 5, 10 and 20), agreed with sir on 2026-10-17 (data/manual_facts.json).
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
| Project | Layer | Quantum % | Classical % | Overall % | Band | Overall range, Z = 5 to 20 |
|---|---|---|---|---|---|---|
| image | L1 | 86.6 | 100.0 | 91.9 | Critical | 86.7 to 96.4 |
| image | L1, R-channel module, generate_small_keypair() | 92.5 | 100.0 | 95.5 | Critical | n/a |
| **image project** | weakest-link rule | | | 91.9 | Critical | 86.7 to 96.4 |
| video | L1 | 79.1 | 61.0 | 71.8 | High | 66.6 to 76.3 |
| video | L1, UI option / function default | 81.6 | 77.0 | 79.7 | Critical | n/a |
| **video project** | weakest-link rule | | | 64.1 | High | 59.8 to 67.7 |

image: no protection, so not scored: L2, L3, L5. video: no protection, so not scored: L5.
The score is a transparent weighted score, not a probability. Scores come from outputs/risk_scores.json.

## 8. Validation
[FILL: results from docs/risk_validation.md: reference order, monotonic tests, sensitivity (weights changed by 20 percent and
random draws, ranking stable or not), consistency with the attacks we really ran.]

## 9. Limits
- The weights are our choice and are not fitted to data. There is no ground truth for a probability.
- The F5 inputs are assumptions agreed with sir; the sensitivity study shows how far the answer moves.
- Quantum results elsewhere in this project are simulator, toy size. Resource figures for real sizes are published estimates.