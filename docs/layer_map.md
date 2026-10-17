# Layer map (Week 1, Tarun)

Version: scanner v0.4.0 findings.json (31 findings). Counts below are from `python src/layers.py`;
Tarun regenerates them on Week 1 Day 5 and names the commit.

## Layers
| Layer | Image project (final-year-part1) | Video project (Secure-Video-Steganography) |
|---|---|---|
| L1 Message encryption | textbook RSA, no padding. 21 findings | textbook RSA, no padding. 9 findings |
| L2 Frame-selection key | none (keyless embedding). 0 findings | SHA-256 of passphrase (`frame_selector.py:32`). 1 finding |
| L3 Integrity | none (manual) | CRC32, works as key-check oracle (manual, **no scanner finding**) |
| L5 Signature | none (manual) | none (manual) |
| Hiding layer | LSB, measured by steganalysis, not scored | XOR-LSB, same |

## Image project, L1 by file
| File | Lines | What | Key size in use |
|---|---|---|---|
| `rsa_utils.py` | 22-50 | manual RSA (primes, phi, modinv, modexp) | 512-bit is **default only**, not used |
| `app.py` / `main.py` | 229, 239, 373, 385 / 83, 101 | keygen wrapper calls | 256-bit (`bits=128`) at 239, 385, 101; 8-bit at 229, 373, 83 |
| `r_channel_stego.py` | 42-59 | R-channel RSA | 8-bit (n < 256) |

## Video project, by file
| File | Lines | Layer | Note |
|---|---|---|---|
| `rsa_crypto.py` | 45-170 | L1 | function default 1024; UI offers 1024/2048/3072, UI default 2048 |
| `app.py` | 263 | L1 | keygen call |
| `frame_selector.py` | 32 | L2 | SHA-256 digest reaches frames 0-255 only |

## Open points
1. L3 CRC32 line numbers in the video project: confirm by hand, then store in `manual_facts.json` (the target submodules are empty in the zip).
2. Image L1 has several key sizes (8, 256, 512 default). Score the size in use per call site, and flag default-only sizes (F3 rule).
3. Image L2/L3/L5 are "none" layers. How a missing layer enters the weakest-link score is decided with Yatharth (risk_model.md).
