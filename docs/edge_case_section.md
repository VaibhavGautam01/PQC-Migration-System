## Edge-case findings (Vaibhav)



Both target projects, pinned at final-year-part1 bb6d944 and steganography 4514806, encrypt with textbook RSA.



### Padding (confirmed by hand)



Four flagged sites, each read in the pinned code: rsa_utils.py:45 and :50 (image project) and rsa_crypto.py:142 and :170 (video project). All four are raw `pow()` calls with no OAEP or PKCS1. The video project wraps the message as \[length]\[CRC32]\[data]\[zeros] before encrypting. That layout is fixed, so encryption is still deterministic.



### Indirect usage



Ten flags: 6 in the image project and 4 in the video project. The crypto is defined in `rsa_utils.py`, `r_channel_stego.py`, `rsa_crypto.py` and `frame_selector.py` and used through imports elsewhere. A scan of a single file would miss it.



### Weaknesses that follow from the missing padding



- **Deterministic encryption:** the same plaintext always gives the same ciphertext. The image project encrypts one character at a time, so a message can be recovered by frequency analysis without factoring.

- **Malleability:** textbook RSA lets an attacker modify ciphertext in predictable ways.

- **Key-check oracle (video project):** the CRC32 inside the plaintext lets an attacker test a candidate private key, because a wrong key fails the checksum.

- **Frame-selection key:** embedded frames can be found by scanning for a plausible 16-bit length header, without the secret key.



### Classical key strength



Rated independently of the quantum score by `key_strength_check.py`:



- Image project, in real use: 256-bit modulus (`app.py` and `main.py` with `bits=128`). Rating CRITICAL: breakable on ordinary hardware today.

- Image project, `rsa_utils.py` default only: 512-bit modulus, also CRITICAL, but callers pass `bits=128`.

- Video project: the function default is 1024 bits (MEDIUM, below the 2048-bit minimum). The UI offers 1024, 2048 and 3072, with 2048 as the default, which meets the minimum. A user who picks 1024 gets the MEDIUM rating.



### Attack demonstrations (local small-key snapshots)



These ran on local copies with reduced keys, not on the pinned commits:



- Image pipeline, 31-bit modulus (`bits=16`): ciphertext extracted from the stego image, n factored in 0.0002 s, message recovered.

- Video pipeline, 95-bit modulus (reduced key): message recovered in 0.23 s without the secret frame key.

- Toy N = 15 and N = 21 versions of the image pipeline exist as targets for Shor's circuit.



No time in this section was measured on the pinned code. The break needs only public information, but factoring a 256-bit or larger modulus needs a sieve method. All quantum results in this project are simulator, toy size.

