# Risk Model (v0.1)

Status: weights v0.1, frozen in Week 1 Day 5. Changed only if the sensitivity
study shows an unstable ranking; each change is documented here.

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
| F1 Quantum exposure | Shor-broken public-key = 100. Grover-weakened symmetric or hash: effective bits >= 128 = 10, 112 to 127 = 30, below 112 = 60. NIST PQC (ML-KEM, ML-DSA, SLH-DSA) with AES-256 = 5 |
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