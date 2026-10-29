# Risk Model (v1.0)

Status: weights v1.0 (v0.1 was frozen in Week 1 Day 5). Changed only if the
sensitivity study shows an unstable ranking or a layer cannot be scored; each
change is documented in the change log at the end of this file.

## What the percentage is

A transparent weighted score from 0 to 100. It is **not** the probability that
someone attacks us. Every factor, weight and threshold is written down and can
be changed in one file, `data/risk_weights.json`. All quantum results behind it
are Aer simulator, toy size.

## Layers scored

| Layer | Image project | Video project |
|---|---|---|
| L1 Message encryption | textbook RSA | textbook RSA (default 1024-bit; UI offers 1024, 2048, 3072) |
| L2 Frame-selection key | none (keyless embedding) | SHA-256 of a passphrase |
| L3 Integrity | none | CRC32 (not cryptographic; works as a key-check oracle) |
| L5 Signature | none | none |

The hiding layer (LSB, XOR-LSB) is measured by steganalysis and is not part of
the quantum percentage.

## Factors (each 0 to 100, higher is riskier)

| Factor | How it is scored |
|---|---|
| F1 Quantum exposure | Shor-broken public-key = 100. Grover-weakened symmetric or hash: effective bits >= 128 = 10, 112 to 127 = 30, below 112 = 60. NIST PQC (ML-KEM, ML-DSA, SLH-DSA) with AES-256 = 5. No quantum-vulnerable algorithm in the layer (`none`, for example CRC32) = 0 |
| F2 Qubit cost | q = 2n+3. Score = 100 x (1 - (log10(q) - 2) / 3), limited to 20 to 100. Shor-broken layers only |
| F3 Classical key weakness | Modulus up to 512 bits = 100, below 1024 = 80, below 2048 = 50, 2048 or more = 10. Uses the size in use; default-only sizes are flagged |
| F4 Construction weakness | No padding and deterministic = 100. Deterministic framing or key-check oracle = 80. Padding without AEAD = 40. AES-GCM or OAEP = 0 to 10 |
| F5 Data lifetime (Mosca) | 100 x (X + Y) / Z, limited to 100. **Gated:** F5_eff = F5 x F1 / 100 |
| F6 Exposure | Keyless = 100. Keyed but bypassable (video header scan) = 90. Keyed and not bypassable = 30. **Gated:** F6_eff = F6 x max(F3, F4) / 100; if F3 does not apply, use F4 alone |

F5 and F6 are gated because they only matter when the layer can be attacked.
A factor that does not apply to a layer (for example F2 for SHA-256) is left
out, and the other weights in its group are re-scaled.

## Formulas

| Quantity | Formula |
|---|---|
| Quantum Risk % | 0.50 x F1 + 0.25 x F2 + 0.25 x F5_eff |
| Classical Weakness % | 0.40 x F3 + 0.30 x F4 + 0.30 x F6_eff |
| Overall Risk % | 0.60 x Quantum + 0.40 x Classical |
| Project score | 0.7 x (worst layer) + 0.3 x (average of layers) |

## Bands

Below 25 Low, 25 to 49 Moderate, 50 to 74 High, 75 and above Critical.

## Assumptions (to be agreed with sir)

X = 5 years (test 2 and 10), Y = 2 years, Z = 10 years (scenarios 5 and 20).
Exposure: the stego file is public. Attacker: has the stego file and public
key, no secret. Until agreed, the score is shown as a range over Z = 5, 10, 20.

## Worked reference values

Assumptions: X = 5, Y = 2, Z = 10; F4 = 5 for OAEP and AES-GCM; F6 = 100;
F3 does not apply to ML-KEM. The code must reproduce these within rounding.

| Case | Quantum % | Classical % | Overall % |
|---|---|---|---|
| RSA-512 without padding | 84.1 | 100.0 | 90.4 |
| RSA-1024 without padding | 81.6 | 80.0 | 80.9 |
| RSA-2048 with OAEP | 79.1 | 8.5 | 50.8 |
| ML-KEM-768 + AES-256-GCM | 4.5 | 5.0 | 4.7 |

RSA-2048 with OAEP is still High because Shor's breaks it; padding only fixes
classical weaknesses.

## Trust checks

- Reference order: RSA-512 > RSA-1024 > RSA-2048+OAEP > ML-KEM-768+AES-GCM.
- Monotonic: a bigger key or added padding never raises the score.
- Sensitivity: weights changed by 20 percent plus random draws; report score
  range and whether the ranking stays the same.
- Consistency: layers we actually broke must score higher than layers we did not.
- Before and after: re-score the PQC prototypes with the same engine.

## Limits

The weights are our choice and are not fitted to data. There is no ground truth
for a probability.


## Physical qubits (estimates)

The model's qubit factor F2 uses logical qubits, q = 2n + 3. Physical-qubit
figures are shown beside it for context and are **estimates, not measurements**.
The 1,000:1 ratio is an assumption for illustration. The only published figure
used is Gidney and Ekera (2021) for RSA-2048 under their stated assumptions
(`data/published_estimates.json`, marked unverified until checked against the
paper). Their logical-qubit formula describes a different circuit from 2n + 3,
so the two are never mixed. F2 does not use physical qubits.

## Change log

| Version | Date | Change | Why |
|---|---|---|---|
| v0.1 | Week 1 Day 5 | First frozen weights | |
| v1.0 | 2026-10-22 | Added F1 category `none` = 0 (no quantum-vulnerable algorithm in the layer) | The video integrity layer (L3, CRC32) could not be scored. Existing weights are unchanged; image scores are unchanged. Video L3 now scores 30.4 (Moderate, quantum 0, classical 76); the video project score moves from 66.4 to 64.1. CRC32 is not cryptography, so Shor and Grover have nothing to break; its weakness is classical (key-check oracle). |


## Signature layer (L5) and the migrated layers

How each primitive is described to the engine (`src/layer_presets.py`). A
"provisional" F4 category is the closest existing one, not an exact match.

| Primitive | F1 category | F4 construction | Provisional |
|---|---|---|---|
| Textbook RSA | shor_broken | no_padding_deterministic | no |
| RSA with OAEP | shor_broken | oaep | no |
| RSA signature (PSS) | shor_broken | oaep | yes |
| ML-KEM-768 + AES-256-GCM | nist_pqc | aead | no |
| ML-DSA-65, SLH-DSA | nist_pqc | aead | yes |
| SHA-256 of a passphrase (video L2 today) | symmetric, 128 effective bits | deterministic_or_oracle | no |
| Random 256-bit key with HMAC-SHA256 (video L2 after v2) | symmetric, 128 effective bits | aead | yes |
| CRC32 (video L3 today) | none | deterministic_or_oracle | no |

Signature options for L5 (image exposure keyless, X = 5, Y = 2, Z = 10):

| Option | Overall % | Band |
|---|---|---|
| None | not scored | "no protection" |
| RSA-2048 with PSS | 50.8 | High |
| ML-DSA-65 | 4.7 | Low |
| SLH-DSA | 4.7 | Low |

Rules:
- A layer with no cryptography, including a missing signature, is not scored and
  is listed as "no protection".
- After migration the integrity layer is the AES-GCM tag inside L1; the CRC32
  layer disappears and no separate L3 is scored.
- Exposure (F6) is the project's own. A signature is public by design, and F6 is
  gated by F4, so keyless against bypassable moves a signature layer by about
  0.6 points.

Project scores (weakest-link rule):

| Project | Before | Migrated, unsigned | Migrated, signed |
|---|---|---|---|
| Image | 91.9 | 4.7 | 4.7 |
| Video | 64.1 | 6.9 | 6.8 |

Limits specific to signatures:
- F5 (Mosca) is defined for secrecy. For a signature, X would mean the years the
  signature must stay trustworthy; this is not parameterised separately. With
  ML-DSA, F1 = 5 limits F5_eff to 3.5 points.
- The model scores risk, not protection. Adding a signature layer does not
  lower any layer's score and authenticity is not credited. It lowers the
  project score only through the average (0.13 points for the video project).
- The F4 categories for ML-DSA, SLH-DSA, the RSA signature and the v2 frame key
  are provisional until the team agrees on one.