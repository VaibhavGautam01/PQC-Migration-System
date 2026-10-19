# Limitations of the Risk Model (weights v1.0)

The percentage is a transparent weighted score from 0 to 100. It is not the
probability that anyone attacks us. All quantum results behind the project are
Aer simulator, toy size.

## 1. What the score cannot be

| Limit | What it means | How we handle it |
|---|---|---|
| Weights are our choice | Not fitted to data; no ground truth exists for a probability | Sensitivity study; weights in one frozen file; every change documented |
| Ranking test is weak on its own | For the reference cases, a bigger key or added padding lowers every factor, so any positive weights keep the order | We report it as expected, and test project-level rankings separately |
| Bands are not stable | RSA-2048 with OAEP is High in 590 and Moderate in 410 of 1,000 narrow weight draws; under wide draws it spans Low to Critical | The dashboard shows a range, not one number |
| Absolute percentage depends on weights | Different sensible weights move the same case by several points (wide draws: tens of points) | Quote the range with the percentage |

## 2. Assumptions we cannot measure

| Input | Value used | Status |
|---|---|---|
| X, years the message must stay secret | 5 (also 2 and 10) | <agreed with sir on date / not yet agreed> |
| Y, years to migrate | 2 | <same> |
| Z, years until a large quantum computer | 10 (also 5 and 20) | Nobody knows; shown as scenarios, never one number |
| Exposure | stego file is public | <same> |

F5 is the largest driver of the quantum percentage and depends on these.

## 3. Modelling simplifications

- **F1 is five coarse buckets.** RSA, ECC, DSA and DH all score 100. There is no
  separate qubit-cost formula for ECC, DSA or DH; F2 uses 2n + 3 and applies to
  RSA moduli only.
- **F2 uses a logical-qubit formula, not the best published estimate.**
  Physical-qubit figures are shown beside it as estimates (Gidney and Ekera,
  2021, marked unverified until checked against the paper) and are not used in
  the score.
- **F3 and F4 are judgement bands.** The F3 bands are copied from
  `key_strength_check.py`; they are rounded thresholds, not security-level
  equivalences. F4 values are discrete categories.
- **The SHA-256 frame-selection key is scored as a deterministic construction.**
  The real weakness is a guessable passphrase, which the model does not measure.
- **Layers with no cryptography are not scored** (image L2, L3, L5; video L5).
  How they enter the project average is an open team decision. The weakest-link
  rule lets one weak layer dominate the project score.
- **The hiding layer (LSB) is outside the quantum percentage.** A low score after
  migration says nothing about steganalysis resistance, which is measured
  separately.

## 4. What the score does not see

- **Implementation risk.** The prototype uses educational, non-hardened
  libraries (kyber-py, dilithium-py). Timing channels, nonce misuse and memory
  handling are not scored. A low "after" score means a safe algorithm choice and
  construction, not production safety.
- **Scanner errors.** Inputs come from `findings.json`. Missed or mislabelled
  findings change the score. Precision and recall are measured only on the
  hand-checked findings. Default-only key sizes are flagged, not scored as in
  use.
- **Residual floor.** The best case, ML-KEM-768 + AES-256-GCM, scores 4.7, not 0:
  F1 = 5, F4 = 5, F5_eff = 3.5 and F6_eff = 5 by design.

## 5. Scope

- Built and checked for two projects only (image and video steganography). It
  is not a general scorer for any project, and the deck's Java, JavaScript and
  LLM items are outside this model.
- No calibration against other projects or incident data.
- Quantum Lab results are toy sizes on a simulator. Real-size claims rest on
  published estimates, labelled as estimates.