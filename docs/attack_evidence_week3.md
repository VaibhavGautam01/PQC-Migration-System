# Attack evidence: Week 3 (Vaibhav)

Everything below was measured on one machine and copied from its output. No number comes from a stand-in.

Measured on: Python 3.14.5 (Windows), pytest 9.1.1, kyber-py 1.2.0, dilithium-py 1.5.1, pycryptodome 4.0.0.
Repo commit the scripts ran at: `eb95f10`. Pinned video project (scanned target): `4514806`.

**Reference backend.** `pqc_stego/video_pqc.py` embeds with its own LSB writer, a reference backend written for testing. It is NOT the pinned video project's embedding or slicing code. Every video result in this file was measured on that reference backend, with synthetic frames, and must be quoted that way.

## 1. Attack on the PQC video variant

Code: `extras/attack_pqc_video.py`. The attacker has the stego frames and the public key(s) only.
Frames: 20 synthetic frames of 4000 raw bytes each (total capacity 10,000 bytes), not a real decoded video.
Unit tests: `tests/test_video_pqc.py`, 9 passed in 0.42 s.

| Check | Expected | Observed (this run) |
|---|---|---|
| Extract the hidden body without any secret | works, flag = 0 | works, flag = 0, 1144 bytes, 3 frames used |
| Receiver decrypts with the right secret key | message read back | message read back |
| Decrypt with the wrong secret key | fails | HybridDecryptError (authentication failed) |
| Flip 1 bit in the header (frame 0) | fails loudly | VideoFormatError (unknown flag) |
| Flip 1 bit in a payload-carrying frame (frame 1) | fails loudly | HybridDecryptError (authentication failed) |
| Signed video: flag readable without any secret | flag = 1 | flag = 1 |
| Signed video: receiver verifies and decrypts | message read back | message read back |
| Signed video read WITHOUT the verifier's public key | rejected | VideoFormatError (a verifier public key is required) |
| Plain video read WITH a verifier public key | rejected | VideoFormatError (expected a signed payload) |
| Signed video verified with the WRONG signer's public key | rejected | SignatureError (signature does not verify) |
| Tamper a signed video's payload (frame 1) | rejected | SignatureError (signature does not verify) |
| Round trip with a frame_select_v2 order | works | works (the script prints only "order test") |
| frame_select_v2 order reaches beyond frame 255 | n/a below 256 frames | by construction only: this run has 20 frames, first 10 indices of the order [0, 7, 5, 3, 14, 19, 18, 16, 8, 1] |

Signing is the real `pqc_stego/signing.py` (ML-DSA-65 from dilithium-py).

Result: every check matched its expectation. Twelve checks are measured; the last one is by construction and is NOT demonstrated by this run, because 20 frames cannot show a frame above 255.

The encryption layer rejects every attack tried (wrong key, header change, payload change). Extraction of the raw body still works without any key, so the hiding layer is unchanged. Migration fixes the encryption and signing layers, not the hiding layer.

## 2. Steganalysis: RSA-sized vs PQC vs signed PQC payload (video)

Code: `extras/steganalysis_video.py`, run as `--frames 30 --frame-size 4000 --lengths 5 40 200`. Synthetic frames, reference backend, total capacity 15,000 bytes, real ML-DSA-65 from `signing.py`.

| msg chars | payload | bytes | frames used | ones (clean) | ones (stego) | chi p (region) | flagged (p>0.5) |
|---|---|---|---|---|---|---|---|
| 5 | RSA-sized (stand-in) | 640 | 2 | 0.4946 | 0.5012 | 0.9996 | True |
| 5 | PQC plain | 1121 | 3 | 0.4916 | 0.4936 | 1.0 | True |
| 5 | PQC signed (ML-DSA-65) | 4430 | 9 | 0.4978 | 0.4964 | 1.0 | True |
| 40 | RSA-sized (stand-in) | 5120 | 11 | 0.4978 | 0.5054 | 1.0 | True |
| 40 | PQC plain | 1156 | 3 | 0.4916 | 0.4983 | 1.0 | True |
| 40 | PQC signed (ML-DSA-65) | 4465 | 9 | 0.4978 | 0.4939 | 0.9998 | True |
| 200 | RSA-sized (stand-in) | 25600 | does not fit in these frames | | | | |
| 200 | PQC plain | 1316 | 3 | 0.4916 | 0.501 | 1.0 | True |
| 200 | PQC signed (ML-DSA-65) | 4625 | 10 | 0.4976 | 0.4918 | 1.0 | True |

Findings:
- Payload size: the RSA-sized stand-in grows with the message (640 bytes at 5 characters, 5,120 at 40) and does not fit at 200 characters (25,600 bytes against 15,000 bytes of capacity). PQC plain is 1,121, 1,156 and 1,316 bytes (message plus 1,116 bytes of overhead). PQC signed adds 3,309 bytes: 4,430, 4,465 and 4,625 bytes.
- Frames used: RSA-sized 2 (5 characters) and 11 (40 characters); PQC plain 3 in all three runs; PQC signed 9, 9 and 10.
- Every row that fits is flagged by the chi-square region test (p from 0.9996 to 1.0), and the share of 1s in the LSB plane stays within about 0.01 of the clean frames. So the test detects LSB replacement itself. It does not separate the RSA-sized, PQC and signed PQC payloads; the signed payload is neither easier nor harder to detect by this test.
- The "RSA-sized" rows are random bytes of RSA ciphertext size, not a real RSA round trip. They compare payload size and LSB statistics only.

## 3. What we did not show (video)

- Not the pinned project's code: the embedding and slicing are a reference backend, so nothing here measures the pinned video project's own embedding.
- No attack on the pinned video project's real key size.
- No steganalysis on a real decoded video, only synthetic frames of random bytes. A lossy codec would destroy the embedded bits; this was not tested.
- Only simple detectors (share of 1s, chi-square pair test), not state-of-the-art steganalysis.
- frame_select_v2: reach beyond frame 255 is not shown by these scripts (20 and 30 frames). The 256-bit key is not brute-forced; that is out of reach.
- dilithium-py (ML-DSA) and kyber-py are educational libraries, not hardened. A passed signature check here is evidence for this construction, not a general proof.
- "The attack fails" means the attacks tried failed. It is not a proof of security.
