# Attack evidence: Week 3 (Vaibhav)

How to use this file: numbers marked **[FILL]** must be pasted from your own run output. Merge
these sections into docs/attack_evidence.md (Week 3 Day 5 task) once filled in.

Versions: qiskit **[FILL]**, qiskit-aer **[FILL]**, kyber-py **[FILL]**, dilithium-py **[FILL]**,
pycryptodome **[FILL]**. Commit: **[FILL: `git rev-parse --short HEAD`]**.

## 1. Attack on the PQC video variant

Code: `extras/attack_pqc_video.py`. Attacker has the stego frames and the public key(s) only.
Frames: **[FILL: real frame count/size, or synthetic — note which]**.

Tested against the real pqc_stego/video_pqc.py, with a hand-built (non-ML-DSA) stand-in for
signing.py used only to validate video_pqc.py's own control flow - the one row below marked
[RE-CHECK] needs confirming against the real signing.py.

| Check | Result (this run) | On your machine |
|---|---|---|
| Extract the header/body without any secret | PASS, flag=0, 1144 B, 3 frames used | **[FILL]** |
| Decrypt with the right secret key | PASS | **[FILL]** |
| Decrypt with the wrong secret key | PASS (HybridDecryptError) | **[FILL]** |
| Flip 1 bit in the header | PASS (VideoFormatError: unknown flag) | **[FILL]** |
| Flip 1 bit in a payload-carrying frame | PASS (HybridDecryptError) | **[FILL]** |
| Signed video: flag readable without a secret | PASS | **[FILL]** |
| Signed video: verify + decrypt with the right verifier key | PASS | **[FILL]** |
| Signed video read WITHOUT the verifier's public key | PASS (VideoFormatError) | **[FILL]** |
| Plain video read WITH a verifier public key | PASS (VideoFormatError) | **[FILL — re-check]** |
| Signed video verified with the WRONG signer's key | **[RE-CHECK with real signing.py]** | **[FILL]** |
| Tamper a signed video's payload | PASS (HybridDecryptError) | **[FILL]** |
| frame_select_v2 order round-trips correctly | PASS | **[FILL]** |

Conclusion: 11 of 12 checks confirmed against the real video_pqc.py (reference backend). The
encryption layer rejects every attack tried (wrong key, header tamper, payload tamper); extraction
of the raw header/body still works without any key, confirming the plan's stated risk "Video
hiding layer stays weak" - migration fixes the encryption/signing layers, not the hiding layer.
**[FILL once you confirm the one re-check row with real signing.py.]**

## 2. Steganalysis: RSA vs PQC vs signed PQC payload (video)

Code: `extras/steganalysis_video.py`. Paste `outputs/steganalysis_pqc_video.md` here:

**[FILL]**

Findings (this run, reference backend, 30 synthetic frames x 4000 B):
- RSA-sized payload grows per character (640 B at 5 chars -> 5,120 B at 40 chars) and does not
  fit at all for 200 characters in this frame count; the PQC blob has a near-fixed ~1,120-1,320 B
  overhead regardless of message length, far smaller for anything beyond a few characters.
- PQC plain and the RSA-sized stand-in are both FLAGGED by the chi-square region test (p~1.0) -
  this is the standard tell of LSB replacement itself, not something that distinguishes RSA from
  PQC.
- The "PQC signed" row's numbers in THIS run (ones~0.13-0.17, NOT flagged) are an artifact of a
  non-ML-DSA stand-in used to test the script and must be re-measured with the real signing.py
  before quoting; a genuine ML-DSA-65 signature should look pseudorandom like the other rows.
**[FILL: replace with your own numbers once re-run with the real signing.py.]**

## 3. What we did not show (video)

- No attack on the pinned video project's real key size.
- No steganalysis on a real decoded video, only synthetic frames.
- dilithium-py (ML-DSA) is educational, not hardened; a passed signature check here is evidence
  for this construction, not a general proof.
- frame_select_v2's 256-bit key is not brute-forced (out of reach); only its reach across frames
  beyond 255 is demonstrated.
