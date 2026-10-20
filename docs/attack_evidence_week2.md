# Attack evidence: Week 2 (Vaibhav)

How to use this file: the numbers marked **[FILL]** must be pasted from your own run output.
Do not invent numbers. If an attack_evidence.md already exists on main, move these sections into it
and delete this file. Every result names the version it was measured on (plan, working rule).

All quantum results: **Aer simulator, toy size.** Software versions: qiskit **[FILL: `pip show qiskit`]**,
qiskit-aer **[FILL: `pip show qiskit-aer`]**, Python **[FILL: `python --version`]**, kyber-py **[FILL]**,
pycryptodome **[FILL]**. Commit: **[FILL: `git rev-parse --short HEAD`]**.

## 1. Q1 Shor phase estimation (circuit built from gates, run on Aer)

Code: `src/q1_shor_pe.py`, `src/q1_run.py`, `src/shor_post.py`. Evidence records: `data/quantum_runs.json`.
Seeds: seed_simulator = seed_transpiler = 12345. Shots: 4096 per run.

| N | a | qubits | period found (from measured counts) | factors | chi-square p vs theory | exact cross-check |
|---|---|---|---|---|---|---|
| 15 | 7 | 12 | 4 | 3 x 5 | 0.069 | agree (max diff 6e-16) |
| 15 | 2 | 12 | 4 | 3 x 5 | 0.069 | agree (max diff 6e-16) |
| 21 | 2 | 15 | 6 | 3 x 7 | 0.217 | agree (max diff 1e-14) |
| 35 | 2 | 18 | 12 | 5 x 7 | 0.496 | agree (max diff 2e-14) |

Repeated runs (Day 2): `data/demo_results.json`, made by `python -m src.q1_demo_batch --save`.
Repeats finding the factors per case: **[FILL from the script output]**.

What this shows: the phase-estimation circuit finds the period of a^x mod N from measured outcomes only, and
the measured histogram is consistent with theory. Changing N and a changes the answer with no code change.

What this does NOT show: the controlled-U blocks are dense matrices built from pow(a, 2^j, N). The circuit is
correct but does not scale, so its gate counts are not resource estimates (Q4 uses the Q2 circuits).

## 2. Shor circuit connected to the toy stego attack

Code: `extras/stego_attack_toy.py --shor`. Attacker input: the public modulus N only.
Results: N=15 **[FILL: base a, measured period, BREAK SUCCESSFUL?]**, N=21 **[FILL]**, N=35 **[FILL]**.
Measured on: local toy key, not the pinned project's key size.

## 3. Attack on the PQC image variant

Code: `extras/attack_pqc_image.py`. Embedder used: **[FILL: reference-lsb (test stand-in) or pinned lsb_stego.py + commit]**.
Attacker has the stego image and the public key only.

| Check | Result |
|---|---|
| Extract the blob without any secret | works (keyless LSB), 1116 + message bytes **[FILL]** |
| RSA break (factor N) | not applicable: ML-KEM-768 public key is 1184 raw bytes, no modulus (by construction, not measured) |
| Plaintext visible in blob | no |
| Decrypt with a wrong secret key | fails (HybridDecryptError) |
| Flip 1 payload bit: header, KEM ciphertext, nonce, tag, AES part | decryption fails every time **[FILL: n of n]** |
| Flip 1 bit outside the payload | message still correct |

Conclusion: the encryption layer no longer gives the attacker anything to factor or forge. Extraction still works, so the
hiding layer is unchanged and is not a quantum weakness.

## 4. Steganalysis: RSA payload vs PQC payload

Code: `extras/steganalysis_pqc.py`. Cover: **[FILL: photo name and size; synthetic covers are demonstration only]**.
Embedder: **[FILL]**. Table: paste `outputs/steganalysis_pqc_image.md` here.

Facts computed from the formulas (check them against the table):
- textbook RSA-1024 hides 128 bytes per message character; the PQC blob adds a fixed 1120 bytes (4-byte header + 1116);
- the PQC raw payload is smaller than the RSA payload for messages longer than about 9 characters.

Findings: **[FILL: write what the table shows, e.g. whether the PQC payload moves the ones fraction or the
chi-square p-value further from the clean cover than the RSA payload. Report it honestly if the larger payload is
easier to detect, and say for which message lengths.]**

## 5. What we did not show

- No attack on the pinned project's real 256-bit or 512-bit image key (needs a sieve tool; stretch goal, not done unless listed above).
- No hardware run: every quantum result is a simulator result.
- The PQC libraries are educational (kyber-py is not hardened against timing attacks); a failed attack here is evidence for this
  construction, not a proof that ML-KEM is secure.
- The video PQC variant is not attacked yet (it depends on the video prototype).
- Steganalysis used simple detectors, not state-of-the-art ones. "Not flagged" does not mean undetectable.
