# Key-size decisions (agreed by the team)

The scanner cannot always see the real key size, so these facts come from reading the
code. They are applied through `data/manual_facts.json` (confirmed overrides) and shown
in the CBOM.

## Final-Year-project-part1 (image steganography)

| Key path | Modulus | Where | Notes |
|---|---|---|---|
| `generate_keypair(bits=128)` | 256 bits | app.py:239, 385; main.py:101 | The real use. Applied to `rsa_utils.py` lines 27, 28 and 30 only. |
| `generate_small_keypair()` | n < 256, at most 8 bits | R-channel module (callers pass no argument, so max_n=256) | Real use. |
| `bits=256` default in `rsa_utils.py` | 512 bits | `rsa_utils.py` | Only a default; not used. |

Lines such as `phi` and `pow` have no size of their own, so they get no size override and
appear in a separate "unknown size" CBOM entry.

## Secure-Video-Steganography

The key size is **user-selectable**: the UI selectbox offers 1024, 2048 and 3072 bits with
2048 as the UI default (`index=1`). 1024 is only the function default. The CBOM records
2048 and notes that a user who picks 1024 gets a key below the 2048-bit minimum.

## Padding

Both projects use textbook RSA with no padding. The edge-case module flags it
(`edge_flag` = `NO_PADDING` on 4 findings, all confirmed by hand). This is a classical
weakness (deterministic encryption), not a consequence of Shor's algorithm.

## Experiments on local small-key copies (not the projects of record)

| Id | Key | Result | Target |
|---|---|---|---|
| EXP-IMAGE-31 | 31-bit modulus | factored in 0.0002 s | Vaibhav's ZIP copy of the image project (`generate_keypair` defaults to bits=16) |
| EXP-VIDEO-95 | 95-bit modulus | factored in 0.23 s | `video_stego_project_updated`, reduced key from `generate_keypair(key_size=96)` |

The toy N=15 and N=21 runs also use the image copy. These show what a small modulus costs
an attacker. They say nothing about the 256-bit, 8-bit or 2048-bit keys above and must not
be quoted as results for the pinned projects.
