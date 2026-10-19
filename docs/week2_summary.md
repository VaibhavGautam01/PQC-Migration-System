# Week 2 Summary: Yatharth Raghuvanshi (Risk Model and Quantum Lead)

## Done

| Day | Work | Files |
|---|---|---|
| 1 | Sensitivity script (one at a time, narrow and wide random draws, assumption grid); Q2 controlled modular multiplier and exponentiation with truth-table tests | `src/sensitivity.py`, `src/q2_arith.py`, tests |
| 2 | Sensitivity results; labelled physical-qubit estimates; gate-level Shor with iterative phase estimation (N = 15, 21; N = 35 timing) | `docs/sensitivity_results.md`, `src/physical_estimates.py`, `src/q2_shor.py`, `src/q2_shor_run.py` |
| 3 | "After" configuration scored with the same engine; before/after table for the image project | `src/before_after.py`, `docs/before_after_image.md` |
| 4 | Security review of the hybrid module: tool, checklist and findings | `src/hybrid_review.py`, `docs/hybrid_security_review.md` |
| 5 | Weights v1.0 frozen (values unchanged); limitations; this summary | `data/risk_weights.json`, `docs/model_limitations.md` |

## Test status

`python -m unittest discover -s tests`: 595 tests, OK, 9 skipped (Python 3.14, local run, commit 0df8e9b).
Slow tests (`SLOW_TESTS=1`): not run for this summary.

## Results

- Sensitivity: the reference order held in 100 percent of narrow and wide
  draws and in all one-at-a-time cases. No weight change was needed. Bands are
  not stable (RSA-2048 with OAEP: High or Moderate depending on weights).
- Before and after, image project (X = 5, Y = 2, Z = 10): textbook RSA 91.9
  (256-bit) or 90.4 (512-bit), Critical; ML-KEM-768 + AES-256-GCM 4.7, Low.
  The "after" score was below "before" in every weight draw.
- Q2: gate-level Shor uses 2n + 3 qubits (11 for N = 15, 13 for N = 21, 15 for
  N = 35). Aer simulator, toy size. N = 15 (a = 7, 200 shots, seed 12345) phase outcomes y = 0, 64, 128, 192 (of 256), factors 3 x 5 in 70 percent of shots;
  N = 21 (a = 2, 200 shots) y = 0, 171, 341, 512, 683, 853 (of 1024), factors 3 x 7 in 82 percent of shots. One-iteration time for N = 35: 0.561 s (15 qubits, transpile 51.3 s; Aer simulator, toy size) (estimate per
  shot: about 6.7 s, an ESTIMATE: 12 iterations x one-iteration time). Chi-square, change-the-question and diagram file for Q2 are still pending.
- Hybrid review (`python src/hybrid_review.py`): 0 FAIL items (D1 to D11 and static check all PASS), findings sent to Uday:
  none needed; kyber-py is educational and not hardened, production route is liboqs-python.

## Open items

- Layers with no cryptography in the project average: team decision.
- F4 choice for the SHA-256 frame-selection key: team decision.
- Evidence records in `data/quantum_runs.json`: schema to agree with Tarun;
  chi-square against theory (rule 5) and the change-the-question comparison
  (rule 6) still to do.
- Static guard (rule 8): only a simple name scan so far; Tarun's guard pending.
- Gidney and Ekera figures: unverified until checked against the paper.
- X, Y, Z: agreed with sir on 2026-10-17 (stored in data/manual_facts.json).
- Image vs video ranking: needs the layer map.

## Next week

Video project scoring and the signed variant, frame-selection fix, Q3 and Q4
support, and parameter-set comparison for ML-KEM and ML-DSA.
