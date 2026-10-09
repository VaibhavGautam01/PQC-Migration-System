# Week 1 Summary: Repository Setup & Detection Engine Core

**Owner:** Tarun Saxena (Detection Engine Lead) | **Branch:** `tarun/detection-engine`
**Sprint goal:** a general-purpose crypto detection engine (not only RSA), tested on both target repos.

## What was completed

| Day | Commit | Work done | Issue |
|---|---|---|---|
| Mon | `82b0a7d` | Repo structure, `.gitignore`, `requirements.txt`, README skeleton, first RSA signature patterns | #1 |
| Tue | `170da57`, `ac3cb4a` | Textbook-RSA patterns (prime helpers, modular inverse, `pow` / `(c ** d) % n`, `65537`); first scan of both target repos | #2 |
| Wed | `44bc2a7` | ECC, DSA, DH, AES and SHA patterns in `src/extra_patterns.py` | #2 |
| Thu | `7807c1e` | Key-size extraction in `src/key_size.py`: variable and default resolution, per-prime vs modulus size, wrapper calls | #2 |
| Fri | `9d54f73` | `src/run_all.py` merges both scans into `outputs/findings.json` v1 | #2, #4 |

## Scanner status (v0.4.0)

- 46 detection patterns across RSA, ECC, DSA, DH, AES and SHA.
- Every finding records: project, file, line, primitive, pattern_id, confidence, key_size, modulus_bits, size_basis, snippet.
- Verified on 4 test fixtures in `tests/fixtures/` (46 findings in total).

## Results on the target repos (findings.json v1)

| Project | Findings | Primitives |
|---|---|---|
| Secure-Video-Steganography | 9 | RSA 8, SHA 1 |
| Final-Year-project-part1 | 15 | RSA 15 |

## Manual notes (the scanner cannot determine these)

1. part1 real use: `generate_keypair(bits=128)` gives a 256-bit modulus. The 256/512 in `rsa_utils.py` is only a default value.
2. part1 `r_channel_stego.py`: modulus `n < 256`, about 8 bits.
3. steganography: key size is chosen in the UI (1024 / 2048 / 3072, default 2048).
4. `bits=N` is assumed to be the per-prime size (modulus = 2 x N), based on the `rsa_utils.py` docstring.

## Known gaps (planned for Week 2)

- Cross-check every finding against the source code line by line (false positives and misses).
- Indirect usage (crypto imported in one file, used in another) is handled by Vaibhav's edge-case module.
- Unit tests for `scanner.py` and a one-command test runner.
- Remove the unused `extract_key_size()` from `scanner.py` in the final cleanup.
