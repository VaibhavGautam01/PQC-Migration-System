"""Privacy amplification with a Toeplitz (2-universal) hash. Classical post-processing for QKD.

SAFETY NOTE: output length and safety margin here are teaching values, not a proven security
analysis. No error correction is implemented, so only noiseless runs can end in a key.
"""


def toeplitz_hash(bits, seed_bits, out_len):
    """Multiply the bit vector by an out_len x len(bits) Toeplitz matrix over GF(2)."""
    n = len(bits)
    if len(seed_bits) != n + out_len - 1:
        raise ValueError("seed must have len(bits) + out_len - 1 bits")
    return [sum(seed_bits[i - j + n - 1] & bits[j] for j in range(n)) & 1 for i in range(out_len)]


def bits_to_bytes(bits):
    if len(bits) % 8:
        raise ValueError("bit count must be a multiple of 8")
    return int("".join(str(b) for b in bits), 2).to_bytes(len(bits) // 8, "big")