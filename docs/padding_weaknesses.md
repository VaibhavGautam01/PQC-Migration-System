\# Confirmed Padding Weaknesses



Both target projects encrypt with textbook RSA: raw modular exponentiation, no OAEP or PKCS1 padding. Evidence for each flag is in docs/edge\_case\_validation.md.



\## Final-Year-project-part1 (image stego)



\- \*\*Where:\*\* `encrypt\_int` and `decrypt\_int` in rsa\_utils.py (lines 54 and 59 in the local copy).

\- \*\*Weakness 1, deterministic encryption:\*\* the same plaintext always gives the same ciphertext. The project encrypts text one character at a time (`encrypt\_text`), so each letter maps to a fixed number. The message is a substitution cipher over the public key, and frequency analysis recovers it without factoring n.

\- \*\*Weakness 2, malleability:\*\* textbook RSA satisfies E(a) \* E(b) mod n = E(a \* b) mod n, so an attacker can modify ciphertext blocks in predictable ways.

\- \*\*Weakness 3, tiny modulus:\*\* the default key is about 31 bits (generate\_keypair bits=16 gives two 16-bit primes). Classical factoring takes 0.0002 s.

\- \*\*Demonstrated:\*\* src/stego\_attack\_image.py extracts the ciphertext from the stego image, factors n and recovers the message using only public information.



\## Secure-Video-Steganography (video stego)



\- \*\*Where:\*\* `encrypt\_message` and `decrypt\_message` in rsa\_crypto.py (lines 142 and 170 in the local copy).

\- \*\*Weakness 1, deterministic encryption:\*\* the message is wrapped as \[length]\[CRC32]\[data]\[zeros] before `pow(m, e, n)`. That layout is fixed, so the same message always gives the same ciphertext. It is not randomized padding.

\- \*\*Weakness 2, key-check oracle:\*\* the CRC32 inside the plaintext lets an attacker test a candidate private key. A wrong d fails the checksum and the right d passes.

\- \*\*Weakness 3, single block:\*\* the message must fit one RSA block, which limits the capacity.

\- \*\*Key size:\*\* the default is 1024 bits. Classical factoring of that size is not feasible today, but a large fault-tolerant quantum computer running Shor's algorithm would break it.

\- \*\*Demonstrated:\*\* src/video\_attack.py recovers the message at a reduced 95-bit key without the secret frame key. Factoring took 0.23 s.



\## Recommended fix



1\. Use RSA-OAEP right away, which removes the determinism and malleability.

2\. For quantum resistance, replace RSA with ML-KEM-768 (FIPS 203) to agree a key, and encrypt the message with AES-GCM using that key.



Padding fixes the classical weaknesses only. It does not stop Shor's algorithm, which is why the migration to a post-quantum scheme is still needed.

