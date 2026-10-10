# Edge-Case Flag Validation

Manual check of automated flags against both target projects.

## Image project (Final-Year-project-part1)

| Flag | Location | Result | Evidence |
|---|---|---|---|
| NO_PADDING | rsa_utils.py:54 | Confirmed | `return pow(m, e, n)`: textbook RSA, no OAEP/PKCS1 |
| NO_PADDING | rsa_utils.py:59 | Confirmed | `return pow(c, d, n)`: textbook RSA, no padding |
| INDIRECT_USAGE | app.py:27, main.py:14, rsa_lsb_stego.py:11, r_channel_stego.py:23 | Confirmed | import functions from rsa_utils.py |
| INDIRECT_USAGE | app.py:25, main.py:12 | Confirmed | import from r_channel_stego.py, which has its own RSA setup (phi, modular inverse) |
| False positive (fixed) | `import rsa` in app.py, main.py | Fixed | pattern matched `import rsa_utils`; corrected with `\b` |

Key size: the scanner reported 16, but that is the prime size. The modulus is about 31 bits (generate_keypair default bits=16).

## Video project (Secure-Video-Steganography)

| Flag | Location | Result | Evidence |
|---|---|---|---|
| NO_PADDING | rsa_crypto.py:142 | Confirmed | `c = pow(m, e, n)`: textbook RSA encryption |
| NO_PADDING | rsa_crypto.py:170 | Confirmed | `m = pow(c, d, n)`: textbook RSA decryption |
| `from Crypto` | rsa_crypto.py | Helper only | uses Crypto.Util.number (getPrime, GCD, inverse); RSA itself is hand-written |
| INDIRECT_USAGE | app.py, pipeline.py | Confirmed | import rsa_crypto and frame_selector |

Key size: default 1024 bits. The length + CRC32 framing is not real padding: it is deterministic and gives an attacker a way to check a recovered key.

## Additional findings

- The frame-selection secret key can be bypassed. Frames carrying data can be found by scanning for a plausible 16-bit length header (src/video_attack.py).
- Frame selection only covers indices 0-255, because a SHA-256 digest has 256 bits.
- Reduced-key breaks: image project 31-bit modulus factored in 0.0002s; video project 95-bit modulus factored in 0.23s. Both recovered the message using only public information.

## Week 2 re-check: flags in the combined outputs/findings.json

Checked the 4 edge_flag findings against the copies in data/targets.

| Project | File:line | Result | What the code shows |
|---|---|---|---|
| Final-Year-project-part1 | rsa_utils.py:54 | Confirmed | `return pow(m, e, n)` in encrypt_int: raw modular exponentiation, no OAEP/PKCS1 |
| Final-Year-project-part1 | rsa_utils.py:59 | Confirmed | `return pow(c, d, n)` in decrypt_int: raw modular exponentiation |
| Secure-Video-Steganography | rsa_crypto.py:142 | Confirmed | `c = pow(m, e, n)`; m is [length][CRC32][data][zeros], a fixed layout, so encryption is deterministic (not randomized padding) |
| Secure-Video-Steganography | rsa_crypto.py:170 | Confirmed | `m = pow(c, d, n)`; the code after it only checks length and CRC32 (integrity check, not padding) |

Note: line numbers are for the local copies in data/targets. They may shift if the team pins a different commit of the target projects. No false positives in this set.