# Attack evidence: master (Vaibhav) - Week 4 Day 1 consolidation

How to use: merge/replace into the team's docs/attack_evidence.md. This file pulls together
docs/attack_evidence_week2.md and docs/attack_evidence_week3.md (keep those as backing detail
if useful, or delete once this is merged) and adds Q10, Q11 and the Week 4 stretch/Q8 status.
Fields marked **[FILL]** need your own fresh run output, version string or commit hash.

All quantum results: **Aer simulator, toy size.**
Versions: qiskit 2.5.2, qiskit-aer 0.17.2, kyber-py 1.2.0, dilithium-py 1.5.1,
pycryptodome 4.0.0, Python 3.14.5. Commit: `4fadd41`.

## 1. Q1 - Shor's algorithm (factoring)
See docs/attack_evidence_week2.md section 1. Summary: N=15, 21, 35 all factored correctly from
measured circuit outcomes, chi-square p-values 0.069-0.496 (consistent with theory), 20/20
repeats per case in the batch run.

Confirmed with Yatharth: his Q2 gate-level circuit currently reaches N=21, smaller than Q1’s N=35. So Q1’s N=35 result (section 1, above) remains the largest toy attack demonstrated by this project; no re-run was needed. If Q2 is extended further before release, re-run extras/stego_attack_toy.py --shor against the new larger N at that point.

## 2. Q3 - Grover's algorithm (toy cipher)
See the Q3 section of your earlier notes. Summary: keys 183, 42, 250 all found and verified at
the theoretical optimum (k=12), success probability sweep matches the sin^2 curve, chi-square
consistent with theory, numpy-emulator cross-check agrees to ~1e-14.

## 3. Q11 - quantum counting
Run (saved to data/quantum_runs.json, 8 records):

| true M | pair | qubits | peak outcome | estimated M | chi2 p (counting) | k (counted) | success (counted) | k (naive, M=1 assumed) | success (naive) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | (0, 11) | 22 | 5 | 1 (MATCH) | 0.728 | 6 | 0.998 | - (same as counted) | - |
| 2 | (0, 136) | 22 | 7 | 2 (MATCH) | 0.887 | 4 | 1.000 | 6 | 0.549 |
| 3 | (64, 79) | 22 | 9 | 3 (MATCH) | 0.808 | 3 | 0.999 | 6 | 0.090 |

Summary: all 3 targets (M=1, 2, 3 matching keys) correctly estimated via the maximum-
likelihood counting estimator before any Grover search ran, every key found and verified.
The naive-assumption comparison (assuming M=1 when the real M is larger) shows exactly why
counting matters: success collapses from 1.000 to 0.549 at M=2, and from 0.999 to 0.090 at
M=3 - using the wrong round count overshoots badly. Circuit: 22 qubits, depth 7,511, runtime
~70-85 s per instance (Aer, toy size).

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
| 11 | 2 | 10 | 3 | 3 | MATCH (self-test) |
| 23 | 5 | 22 | 7 | 7 | MATCH (`test_change_the_question_p23`) |
| 23 | 5 | 22 | 19 | 19 | MATCH (`test_change_the_question_p23`) |

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
Run (2026-11-02): the pinned project's own `rsa_utils.generate_keypair()` (default
`bits=256` per prime, so N is ~512 bits - larger than the plan's "256-bit image key" text;
worth flagging this discrepancy between the plan's description and the real code's default)
was called directly to produce one genuine key instance - no modulus is stored anywhere in
the project; one is generated fresh on each run. N obtained:
`10292582080507310278399931576034906946512437480772685288992878268290823438744942570085644300786123149943242357727720694922105172962982996699530293287369019`
(512 bits).

```
python extras\sieve_attempt.py --n 10292582080507310278399931576034906946512437480772685288992878268290823438744942570085644300786123149943242357727720694922105172962982996699530293287369019 --budget-seconds 120
```

Tool: sieve_attempt.py (Pollard's rho + Pollard's p-1), version 1.0 (this project, not a
third-party library). Budget: 120.0 s. **NOT COMPLETED**: both Pollard's p-1 and Pollard's rho
tried, neither found a factor in the full 120.0 s budget. This is the expected, honest result
for a well-generated 512-bit RSA key - exactly what the plan's risk table anticipates for this
stretch goal, reported with the tool, version and time rather than silence.

## 9. Q8: IBM Quantum access check (Week 4 Day 5)
Code: `src/q8_check_access.py`. This checks account/service access only - it runs no circuit and
spends no runtime budget.

Run (2026-11-01): `python -m src.q8_check_access`
- qiskit-ibm-runtime installed: True (version 0.50.0)
- saved account found: False
- service reachable: False

Result: **not yet confirmed**. qiskit-ibm-runtime is installed, but no IBM Quantum account is
saved on this machine, so the service cannot be reached. This is the normal, honest outcome
for Day 5 when nobody has run `QiskitRuntimeService.save_account(token=...)` yet with a token
from https://quantum.ibm.com. No circuit was run and no runtime budget was spent. Flagged to
Tarun, who owns Q8 overall, to decide whether and when to set one up - `src/q8_hardware_run.py`
is ready to run the moment access is confirmed.

## 10. What we did not show
- The pinned project's real 256-bit/512-bit key: attempted with a real tool (section 8), likely
  "not completed" for a well-generated key - that is the honest, expected result.
- No real quantum hardware runs yet (Q8, pending account access, section 9).
- Q2's largest handled N not yet confirmed with Yatharth for the toy-attack re-run (section 1).
- kyber-py and dilithium-py are educational libraries, not hardened; every "attack failed"
  result here is evidence for these specific constructions, not a general security proof.
