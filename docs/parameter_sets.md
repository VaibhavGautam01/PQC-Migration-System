# Parameter Sets: ML-KEM and ML-DSA

Weights v1.0 are unaffected: every NIST PQC choice scores F1 = 5, so the choice
between sets is made on capacity and assurance, not on the risk score.

Sizes in bytes. Source: plan table (FIPS 203 and 204). Checked against the
standards by <name> on <date>: <yes / not yet>. Library check
(`python src/parameter_sets.py --measure`): <no differences / differences: ...>.

| Set | NIST category | Public key | Secret key | Ciphertext or signature |
|---|---|---|---|---|
| ML-KEM-512 | 1 | 800 | 1,632 | 768 |
| ML-KEM-768 | 3 | 1,184 | 2,400 | 1,088 |
| ML-KEM-1024 | 5 | 1,568 | 3,168 | 1,568 |
| ML-DSA-44 | 2 | 1,312 | 2,560 | 2,420 |
| ML-DSA-65 | 3 | 1,952 | 4,032 | 3,309 |
| ML-DSA-87 | 5 | 2,592 | 4,896 | 4,627 |

## Payload overhead and capacity

Payload = KEM ciphertext + 12-byte nonce + 16-byte tag + message, plus the
signature when signing. Message 100 bytes. Capacity assumption: 1 bit per
colour channel, 3 channels (<confirmed against the pinned embedding / not
confirmed>); video frames also carry a 16-bit length header.

| Setup | Overhead (B) | Total (B) | Smallest square image | Frames of 128x128 | Rate in 256x256 |
|---|---|---|---|---|---|
| ML-KEM-512 | 796 | 896 | 49 px | 1 | 3.6% |
| ML-KEM-512 + ML-DSA-44 | 3,216 | 3,316 | 95 px | 1 | 13.5% |
| ML-KEM-768 | 1,116 | 1,216 | 57 px | 1 | 4.9% |
| ML-KEM-768 + ML-DSA-65 | 4,425 | 4,525 | 110 px | 1 | 18.4% |
| ML-KEM-1024 | 1,596 | 1,696 | 68 px | 1 | 6.9% |
| ML-KEM-1024 + ML-DSA-87 | 6,223 | 6,323 | 130 px | 2 | 25.7% |

For comparison a textbook RSA ciphertext is 32 B (256-bit) to 256 B (2048-bit).
The 1,116 B overhead of ML-KEM-768 matches the layout checked in
`src/hybrid_review.py`. Extra headers in the real format add to these numbers.
A larger payload is easier to detect; the detectability is measured separately
(steganalysis), not by this table.

## Recommended default

**ML-KEM-768 + ML-DSA-65** (NIST category 3 for both): moderate sizes, 1,116 B
unsigned and 4,425 B signed.

## When to choose another

| Choice | Choose it when | Cost or trade-off |
|---|---|---|
| ML-KEM-512 + ML-DSA-44 | the cover is small or capacity is tight, and the data is short-lived | lower assurance (category 1 and 2); saves 320 B on the ciphertext and 889 B on the signature |
| ML-KEM-1024 + ML-DSA-87 | the data must stay secret the longest and capacity is ample | 480 B more ciphertext and 1,318 B more signature; 25.7% of a 256x256 image |
| SLH-DSA instead of ML-DSA | a hash-based, conservative signature is wanted | much larger signatures; not compared here |
| Hybrid with X25519 | during a transition | an extra classical key exchange to carry (about 32 bytes) |

Keep the KEM and the signature at matching categories: mixing them makes the
weaker one the real limit. Signing is optional and roughly quadruples the payload
at the default sizes.

## Limits

- Sizes come from the plan table and need the standards check above.
- The capacity model is an assumption about the embedding, not a measurement.
- The libraries (kyber-py, dilithium-py) are educational and not hardened
  against timing attacks; they are prototype code, not production crypto.
- The risk model scores all NIST PQC sets alike (F1 = 5).