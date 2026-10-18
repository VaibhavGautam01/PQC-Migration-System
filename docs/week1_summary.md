# Week 1 Summary: Repository Setup & Detection Engine Core

**Owner:** Tarun Saxena (Detection Engine Lead) | **Branch:** `tarun/detection-engine`
**Sprint goal:** a general-purpose crypto detection engine (not only RSA), tested on both target repos.

## What was completed

| Day | Commit | Work done | Issue |
|---|---|---|---|
| Mon | `82b0a7d` | Repo structure, `.gitignore`, `requirements.txt`, README skeleton, first RSA signature patterns | #1 |
| Tue | `170da57`, `ac3cb4a` | Textbook-RSA patterns (prime helpers, modular inverse, `pow` / `(c ** d) % n`, `65537`); first scan of both target repos | #2 |
| Wed | `44bc2a7` | ECC, DSA, DH, AES and SHA patterns in `src/extra_patterns.py` | #2 |
| Thu | `7807c1e` | Key-size extraction in `src/key_size.py`: variable and default resolution, per-prime vs modulus size, wrapper calls | #2 |
| Fri | `9d54f73` | `src/run_all.py` merges both scans into `outputs/findings.json` v1 | #2, #4 |

## Scanner status (v0.4.0)

- 46 detection patterns across RSA, ECC, DSA, DH, AES and SHA.
- Every finding records: project, file, line, primitive, pattern_id, confidence, key_size, modulus_bits, size_basis, snippet.
- Verified on 4 test fixtures in `tests/fixtures/` (46 findings in total).

## Results on the target repos (findings.json v1)

| Project | Findings | Primitives |
|---|---|---|
| Secure-Video-Steganography | 9 | RSA 8, SHA 1 |
| Final-Year-project-part1 | 15 | RSA 15 |

Note: part1 later went from 15 to 17 findings after the Week 2 cross-check added the `RSA-MANUAL-PRIME-ISPRIME` pattern.
## Manual notes (the scanner cannot determine these)

1. part1 real use: `generate_keypair(bits=128)` gives a 256-bit modulus. The 256/512 in `rsa_utils.py` is only a default value.
2. part1 `r_channel_stego.py`: modulus `n < 256`, at most 8 bits.
3. steganography: key size is chosen in the UI (1024 / 2048 / 3072, default 2048).
4. `bits=N` is assumed to be the per-prime size (modulus = 2 x N), based on the `rsa_utils.py` docstring.

## Known gaps (planned for Week 2)

- Cross-check every finding against the source code line by line (false positives and misses).
- Indirect usage (crypto imported in one file, used in another) is handled by Vaibhav's edge-case module.
- Unit tests for `scanner.py` and a one-command test runner.
- Remove the unused `extract_key_size()` from `scanner.py` in the final cleanup.






# Week 1 Summary: Yatharth Raghuvanshi (Risk Model and Quantum Lead)

## Done

| Day | Work | Files |
|---|---|---|
| 1 | Risk model specification; audit of the Shor demo against rules 1 to 11 | `docs/risk_model.md`, `docs/shor_audit.md` |
| 2 | Factors F1 to F6 as pure functions; weights file; Q2 QFT adder and modular adder | `src/risk_score.py`, `data/risk_weights.json`, `src/q2_arith.py`, tests |
| 3 | Formulas, bands, weakest-link score; modular subtractor (Q2 adder block finished) | `src/risk_score.py`, `tests/test_risk_formulas.py`, `src/q2_arith.py` |
| 4 | Review of the model and first scores | `src/risk_review.py`, `docs/risk_review_week1.md` |
| 5 | Weights v0.1 frozen; sensitivity plan; this summary | `src/weights_lock.py`, `docs/sensitivity_plan.md` |

## Test status

Run: `python -m unittest discover -s tests`. Result: <n> tests, <OK or failures>,
<n> skipped (the slow N = 15 and 21 adder test, run with `SLOW_TESTS=1`:
<passed / not run>).

## Results

- The code reproduces all 12 worked values in plan section 4 (quantum,
  classical and overall for the four reference cases) within rounding.
- Reference order and monotonic checks pass. F5 and F6 gating checks pass.
- Q2 adders pass truth-table tests (rule 9) on all inputs for N = 3, 5, 7,
  and N = 15, 21 in the slow test. Aer simulator, toy size.

## Open items

- Shor audit (rules 4, 5, 8, 9, 10 failed; rules 3, 6, 11 partial): to be
  fixed in Q1 (Vaibhav) and Q2 (Yatharth), tracked in the Q1 and Q2 issues.
- Comparison with Tarun's `outputs/risk_scores.json`: <done / pending>.
- Layers with no cryptography in the project average: team decision needed.
- F4 choice for the SHA-256 frame-selection key: team decision needed.
- Sensitivity study: script and results in Week 2 Day 1.

## Next week

Sensitivity script and results, then Q2 multiplier and exponentiation, Shor
at gate level for N = 15 and 21, and the "after" score for the image project.