## Classical key strength

These ratings are independent of the quantum risk score. A short RSA/DSA/DH key can be broken by ordinary computers today, with no quantum computer involved.

| Project | File:line | Modulus (bits) | Basis | Rating | Reason |
|---|---|---|---|---|---|
| Final-Year-project-part1 | app.py:239 | 256 | in use | CRITICAL | breakable on ordinary hardware today (RSA-512 was factored in 1999) |
| Final-Year-project-part1 | app.py:385 | 256 | in use | CRITICAL | breakable on ordinary hardware today (RSA-512 was factored in 1999) |
| Final-Year-project-part1 | main.py:101 | 256 | in use | CRITICAL | breakable on ordinary hardware today (RSA-512 was factored in 1999) |
| Final-Year-project-part1 | rsa_utils.py:27 | 512 | default only | CRITICAL | breakable on ordinary hardware today (RSA-512 was factored in 1999) |
| Final-Year-project-part1 | rsa_utils.py:28 | 512 | default only | CRITICAL | breakable on ordinary hardware today (RSA-512 was factored in 1999) |
| Final-Year-project-part1 | rsa_utils.py:30 | 512 | default only | CRITICAL | breakable on ordinary hardware today (RSA-512 was factored in 1999) |
| Secure-Video-Steganography | rsa_crypto.py:48 | 1024 | default only | MEDIUM | below the 2048-bit NIST minimum; weak classical margin |
| Secure-Video-Steganography | rsa_crypto.py:49 | 1024 | default only | MEDIUM | below the 2048-bit NIST minimum; weak classical margin |

17 further RSA/DSA/DH findings carry no modulus size and are not rated.

Sizes are the modulus sizes resolved by the scanner's key-size extraction.
Rows marked 'default only' take the size from a function default value; the size really used by callers or the UI may differ.
