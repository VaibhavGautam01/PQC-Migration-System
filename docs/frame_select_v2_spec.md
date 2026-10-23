# Frame-Selection v2: Specification

Owner: Yatharth Raghuvanshi. Implementation: `pqc_stego/frame_select_v2.py`
(Week 3, Day 2). Tests: `tests/test_frame_select_v2.py`.
The pinned video project is never edited; the prototype imports it by path.

## 1. Problem (current behaviour)

Source: `frame_selector.py` in Secure-Video-Steganography, pinned at 4514806.

- The key is the SHA-256 of a passphrase: unsalted, no key stretching
  (`frame_selector.py` line <n>).
- `sha256_select_indices(<signature>)` turns digest bytes into frame numbers.
  A digest byte is 0 to 255, so only frames 0 to 255 can ever be selected
  (<line numbers / not confirmed>).
- A guessed passphrase can be checked without decrypting: each selected
  frame carries a 16-bit length header that looks plausible only for the
  right frames (<where in the code>).
- Result: a video longer than 256 frames is only partly used, and the
  frame-selection key is only as strong as the passphrase.

## 2. Goals and non-goals

Goals:
1. Every frame of the video can be selected (whole-video coverage).
2. The selection is controlled by a 256-bit random key, not by a passphrase.
3. Every frame is equally likely (no bias).
4. Same key and video length give the same selection (the extractor repeats it).
5. Standard library only (`hmac`, `hashlib`, `secrets`); no new dependency.

Non-goals:
- It does not hide that data exists. The header scan and steganalysis are
  separate and are not fixed here.
- It does not decide how the key reaches the receiver (open question 1).

## 3. Design

Public interface (all in `pqc_stego/frame_select_v2.py`):

    generate_key() -> bytes                      # 32 random bytes (secrets)
    select_frames(key, total_frames, count) -> list[int]

`select_frames` returns `count` distinct frame numbers in `[0, total_frames)`,
in embedding order (the first number carries the first payload part).

Algorithm:
1. Keyed bit stream: block i = HMAC-SHA256(key, "pqc-stego frame-select v2"
   || total_frames (8 bytes) || i (8 bytes)). Each 32-byte block gives four
   64-bit words.
2. Uniform numbers without bias: rejection sampling. To draw below `bound`,
   discard words in the top partial range of 2^64, then take the word modulo
   `bound`.
3. Selection: a partial Fisher-Yates shuffle of `range(total_frames)` run
   virtually with a dictionary of swapped positions, so memory is O(count),
   not O(total_frames). Step i draws j uniformly in `[i, total_frames)`, swaps
   positions i and j, and outputs the frame now at position i.

Properties this gives:

| Property | Why |
|---|---|
| Whole-video coverage | the shuffle ranges over all positions, not over digest bytes |
| Uniform, no bias | Fisher-Yates plus rejection sampling |
| Prefix-stable | the stream depends on key and `total_frames` only, so `select_frames(k, n, j)` equals the first j entries of `select_frames(k, n, m)` for j < m. The extractor reads the payload length from the first frames and only then knows how many frames it needs |
| Domain separation | the fixed label keeps this use of the key apart from any other |
| Bound to video length | different `total_frames` gives a different selection |
| No passphrase oracle | with a 256-bit random key there is nothing to guess offline |

## 4. Security notes

- Random 256-bit key. Brute force is infeasible even with Grover's algorithm
  (about 128 bits of effective strength).
- HMAC-SHA256 is a standard keyed pseudo-random function.
- The key is shared out of band. If a human must type it, a passphrase mode is
  needed: derive the 256-bit key with a slow, salted function (hashlib.scrypt,
  per-file salt). This is optional and not part of the minimum design.
- The output order is secret. If a caller sorts the frames, the embedding
  order is lost.

## 5. Effect on the risk score

The video frame-selection layer (L2) changes from "SHA-256 of a passphrase"
(F4 = deterministic_or_oracle, 35.8, Moderate) to a random 256-bit key with a
keyed pseudo-random function. Which F4 category describes this is decided in
Week 3, Day 2, when the layer is re-scored. The weights file is frozen (v1.0);
a new category would be a new key in it and needs a change-log row and a new
lock.

## 6. Test plan (`tests/test_frame_select_v2.py`)

| Test | Checks |
|---|---|
| range, distinct, exact count | basic validity for several sizes |
| determinism, key sensitivity, video-length sensitivity | repeatable, and different inputs change the result |
| prefix stability | the first j frames do not depend on the requested count |
| count equals total | the result is a permutation of all frames |
| frames beyond 255 reachable | the old limit is gone |
| every position reachable (1,000 frames; slow test 5,000) | no frame is unreachable |
| first and last frame reachable | edge positions |
| chi-square uniformity (50 frames) and first-frame uniformity | no position is favoured |
| uniformity for a range of 1,000 | no modulo bias |
| bad inputs | wrong key length, wrong types, count above total |
| speed | 200,000 frames, 2,000 selected, under 3 seconds |
| source hygiene | no `random` module; uses `hmac` |
| tests are sensitive | the old scheme and modulo bias are caught by the same checks |

Keys come from a fixed sequence, so the tests are deterministic.

## 7. Acceptance criteria (Day 2)

All tests pass, including the slow ones (`SLOW_TESTS=1`), with only the
standard library, and `python -m src.quantum_guard` still passes.

## 8. Open questions

1. How does the receiver get the frame key? It cannot be inside the ML-KEM
   payload, because the payload sits in the frames the key selects. Options:
   shared out of band, or a separate small header at fixed positions. Decide
   with Tarun and Uday.
2. Is the number of frames needed known before extraction? (Prefix stability
   covers it, but the caller must read the length from the first frames.)
3. Is a passphrase mode needed for the UI?
4. Does the pipeline need frames returned sorted?


## 9. Exposure after v2 (video project)

The exposure input for the video project stays `bypassable` (F6 = 90). The
random key stops anyone from guessing the frame set, but the header scan can
still locate the frames that carry data (to be measured by Vaibhav in Week 3).
Choosing `keyed` would claim more than has been shown.

Video L2 scored with the current engine (symmetric, effective 128 bits; X = 5,
Y = 2, Z = 10):

| State | F4 category | Exposure | Quantum % | Classical % | Overall % | Band |
|---|---|---|---|---|---|---|
| Before (SHA-256 of a passphrase) | deterministic_or_oracle | bypassable | 9.0 | 76.0 | 35.8 | Moderate |
| Before | deterministic_or_oracle | keyed | 9.0 | 52.0 | 26.2 | Moderate |
| After v2 (provisional) | aead | bypassable | 9.0 | 4.8 | 7.3 | Low |
| After v2 (provisional) | aead | keyed | 9.0 | 3.2 | 6.7 | Low |

After v2, the exposure choice moves the score by 0.6 points, because F6 is
gated by the layer's weakness. Before v2 it moved it by 9.6 points.
"Provisional" because F4 = aead is the closest existing category for a keyed
pseudo-random function with a random 256-bit key; it is not literally AEAD.