## Week 2 Summary: Mapper on real data (Uday)

**Goal:** connect `quantum_mapper.py` to the real `findings.json` and make the mapping report trustworthy.

**Delivered**

- The mapper now reads the real findings, validates them (`--strict`), and prefers `modulus_bits` over the scanner's `key_size`, because the scanner can report the prime size instead of the modulus size.
- Manual facts the scanner cannot see live in `data/manual_facts.json`. An override changes a size only when it is marked `confirmed`, so nothing disputed changes results silently.
- `docs/mapping_report.md` is generated from the real findings and ends with a **Data caveats** section that lists every size warning and unconfirmed override.
- Tests: synthetic ECC findings prove the mapper works beyond RSA; the real-data contract tests check `findings.json` against the agreed schema.
- Documentation: `docs/quantum_mapper.md` (mapping table, fields, commands, limits).

**Open questions (need a team decision before the CBOM is final)**

1. Modulus size for `Final-Year-project-part1`: the findings review says 256 bits (and under 256 as a number, at most 8 bits, in `r_channel_stego.py`); the attack work reports a 31-bit modulus. These need to be reconciled and the overrides confirmed.
2. Default key size of `Secure-Video-Steganography`: 1024 or 2048 bits.

**Resolved in Week 3:** see `docs/week3_summary.md` and `docs/size_decisions.md` (part1: 256 bits in use and at most 8 bits in the R-channel module; video: UI default 2048). The 31-bit figure comes from a local small-key copy, not the project of record.

**Limits:** the mapping is theoretical (which attack applies, not that it is practical today). Padding and small-key weaknesses are reported separately from the quantum score. All quantum work runs on a simulator at toy sizes.



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

`python -m unittest discover -s tests`: <n> tests, <OK / failures>, <n> skipped.
Slow tests (`SLOW_TESTS=1`): <passed / not run>.

## Results

- Sensitivity: the reference order held in 100 percent of narrow and wide
  draws and in all one-at-a-time cases. No weight change was needed. Bands are
  not stable (RSA-2048 with OAEP: High or Moderate depending on weights).
- Before and after, image project (X = 5, Y = 2, Z = 10): textbook RSA 91.9
  (256-bit) or 90.4 (512-bit), Critical; ML-KEM-768 + AES-256-GCM 4.7, Low.
  The "after" score was below "before" in every weight draw.
- Q2: gate-level Shor uses 2n + 3 qubits (11 for N = 15, 13 for N = 21, 15 for
  N = 35). Aer simulator, toy size. N = 15 phase outcomes: <fill from run>;
  N = 21: <fill>. One-iteration time for N = 35: <fill> seconds (estimate per
  shot: <fill>, an ESTIMATE).
- Hybrid review: <number of FAIL / WARN items>, findings sent to Uday:
  <summary or "pending: hybrid.py not yet merged">.

## Open items

- Layers with no cryptography in the project average: team decision.
- F4 choice for the SHA-256 frame-selection key: team decision.
- Evidence records in `data/quantum_runs.json`: schema to agree with Tarun;
  chi-square against theory (rule 5) and the change-the-question comparison
  (rule 6) still to do.
- Static guard (rule 8): only a simple name scan so far; Tarun's guard pending.
- Gidney and Ekera figures: unverified until checked against the paper.
- X, Y, Z: <agreed / not yet agreed with sir>.
- Image vs video ranking: needs the layer map.

## Next week

Video project scoring and the signed variant, frame-selection fix, Q3 and Q4
support, and parameter-set comparison for ML-KEM and ML-DSA.