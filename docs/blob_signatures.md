# Blob signatures for the Stego Analyzer (our own formats only)

Source of truth: stego_analyzer/cipher_identify.py and pqc_stego/hybrid.py (hybrid.OVERHEAD = 1,116 B).

| Verdict | Rule | What it does NOT prove |
|---|---|---|
| textbook_rsa | hex text, public key given, whole number of blocks for N (2 or more), every block below N | The padding scheme: one OAEP block also looks like a textbook block |
| ml_kem_aes_gcm | hex text of at least 1,116 B (1,088 KEM ciphertext + 12 nonce + 16 tag), not a textbook layout | The structure inside: any 1,088-byte string is a valid ML-KEM ciphertext, so only the secret key can confirm it. Report as "consistent with ML-KEM + AES-GCM (length rule only)". |
| unrecognised | anything else | Nothing: no guess is made |

## Known ambiguity
A long RSA blob read without its public key can exceed 1,116 B and match the ML-KEM length rule.
OAEP versus textbook cannot be separated by length. Repeated blocks prove determinism (so not OAEP) only when the
block count is small compared with N. Padding is confirmed only after a successful break.

## Scoring consequence
When padding is undetermined, F4 is shown as a range (textbook to OAEP) or as the labelled worst case.
Sizes come from FIPS 203 and are locked by tests/test_sizes_match_libraries.py.
