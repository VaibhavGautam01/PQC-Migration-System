"""
frame_select_v2.py
------------------
Keyed, whole-video frame selection (spec: docs/frame_select_v2_spec.md).

The old scheme turned the bytes of an unsalted SHA-256 of a passphrase into frame
numbers, so only frames 0 to 255 could ever be chosen. This version uses a random
256-bit key and HMAC-SHA256 as a pseudo-random function, so every frame of the
video can be selected and every frame is equally likely.

  key = generate_key()                              # 32 random bytes
  frames = select_frames(key, total_frames, count)  # distinct frame numbers

Properties:
  * indices are distinct and lie in [0, total_frames)
  * same key and total_frames give the same list (the extractor repeats it)
  * prefix-stable: the first j frames do not depend on count, so the extractor can
    read the payload length from the first frames before it knows how many it needs
  * no modulo bias (rejection sampling); memory is O(count)

Standard library only. This module does not hide that data exists and does not
decide how the key reaches the receiver.
"""
import hashlib
import hmac
import secrets

KEY_LEN = 32
_DOMAIN = b"pqc-stego frame-select v2"

__all__ = ["KEY_LEN", "generate_key", "select_frames"]


def generate_key() -> bytes:
    """Return a fresh random 256-bit key."""
    return secrets.token_bytes(KEY_LEN)


def _words(key: bytes, total_frames: int):
    """Endless stream of 64-bit words: HMAC-SHA256 in counter mode."""
    counter = 0
    while True:
        block = hmac.new(key, _DOMAIN + total_frames.to_bytes(8, "big")
                         + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        for i in range(0, 32, 8):
            yield int.from_bytes(block[i:i + 8], "big")
        counter += 1


def _below(words, bound: int) -> int:
    """Uniform integer in [0, bound) by rejection sampling (no modulo bias)."""
    limit = (1 << 64) - ((1 << 64) % bound)
    while True:
        v = next(words)
        if v < limit:
            return v % bound


def _check_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer, got {value!r}")


def select_frames(key: bytes, total_frames: int, count: int) -> list:
    """Return `count` distinct frame numbers in [0, total_frames), in embedding order."""
    if not isinstance(key, (bytes, bytearray)) or len(key) != KEY_LEN:
        raise ValueError(f"key must be {KEY_LEN} bytes")
    _check_int(total_frames, "total_frames")
    _check_int(count, "count")
    if total_frames < 1:
        raise ValueError("total_frames must be at least 1")
    if not 0 <= count <= total_frames:
        raise ValueError("count must be between 0 and total_frames")

    words = _words(bytes(key), total_frames)
    moved, out = {}, []                     # virtual Fisher-Yates shuffle
    for i in range(count):
        j = i + _below(words, total_frames - i)
        at_i, at_j = moved.get(i, i), moved.get(j, j)
        moved[j], moved[i] = at_i, at_j
        out.append(at_j)
    return out