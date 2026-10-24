"""
toy_cipher.py - the CLASSICAL reference model of the Q3 toy block cipher.

WHAT THE TOY CIPHER IS
----------------------
A tiny two-round substitution-permutation cipher with an 8-bit block and an 8-bit key
(256 possible keys). It is a teaching cipher: NOT AES, NOT secure, only small enough that
its whole encryption can be written as reversible quantum gates and simulated.

    x = plaintext (8 bits)
    round 1:  x = x XOR K
              x = S-box on the low nibble (bits 0-3) and on the high nibble (bits 4-7)
              x = bit permutation: the bit at position i moves to position (3 * i) mod 8
    round 2:  x = x XOR rotl(K, 3)              (rotl = rotate the 8-bit key left by 3)
              x = S-box on both nibbles
    ciphertext = x

The 4-bit S-box is defined in the quantum circuit as a small network of X, CNOT and Toffoli
gates (see q3_grover.py). SBOX below is the same permutation written as a table, so a test
can prove that the gate network and this table agree on every input (rule 9, truth table).

WHY THIS FILE IS SEPARATE FROM THE CIRCUIT
------------------------------------------
This module may compute ciphertexts and search all 256 keys, because it is used for
  * making the known plaintext/ciphertext pairs the attacker is given, and
  * the THEORY curve and the verification of what the circuit measured (rules 5 and 9).
The circuit builder (q3_grover.py) never imports this file: the quantum oracle must not be
able to see the key or the answer (rule 3). A test enforces that.

Aer simulator, toy size. Cipher is a toy; real AES/SHA sizes are covered only by published
estimates, never by this circuit.
"""

KEY_BITS = 8
BLOCK_BITS = 8
NUM_KEYS = 2 ** KEY_BITS

# the 4-bit S-box as a table: S(v) for v = 0..15 (equals the gate network in q3_grover.py)
SBOX = [8, 11, 10, 7, 14, 13, 3, 12, 0, 5, 2, 9, 4, 1, 15, 6]

# bit permutation of the linear layer: the bit at position i moves to position (3*i) % 8
BIT_PERM = [(3 * i) % 8 for i in range(8)]


def rotl8(value: int, shift: int) -> int:
    """Rotate an 8-bit value left by `shift` positions."""
    shift %= 8
    return ((value << shift) | (value >> (8 - shift))) & 0xFF


def sbox_layer(x: int) -> int:
    """Apply the S-box to the low nibble and to the high nibble of an 8-bit value."""
    return SBOX[x & 0xF] | (SBOX[x >> 4] << 4)


def bit_permute(x: int) -> int:
    """Linear layer: the bit at position i moves to position (3*i) mod 8."""
    out = 0
    for i in range(8):
        out |= ((x >> i) & 1) << BIT_PERM[i]
    return out


def round_key_2(key: int) -> int:
    """Key schedule: the second round key is the first one rotated left by 3 bits."""
    return rotl8(key, 3)


def encrypt(key: int, plaintext: int) -> int:
    """Encrypt one 8-bit block with an 8-bit key (the classical reference)."""
    x = plaintext ^ key
    x = sbox_layer(x)
    x = bit_permute(x)
    x ^= round_key_2(key)
    return sbox_layer(x)


def make_pairs(secret_key: int, plaintexts=(0x5A, 0xC3)) -> list:
    """Known plaintext / ciphertext pairs an attacker would have: [(P1, C1), (P2, C2)]."""
    return [(p, encrypt(secret_key, p)) for p in plaintexts]


def consistent(key: int, pairs) -> bool:
    """True when `key` encrypts every known plaintext to its known ciphertext.

    Used to VERIFY a key the circuit measured, and to count solutions for the theory curve.
    """
    return all(encrypt(key, p) == c for p, c in pairs)


def keys_matching(pairs) -> list:
    """All keys consistent with the pairs, by brute force.

    FOR THEORY AND VERIFICATION ONLY (it gives M, the number of solutions, for the
    sine-squared curve). The quantum circuit never receives this list.
    """
    return [k for k in range(NUM_KEYS) if consistent(k, pairs)]
