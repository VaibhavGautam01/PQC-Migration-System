\# Edge-Case Flag Validation



Manual check of automated flags against both target projects.



\## Image project (Final-Year-project-part1-main)



| Flag | Location | Result | Evidence |

|---|---|---|---|

| NO\_PADDING | rsa\_utils.py:54 | Confirmed | `return pow(m, e, n)`: textbook RSA, no OAEP/PKCS1 |

| NO\_PADDING | rsa\_utils.py:59 | Confirmed | `return pow(c, d, n)`: textbook RSA, no padding |

| INDIRECT\_USAGE | app.py:27, main.py:14, rsa\_lsb\_stego.py:11, r\_channel\_stego.py:23 | Confirmed | import functions from rsa\_utils.py |

| INDIRECT\_USAGE | app.py:25, main.py:12 | Confirmed | import from r\_channel\_stego.py, which has its own RSA setup (phi, modular inverse) |

| False positive (fixed) | `import rsa` in app.py, main.py | Fixed | pattern matched `import rsa\_utils`; corrected with `\\b` |



Key size: the scanner reported 16, but that is the prime size. The modulus is about 31 bits (generate\_keypair default bits=16).



\## Video project (video\_stego\_project\_updated)



| Flag | Location | Result | Evidence |

|---|---|---|---|

| NO\_PADDING | rsa\_crypto.py:142 | Confirmed | `c = pow(m, e, n)`: textbook RSA encryption |

| NO\_PADDING | rsa\_crypto.py:170 | Confirmed | `m = pow(c, d, n)`: textbook RSA decryption |

| `from Crypto` | rsa\_crypto.py | Helper only | uses Crypto.Util.number (getPrime, GCD, inverse); RSA itself is hand-written |

| INDIRECT\_USAGE | app.py, pipeline.py | Confirmed | import rsa\_crypto and frame\_selector |



Key size: default 1024 bits. The length + CRC32 framing is not real padding: it is deterministic and gives an attacker a way to check a recovered key.



\## Additional findings



\- The frame-selection secret key can be bypassed. Frames carrying data can be found by scanning for a plausible 16-bit length header (src/video\_attack.py).

\- Frame selection only covers indices 0-255, because a SHA-256 digest has 256 bits.

\- Reduced-key breaks: image project 31-bit modulus factored in 0.0002s; video project 95-bit modulus factored in 0.23s. Both recovered the message using only public information.

