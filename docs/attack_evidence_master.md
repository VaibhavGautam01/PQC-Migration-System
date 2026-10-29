# Attack evidence: master (Vaibhav) - Week 4 Day 1 consolidation

How to use: merge/replace into the team's docs/attack_evidence.md. This file pulls together
docs/attack_evidence_week2.md and docs/attack_evidence_week3.md (keep those as backing detail
if useful, or delete once this is merged) and adds Q10, Q11 and the Week 4 stretch/Q8 status.
Fields marked **[FILL]** need your own fresh run output, version string or commit hash.

All quantum results: **Aer simulator, toy size.**
Versions: qiskit **[FILL]**, qiskit-aer **[FILL]**, kyber-py **[FILL]**, dilithium-py **[FILL]**,
pycryptodome **[FILL]**, Python **[FILL]**. Commit: **[FILL: `git rev-parse --short HEAD`]**.

## 1. Q1 - Shor's algorithm (factoring)
See docs/attack_evidence_week2.md section 1. Summary: N=15, 21, 35 all factored correctly from
measured circuit outcomes, chi-square p-values 0.069-0.496 (consistent with theory), 20/20
repeats per case in the batch run.

**[FILL]**: largest N your Q1 circuit (or, if merged, Yatharth's Q2 gate-level circuit) reaches -
confirm with Yatharth and re-run `extras/stego_attack_toy.py --shor` against that N (Week 4 Day
1's "largest N that Q1 or Q2 handles" task).

## 2. Q3 - Grover's algorithm (toy cipher)
See the Q3 section of your earlier notes. Summary: keys 183, 42, 250 all found and verified at
the theoretical optimum (k=12), success probability sweep matches the sin^2 curve, chi-square
consistent with theory, numpy-emulator cross-check agrees to ~1e-14.

## 3. Q11 - quantum counting
M=1, 2, 3 matching keys all correctly estimated via the maximum-likelihood estimator before any
Grover search ran; numpy-emulator cross-check agrees with the analytic theory to ~1e-14.
**[FILL]**: paste your real `python -m src.q11_run --save` output here.

## 4. Q10 - Shor's algorithm (discrete log) - NEW this week
Code: `src/q10_dlog.py`, `src/q10_run.py`, `src/dlog_post.py`. Reuses Q1's order-finding circuit
(stage 1) and Q1's controlled-modmul/inverse-QFT building blocks (stage 2, a new two-register
phase-estimation circuit).

A real bug was found and fixed during testing: an incorrect assumption about how measured
register values are ordered in the circuit's output caused x to go unrecovered (or, in one
early version, to silently recover a wrong value) for some instances. The fix was verified
against real measured Aer data, not just reasoning: 5 of 5 non-degenerate outcomes from a real
p=23 run correctly recovered the secret x once the bit-ordering was corrected, versus 0 of 5
under every other ordering hypothesis tested. See `tests/test_q10_dlog.py`'s
`RealMeasuredDataRegressionTest`, which pins this down permanently using the real captured data.

| p | g | order r | secret x | recovered x | result |
|---|---|---|---|---|---|
| 11 | 2 | 10 | 3 | **[FILL]** | **[FILL]** |
| 23 | 5 | 22 | 7 | **[FILL]** | **[FILL]** |
| 23 | 5 | 22 | 19 | **[FILL]** | **[FILL]** |

Honest limits: the controlled modular-multiplication gates are dense matrices (same limit as
Q1), so this does not scale past small toy primes (p <= ~31 keeps qubits under ~20). A small-
order self-test (like p=11, r=10) is weak evidence on its own - roughly a 1-in-10 chance a wrong
implementation accidentally passes by luck, which is exactly what happened during development.
The p=23 instances (r=22) are the ones that give genuine confidence.

## 5. Image attack and steganalysis (Week 2)
See docs/attack_evidence_week2.md in full. Summary: 12/12 checks pass (reference and pinned
embedder), real cover images (lena_stego.png, bellpepper_stego_image.png), PQC payload smaller
than RSA's for messages over ~9 characters.

## 6. Video attack and steganalysis (Week 3)
See docs/attack_evidence_week3.md in full. Summary: 12/12 checks pass against the REAL
`pqc_stego/video_pqc.py` and `pqc_stego/signing.py` (not a stand-in), including the
wrong-signer-key check. Signed and plain PQC payloads are statistically indistinguishable from
each other in the LSB plane; the signature adds only its size overhead (~3,309 B), not a new
detectability signature.

## 7. Breaking our own work (Week 4 Day 3)
Code: `extras/break_own_work.py`. Nonce reuse: the classic two-time-pad leak confirmed as a real
attack CLASS, but `hybrid_encrypt()` itself never reuses a nonce (2000/2000 distinct,
os.urandom every call) - not applicable to the real code. Score gaming: mislabelling a layer's
category or exposure can swing F1/F6 by 70-95 points with zero change to the real crypto (the
model trusts given labels, it does not re-derive them from raw code); `risk_weights.json` has
no integrity check. All three findings belong in the report's "Risks and honest limits" section.

## 8. Stretch: sieve attempt on the real pinned key (Week 4 Day 2)
Code: `extras/sieve_attempt.py` (Pollard's rho + Pollard's p-1, NOT a general number field
sieve - see the file's own docstring for why that scope is appropriate for a stretch goal).

Self-test (small composites, confirms the tool works): PASS - 91, 3,233 and 363,413 all
factored correctly in well under a second.

Real attempt against the pinned key:
**[FILL: run `python extras\sieve_attempt.py --n <the real modulus>` (get the real modulus
from wherever the pinned project stores its key) and paste the result - tool, version, time,
and whether it completed. For a well-generated 256-bit key, "not completed" after the time
budget is the expected, honest result and is fine to report exactly that way, per the plan's
own rule for this stretch goal.]**

## 9. Q8: IBM Quantum access check (Week 4 Day 5)
Code: `src/q8_check_access.py`. This checks account/service access only - it runs no circuit and
spends no runtime budget.

**[FILL: run `python -m src.q8_check_access` and paste the result.]** If no account is
configured yet, that is a normal "not yet confirmed" result for this step, not a failure -
flag it to Tarun, who owns Q8 overall, to decide whether and how to set one up.

## 10. What we did not show
- The pinned project's real 256-bit/512-bit key: attempted with a real tool (section 8), likely
  "not completed" for a well-generated key - that is the honest, expected result.
- No real quantum hardware runs yet (Q8, pending account access, section 9).
- Q2's largest handled N not yet confirmed with Yatharth for the toy-attack re-run (section 1).
- kyber-py and dilithium-py are educational libraries, not hardened; every "attack failed"
  result here is evidence for these specific constructions, not a general security proof.
