# Before and After: Image Project (L1 message encryption)

Weights v0.1, same engine for both rows (`src/before_after.py`).
Inputs: X = 5, Y = 2, Z = 10 years. Weighted score, not a probability.
Formulas and weights only; no quantum simulation is involved.

| RSA modulus | Setup | Quantum % | Classical % | Overall % | Band |
|---|---|---|---|---|---|
| 256 bits | Before: textbook RSA, no padding | 86.6 | 100.0 | 91.9 | Critical |
| 256 bits | After: ML-KEM-768 + AES-256-GCM | 4.5 | 5.0 | 4.7 | Low |
| 512 bits | Before: textbook RSA, no padding | 84.1 | 100.0 | 90.4 | Critical |
| 512 bits | After: ML-KEM-768 + AES-256-GCM | 4.5 | 5.0 | 4.7 | Low |

Size used in the report: 256 bits (the size in use: `generate_keypair(bits=128)` in app.py and main.py; 512 bits is only an unused default in rsa_utils.py). Basis: docs/size_decisions.md.

## Z scenarios (overall %, before to after)

| Z (years) | 256 bits | 512 bits |
|---|---|---|
| 5 | 96.4 to 5.0 | 94.9 to 5.0 |
| 10 | 91.9 to 4.7 | 90.4 to 4.7 |
| 20 | 86.7 to 4.3 | 85.2 to 4.3 |

## Robustness to the weights

In 1,000 narrow and 1,000 wide random weight draws (seed 42), the "after" score
was below the "before" score every time. The "after" score stayed between 3.5
and 5.0. The drop is large because F1 falls from 100 to 5; any sensible weights
give the same ordering.

## Why the "after" score is not zero

| Factor | Value | Reason |
|---|---|---|
| F1 quantum exposure | 5.0 | NIST PQC level is scored 5, not 0 |
| F4 construction | 5.0 | AES-GCM is scored just above zero by design |
| F5_eff data lifetime | 3.5 | F5 = 70, gated by F1 (5 percent) |
| F6_eff exposure | 5.0 | ciphertext is still extractable, gated by F4 |

F2 and F3 do not apply to ML-KEM. The model measures algorithm choice and
construction. It does not measure implementation risk (the prototype uses
educational, non-hardened libraries), so a low score does not mean production
safety.

## What is not in this table

- The hiding layer (LSB) is unchanged and is measured by steganalysis.
- Layers with no cryptography are not scored (open team decision).
- The optional ML-DSA-65 signature (L5) is scored in Week 3.
- The video project is scored in Week 3.