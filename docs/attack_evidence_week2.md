# Attack evidence: Week 2 (Vaibhav)

How to use this file: numbers marked **[FILL]** must be pasted from your own run output. Do not invent numbers.
If an attack_evidence.md already exists on main, move these sections into it and delete this file.
Every result names the version it was measured on.

All quantum results: **Aer simulator, toy size.**
Versions: qiskit 2.5.2, qiskit-aer 0.17.2, Python 3.14.5, kyber-py 1.2.0, pycryptodome 4.0.0.
Pinned image project: `final-year-part1` at commit `bb6d944`.
Code commit for sections 1 to 4: `eb1a442` (last change to the scripts; branch `vaibhav/week2-attacks`).

## 1. Q1 Shor phase estimation (circuit built from gates, run on Aer)

Code: `src/q1_shor_pe.py`, `src/q1_run.py`, `src/shor_post.py`. Evidence records: `data/quantum_runs.json`.
Seeds: seed_simulator = seed_transpiler = 12345. Shots: 4096 per run.

| N | a | qubits | period found (from measured counts) | factors | chi-square p vs theory | exact cross-check |
|---|---|---|---|---|---|---|
| 15 | 7 | 12 | 4 | 3 x 5 | 0.069 | agree (max diff 6e-16) |
| 15 | 2 | 12 | 4 | 3 x 5 | 0.069 | agree (max diff 6e-16) |
| 21 | 2 | 15 | 6 | 3 x 7 | 0.217 | agree (max diff 1e-14) |
| 35 | 2 | 18 | 12 | 5 x 7 | 0.496 | agree (max diff 2e-14) |

Repeated runs (`python -m src.q1_demo_batch --save`; details in `data/q1_batch_results.json`, summary line per N
merged into `data/demo_results.json`). 20 repeats x 2048 shots per case, seeds 12345 to 12364:

| N | a | repeats that found the factors | period in every repeat | mean per-shot success | pooled chi-square p |
|---|---|---|---|---|---|
| 15 | 7 | 20 / 20 | 4 | 75% | 0.319 |
| 15 | 2 | 20 / 20 | 4 | 75% | 0.319 |
| 21 | 2 | 20 / 20 | 6 | 82% | 0.670 |
| 35 | 2 | 20 / 20 | 12 | 90% | 0.779 |

(The two N=15 rows are identical because the ideal distribution depends only on the period, 4 for both bases, and the
seeds are the same.)

What this shows: the phase-estimation circuit finds the period of a^x mod N from measured outcomes only, the factors
follow in every repeat, and the pooled histograms are consistent with theory. Changing N and a changes the answer with
no code change.

What this does NOT show: the controlled-U blocks are dense matrices built from pow(a, 2^j, N). The circuit is correct
but does not scale, so its gate counts are not resource estimates (Q4 uses the Q2 circuits).

## 2. Shor circuit connected to the toy stego attack

Code: `extras/stego_attack_toy.py --shor`. Attacker input: the public modulus N only.
Results (pinned project's `embed_lsb` / `extract_lsb`, message "HELLO", 10 ciphertext blocks extracted each time):

| N | toy key e | base a | measured period r | factors | recovered d | result |
|---|---|---|---|---|---|---|
| 15 | 3 | 2 | 4 | 3 x 5 | 3 | BREAK SUCCESSFUL, HELLO decrypted |
| 21 | 5 | 2 | 6 | 3 x 7 | 5 | BREAK SUCCESSFUL, HELLO decrypted |
| 35 | 5 | 2 | 12 | 5 x 7 | 5 | BREAK SUCCESSFUL, HELLO decrypted |

Each break needed 1 attempt (the first base worked). The factoring step is the Q1 circuit on the Aer simulator; the
attacker gives it only the public N. Measured on: local toy keys (N=15, 21, 35), not the pinned project's real 256-bit or
512-bit keys.

## 3. Attack on the PQC image variant

Code: `extras/attack_pqc_image.py`. The attacker has the stego image and the public key only.
Covers: `stego_images/lena_stego.png` (512x512) and `stego_images/bellpepper_stego_image.png` (320x320).
Message: "HELLO" (5 bytes); hidden blob 1,121 bytes.

Embedder (a): reference LSB (a stand-in, not the pinned project's code). Result: **12 of 12 checks passed on both images.**

| Check | Result |
|---|---|
| Extract the blob without any secret | works (keyless LSB), 1,121 bytes |
| RSA break (factor N) | not applicable: ML-KEM-768 public key is 1,184 raw bytes, no modulus. This is "by construction", not a measured attack |
| Plaintext visible in blob | no |
| Decrypt with a wrong secret key | fails (HybridDecryptError) |
| Decrypt with the right secret key | HELLO |
| Flip 1 bit in the length header | fails (ImageCapacityError: the container's own length check, before any decryption) |
| Flip 1 bit in KEM ciphertext (first byte, middle), nonce, GCM tag, AES part | decryption fails every time (HybridDecryptError), 5 of 5 |
| Flip 1 bit outside the payload | message still correct |

Embedder (b): the pinned project's own `lsb_stego.py` (commit `bb6d944`) embed/extract on `lena_stego.png`. Its wire format
is a 32-bit length header followed by the blob as hex text. Result: **12 of 12 checks passed.**
Every tampered copy was rejected. Latest run (`outputs/attack_pqc_image_pinned.json`):
- flip in the 32-bit length header: rejected while parsing, before decryption (ValueError, non-hexadecimal text in the
  extracted string);
- flips in the KEM ciphertext (2 positions), the nonce, the GCM tag and the AES ciphertext: all rejected by the AES-GCM
  authentication check (HybridDecryptError, "authentication failed"), 5 of 5.
An earlier run of the same script (new random key and blob each run) rejected three of the payload flips with a plain
ValueError instead. The likely reason, not separately verified: the pinned format stores the blob as hex text, flipping
the lowest bit of a hex character's code can turn 'a' or 'f' into a non-hex character, and the parser then rejects it
before decryption. Either way the result is a loud failure and never a wrong plaintext; the script prints which layer
rejected each flip. The reference-embedder run (a) shows the GCM tag catching KEM, nonce, tag and AES-part flips.

Conclusion: the encryption layer no longer gives the attacker anything to factor or forge, and a flipped payload bit
is rejected. Extraction still works, so the hiding layer is unchanged; its weakness is not a quantum weakness.

## 4. Steganalysis: RSA payload vs PQC payload

Code: `extras/steganalysis_pqc.py`. Covers: lena_stego.png and bellpepper_stego_image.png. Both clean-cover rows show no hex
header and no length header. RSA = textbook RSA-1024, one 128-byte block per message character.

Lena, reference embedder (capacity 98,304 B):

| msg chars | payload | bytes | cap used | ones whole | ones region | chi p region | flagged (p>0.5) | hex header | length header |
|---|---|---|---|---|---|---|---|---|---|
| - | clean cover | - | 0.0% | 0.4939 | 0.4819 | 0.0 | False | False | False |
| 5 | RSA hex | 1280 | 1.3% | 0.4936 | 0.4379 | 0.0 | False | True | False |
| 5 | PQC hex | 2242 | 2.3% | 0.4933 | 0.4368 | 0.0 | False | True | False |
| 5 | PQC raw | 1125 | 1.1% | 0.4944 | 0.5004 | 1.0 | True | False | True |
| 40 | RSA hex | 10240 | 10.4% | 0.4913 | 0.4391 | 0.0 | False | True | False |
| 40 | PQC hex | 2312 | 2.4% | 0.4933 | 0.4372 | 0.0 | False | True | False |
| 40 | PQC raw | 1160 | 1.2% | 0.4944 | 0.4999 | 1.0 | True | False | True |
| 200 | RSA hex | 51200 | 52.1% | 0.4719 | 0.4394 | 0.0 | False | True | False |
| 200 | PQC hex | 2632 | 2.7% | 0.4933 | 0.4395 | 0.0 | False | True | False |
| 200 | PQC raw | 1320 | 1.3% | 0.4944 | 0.5011 | 0.9996 | True | False | True |

Bell pepper, reference embedder (capacity 38,400 B; the 200-character RSA payload does not fit, so lengths 5 and 40):

| msg chars | payload | bytes | cap used | ones whole | ones region | chi p region | flagged (p>0.5) | hex header | length header |
|---|---|---|---|---|---|---|---|---|---|
| - | clean cover | - | 0.0% | 0.4926 | 0.495 | 0.0 | False | False | False |
| 5 | RSA hex | 1280 | 3.3% | 0.4906 | 0.435 | 0.0056 | False | True | False |
| 5 | PQC hex | 2242 | 5.8% | 0.4891 | 0.4413 | 0.0002 | False | True | False |
| 5 | PQC raw | 1125 | 2.9% | 0.4931 | 0.5092 | 1.0 | True | False | True |
| 40 | RSA hex | 10240 | 26.7% | 0.477 | 0.4364 | 0.0 | False | True | False |
| 40 | PQC hex | 2312 | 6.0% | 0.4886 | 0.4361 | 0.0 | False | True | False |
| 40 | PQC raw | 1160 | 3.0% | 0.4927 | 0.4984 | 1.0 | True | False | True |

Lena, pinned embedder (`lsb_stego.py` at `bb6d944` for the hex rows; the PQC raw rows still use the reference embedder).
The pinned format starts with a 32-bit length header, so the hex scan skips 32 bits:

| msg chars | payload | bytes | cap used | ones whole | ones region | chi p region | flagged (p>0.5) | hex header | length header |
|---|---|---|---|---|---|---|---|---|---|
| - | clean cover | - | 0.0% | 0.4939 | 0.4819 | 0.0 | False | False | False |
| 5 | RSA hex | 1280 | 1.3% | 0.4936 | 0.4371 | 0.0 | False | True | True |
| 5 | PQC hex | 2242 | 2.3% | 0.4933 | 0.4351 | 0.0 | False | True | True |
| 5 | PQC raw | 1125 | 1.1% | 0.4943 | 0.4924 | 0.9993 | True | False | True |
| 40 | RSA hex | 10240 | 10.4% | 0.4911 | 0.4372 | 0.0 | False | True | True |
| 40 | PQC hex | 2312 | 2.4% | 0.4933 | 0.4386 | 0.0 | False | True | True |
| 40 | PQC raw | 1160 | 1.2% | 0.4944 | 0.5008 | 1.0 | True | False | True |
| 200 | RSA hex | 51200 | 52.1% | 0.4707 | 0.4373 | 0.0 | False | True | True |
| 200 | PQC hex | 2632 | 2.7% | 0.4933 | 0.4385 | 0.0 | False | True | True |
| 200 | PQC raw | 1320 | 1.3% | 0.4945 | 0.5041 | 0.9998 | True | False | True |

With the pinned embedder both hex payloads (RSA and PQC) show a recognisable structure at the start of the LSB plane: the
32-bit length header (plausible length, `length header` True) followed by clean hex text (`hex header` True). The structure
is the same for RSA and PQC, so it does not separate them. (An earlier pinned run before the 32-bit-header fix read
`hex header` False because the scan started at bit 0.)

Facts from the formulas (match the table): textbook RSA-1024 hides 128 bytes per message character; the PQC blob adds a
fixed 1,120 bytes (4-byte header + 1,116); so the PQC raw payload is smaller than the RSA payload for messages longer
than about 9 characters.

Findings (draft from the measured tables; check them against your final tables):
- Payload size: PQC hex is larger than RSA hex at 5 characters (2,242 B vs 1,280 B) and smaller from about 9 characters
  upward (2,312 B vs 10,240 B at 40; 2,632 B vs 51,200 B at 200). The expectation in the plan, that the PQC payload
  would be larger, holds only for very short messages.
- Where it shows: the 200-character RSA payload moves Lena's whole-image ones fraction from 0.4939 to 0.4719 and uses 52%
  of the capacity. The PQC payloads move it by 0.0006 or less.
- The detectors react to the hiding format, not to RSA vs ML-KEM. Hex-text payloads (RSA hex and PQC hex alike) have a
  ones fraction of about 0.44 in the embedded region (clean: 0.48) and a hex-string start. The raw PQC format has a
  random-looking ones fraction but is flagged by the chi-square pair rule and by its length header.
- Neither the PQC nor the RSA hex rows are flagged by the chi-square region rule.

Limits: two images, one reference embedder plus the pinned one for hex rows, simple detectors. The whole-image chi-square
is 0.0 in every row (only 1 to 52 percent of the image is changed), so it does not discriminate here. The region test
assumes the detector knows where the payload starts and ends. "Not flagged" does not mean undetectable.

## 5. What we did not show

- No attack on the pinned project's real 256-bit or 512-bit image key (needs a sieve tool; stretch goal, not done unless listed above).
- No hardware run: every quantum result is a simulator result.
- The PQC libraries are educational (kyber-py is not hardened against timing attacks); a failed attack here is evidence for
  this construction, not a proof that ML-KEM is secure.
- The video PQC variant is not attacked yet (it depends on the video prototype).
- Steganalysis used simple detectors, not state-of-the-art ones.
