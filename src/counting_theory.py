"""
counting_theory.py - classical helpers for Q11 (quantum counting). Standard library only.

Two jobs, both done OUTSIDE the quantum circuit:

1. MAKE THE QUESTION. find_pair_with_matches() builds a known (plaintext, ciphertext) pair
   for which a chosen number M of keys fit. The attacker sees only the pair; the circuit is
   never told M. (M is also what the theory curve and the final check need.)
2. READ THE ANSWER. estimate_count() turns the measured counting-register histogram into an
   estimate of M, and counting_distribution() gives the ideal histogram to compare it with.

THE MATHS in two lines
----------------------
Grover's iterate G rotates by 2*theta where sin^2(theta) = M / N (N = number of candidate keys).
Phase estimation on G measures y / 2^t close to theta / pi (or 1 - theta/pi), so
        M is about N * sin^2(pi * y / 2^t).
With t counting qubits the answer is only as sharp as 2^-t: small counts need t large enough.

Nothing here is imported by the circuit builder (q11_counting.py); a test checks that.
"""
from collections import Counter
from math import asin, floor, log, pi, sin, sqrt

from src import toy_cipher as T


def matching_free_keys(pair, free_bits: int, known_value: int) -> list:
    """Free key parts (low `free_bits` bits) that, with the known high bits, encrypt P to C.

    Brute force: for making instances, theory and verification ONLY.
    """
    plaintext, ciphertext = pair
    return [k for k in range(2 ** free_bits)
            if T.encrypt((known_value << free_bits) | k, plaintext) == ciphertext]


def find_pair_with_matches(M: int, free_bits: int, known_value: int = 0):
    """First (plaintext, ciphertext) pair (scanning plaintexts 0, 1, 2 ...) that exactly M
    candidate keys fit. Returns None if this toy cipher has no such pair.

    Facts about this toy cipher (measured): with 6 free key bits there are pairs with 1, 2 and
    3 matching keys but none with 4; a 4-way collision exists only for the full 8-bit key.
    """
    for plaintext in range(256):
        outputs = Counter(T.encrypt((known_value << free_bits) | k, plaintext)
                          for k in range(2 ** free_bits))
        for ciphertext in sorted(outputs):
            if outputs[ciphertext] == M:
                return plaintext, ciphertext
    return None


def counting_distribution(M: int, N: int, t: int) -> list:
    """Ideal probability of each counting outcome y = 0 .. 2^t - 1 (needs 1 <= M < N).

    The start state is an equal mix of the two eigenvectors of G, with phases +theta/pi and
    -theta/pi (mod 1). A phase phi gives outcome y with probability
        F(phi - y/T) = sin^2(pi T d) / (T^2 sin^2(pi d)),  d = phi - y/T,  T = 2^t,
    so P(y) = 1/2 * [F(phi - y/T) + F(1 - phi - y/T)].
    """
    T_ = 2 ** t
    phi = asin(sqrt(M / N)) / pi

    def F(d):
        denom = sin(pi * d)
        return 1.0 if abs(denom) < 1e-12 else (sin(pi * T_ * d) / (T_ * denom)) ** 2

    return [0.5 * (F(phi - y / T_) + F(1 - phi - y / T_)) for y in range(T_)]


def count_from_outcome(y: int, N: int, t: int) -> float:
    """The (continuous) count estimate for one measured outcome y."""
    return N * sin(pi * y / 2 ** t) ** 2


def estimate_count(counts: dict, N: int, t: int) -> dict:
    """Estimate M from a measured histogram (bitstring -> count). Uses ONLY the counts.

    The outcomes y and 2^t - y mean the same count, so they are added together before the most
    frequent one is chosen.
    """
    T_ = 2 ** t
    merged = {}
    for bits, c in counts.items():
        y = int(bits, 2)
        key = min(y, (T_ - y) % T_)
        merged[key] = merged.get(key, 0) + c
    peak = max(merged, key=lambda k: (merged[k], -k))
    raw = count_from_outcome(peak, N, t)
    shots = sum(counts.values())
    per_shot = {}
    for bits, c in counts.items():
        m = round(count_from_outcome(int(bits, 2), N, t))
        per_shot[m] = per_shot.get(m, 0) + c
    return {"peak_outcome": peak, "estimate_raw": raw, "estimate": max(1, round(raw)),
            "shots_per_estimate": {str(k): v for k, v in sorted(per_shot.items())},
            "shots": shots}


def iterations_for(M: int, N: int) -> int:
    """Grover rounds for M matching keys among N: floor(pi/4 * sqrt(N / M))."""
    return floor(pi / (4 * asin(sqrt(M / N))))


def estimate_count_ml(counts: dict, N: int, t: int, max_M: int = None) -> dict:
    """Maximum-likelihood estimate of M from a measured histogram. Uses ONLY the counts.

    For every candidate M = 1 .. max_M the ideal counting histogram is computed, and the M whose
    histogram makes the measured counts most likely is chosen. This is sharper than rounding the
    single most frequent outcome (estimate_count), which can be off by one when 2^t is small.
    It is post-processing of measured data, like continued fractions in Shor.
    """
    max_M = min(N - 1, max_M or N // 2)
    best_M, best_ll = 1, None
    for M in range(1, max_M + 1):
        dist = counting_distribution(M, N, t)
        ll = sum(c * log(max(dist[int(bits, 2)], 1e-300)) for bits, c in counts.items())
        if best_ll is None or ll > best_ll:
            best_M, best_ll = M, ll
    return {"estimate": best_M, "log_likelihood": best_ll, "candidates_tested": max_M}
