"""Simple randomness tests (monobit, runs, byte chi-square), pure Python.

The chi-square p-value uses the Wilson-Hilferty approximation. These tests can fail good data about
as often as their p-value threshold says, and passing them does NOT prove the data is secure.
"""
import math


def bits_from_bytes(data):
    return [(byte >> (7 - j)) & 1 for byte in data for j in range(8)]


def monobit_p(bits):
    n = len(bits)
    s = abs(sum(2 * b - 1 for b in bits)) / math.sqrt(n)
    return math.erfc(s / math.sqrt(2))


def runs_p(bits):
    n = len(bits)
    pi = sum(bits) / n
    if abs(pi - 0.5) >= 2 / math.sqrt(n):
        return 0.0
    v = 1 + sum(bits[i] != bits[i + 1] for i in range(n - 1))
    return math.erfc(abs(v - 2 * n * pi * (1 - pi)) / (2 * math.sqrt(2 * n) * pi * (1 - pi)))


def byte_chi2(bits):
    """Return (chi2, approximate p) for the byte histogram. Needs at least 1280 bytes."""
    nbytes = len(bits) // 8
    if nbytes < 1280:
        raise ValueError("need at least 1280 bytes (10240 bits) for the chi-square test")
    counts = [0] * 256
    for i in range(nbytes):
        counts[int("".join(map(str, bits[i * 8:i * 8 + 8])), 2)] += 1
    expected = nbytes / 256
    chi2 = sum((c - expected) ** 2 / expected for c in counts)
    df = 255
    z = ((chi2 / df) ** (1 / 3) - (1 - 2 / (9 * df))) / math.sqrt(2 / (9 * df))
    return chi2, 0.5 * math.erfc(z / math.sqrt(2))