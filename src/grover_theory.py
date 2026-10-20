"""
grover_theory.py - what an IDEAL Grover search predicts (rule 5). Standard library only.

Used AFTER a run, to compare the measured histogram with theory. The circuit never sees these
numbers (q3_grover.py does not import this file).

With N = 256 keys of which M match the known pairs, let theta = asin(sqrt(M / N)).
After k rounds the chance of measuring a matching key is  sin^2((2k + 1) * theta).
Every matching key is equally likely, and so is every non-matching key.
"""
from math import asin, floor, pi, sin, sqrt


def theta(M: int, N: int) -> float:
    """Grover rotation angle for M marked items among N."""
    return asin(sqrt(M / N))


def success_probability(k: int, M: int, N: int) -> float:
    """Probability of measuring SOME matching key after k Grover rounds."""
    return sin((2 * k + 1) * theta(M, N)) ** 2


def optimal_iterations(M: int, N: int) -> int:
    """Number of rounds that maximises the success probability (about pi/4 * sqrt(N/M))."""
    return floor(pi / (4 * theta(M, N)))


def expected_distribution(k: int, marked_keys, N: int) -> list:
    """Ideal probability of every key value 0..N-1 after k rounds."""
    marked = set(marked_keys)
    M = len(marked)
    p = success_probability(k, M, N)
    return [p / M if key in marked else (1 - p) / (N - M) for key in range(N)]
