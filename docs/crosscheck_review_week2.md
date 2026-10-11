# Week 2 Day 2: Check B review (Tarun)

Source: docs/crosscheck_week2.md (Check B: 166 unflagged crypto-looking lines).
Method: src/triage_checkb.py split them into 109 comments/docstrings/UI text,
36 other code lines and 21 candidates; each candidate was read by hand.

## Real scanner gap (fixed)
- r_channel_stego.py:42 and :54 pick RSA primes with sympy isprime(). The old
  prime patterns (getPrime, randprime, nextprime) did not match this style, so
  the prime-selection step was unflagged (the phi and modular-inverse lines in
  that file were already caught). Added pattern RSA-MANUAL-PRIME-ISPRIME
  (confidence: low). Result: findings 24 -> 26 (part1 15 -> 17).

## Not bugs (kept as is)
- encrypt/decrypt wrapper definitions and calls (rsa_utils.py, rsa_crypto.py,
  pipeline.py, r_channel_stego.py, rsa_lsb_stego.py): the RSA operation inside
  them is already flagged as RSA-MODEXP (rsa_crypto.py:142, :170 and
  rsa_utils.py:45, :50 in the scanned copy), and cross-file use is covered by
  the edge-case INDIRECT_USAGE check.
- GCD(e, phi) and phi % e loops: public-exponent selection helpers with no key
  size or algorithm information.
- import hashlib, from sympy import isprime: imports alone are not flagged;
  the actual hash call is (frame_selector.py:32, HASH-SHA2-HASHLIB).
- Remaining lines: comments, docstrings, UI text and variable names.
