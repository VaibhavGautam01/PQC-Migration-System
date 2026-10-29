# Blob signatures (analyzer draft, image project formats only)

| Payload | Length rule | Recognition |
|---|---|---|
| ML-KEM-768 + AES-256-GCM | length >= 1,116 B; message length = length - 1,116 | first 1,088 B = KEM ciphertext; then 12 B nonce, 16 B tag |
| Textbook RSA | length = modulus bytes (128 B for 1024-bit, 256 B for 2048-bit) | modulus size read from length |
| OAEP-style RSA | same length as textbook RSA at the same modulus size | NOT separable by length alone |

Open question: how does the image project's own format mark OAEP versus textbook? Check the pinned code before
Week 6; if there is no marker, the analyzer must say "RSA, padding unknown" rather than guess.

Sizes cross-checked against FIPS 203 (ML-KEM-768 ciphertext = 1,088 B). Test set: generated from our own projects only.
