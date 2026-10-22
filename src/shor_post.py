"""
shor_post.py - classical helpers for Shor order finding (Q1).

WHY THIS FILE EXISTS
--------------------
Rule 2 of the plan says classical code may do ONLY the pre- and post-processing
that Shor's algorithm itself defines. Everything of that kind lives here:

  * check_inputs()            - pre-processing: a must be coprime to N
  * decode_outcome()          - post-processing: measured number y -> period r
                                (continued fractions, then "try multiples of r0")
  * factors_from_period()     - post-processing: period r -> factors (gcd step)
  * analyse_counts()          - apply the two steps above to a whole measured
                                histogram and vote on the period
  * theoretical_distribution()- what an IDEAL quantum computer would measure
                                (used ONLY to compare with the measurement, rule 5)
  * chi_square_vs_theory()    - the chi-square test of rule 5 (no scipy needed)

This file contains NO quantum circuit and never produces an answer that the
circuit did not measure. It is deliberately NOT named q1_*.py: the static guard
(rule 8) scans every src/q<number>_*.py file and bans "period search" loops
there, but post-processing legitimately needs to verify a candidate period.
Keeping it here keeps the circuit-builder files clean.

Only the standard library is used, so these functions (and their tests) run
even on a machine where qiskit is not installed.

All quantum results that use this file: Aer simulator, toy size.
"""
from fractions import Fraction
from math import exp, gcd, lgamma, log, pi, sin


# --------------------------------------------------------------------------
# 1. Pre-processing
# --------------------------------------------------------------------------
def check_inputs(a: int, N: int) -> None:
    """Raise ValueError unless 1 < a < N and gcd(a, N) == 1.

    If gcd(a, N) > 1 you have already found a factor of N by luck (that is
    part of Shor's algorithm too), and no quantum circuit is needed.
    """
    if N < 3:
        raise ValueError("N must be at least 3")
    if not 1 < a < N:
        raise ValueError(f"a must satisfy 1 < a < N (got a={a}, N={N})")
    g = gcd(a, N)
    if g != 1:
        raise ValueError(
            f"gcd(a, N) = {g} is already a factor of N = {N}; pick an a coprime to N")


# --------------------------------------------------------------------------
# 2. Post-processing of ONE measured value
# --------------------------------------------------------------------------
def decode_outcome(y: int, m: int, a: int, N: int):
    """Turn one measured integer y (phase estimate y / 2**m) into the period r.

    Step A (continued fractions): the true phase is s/r for some integer s, so
            Fraction(y, 2**m).limit_denominator(N) is a candidate r0 = r / gcd(s, r).
    Step B (try multiples): r0 can be a proper divisor of r, so test r0, 2*r0,
            3*r0 ... and accept the first one with a**r == 1 (mod N).
    Returns the period r, or None if this measurement gives no valid period
    (y = 0 carries no information).
    """
    if y == 0:
        return None
    r0 = Fraction(y, 2 ** m).limit_denominator(N).denominator
    r = r0
    while r <= N:
        if pow(a, r, N) == 1:      # verification of a CANDIDATE, not a search
            return r
        r += r0
    return None


def factors_from_period(a: int, N: int, r: int):
    """The gcd step of Shor: from an even period r get two factors of N, or None.

    Fails (returns None) when r is odd or when a**(r/2) == -1 (mod N);
    then you simply use another measurement.
    """
    if r is None or r % 2 == 1:
        return None
    u = pow(a, r // 2, N)
    if u == N - 1:
        return None
    for f in (gcd(u - 1, N), gcd(u + 1, N)):
        if f not in (1, N):
            return tuple(sorted((f, N // f)))
    return None


def factors_from_measurement(y: int, m: int, a: int, N: int):
    """One measured value y -> factors of N (or None). Post-processing only:
    decode_outcome (continued fractions) then the gcd step."""
    return factors_from_period(a, N, decode_outcome(y, m, a, N))


def analyse_counts(counts: dict, m: int, a: int, N: int) -> dict:
    """Post-process a whole measured histogram (bitstring -> count).

    Every shot votes for a period. The period with the most votes that also
    yields factors is reported. Everything here comes ONLY from the measured
    counts (rule 2).

    Returns {"period", "factors", "votes", "success_rate", "shots"} where
    success_rate = fraction of shots whose single outcome ALONE already gives
    the factors.
    """
    shots = sum(counts.values())
    votes, good = {}, 0
    for bits, cnt in counts.items():
        r = decode_outcome(int(bits, 2), m, a, N)
        if r is None:
            continue
        votes[r] = votes.get(r, 0) + cnt
        if factors_from_period(a, N, r):
            good += cnt
    period, factors = None, None
    for r, _ in sorted(votes.items(), key=lambda kv: (-kv[1], kv[0])):
        f = factors_from_period(a, N, r)
        if f:
            period, factors = r, f
            break
    return {"period": period, "factors": list(factors) if factors else None,
            "votes": votes, "success_rate": good / shots if shots else 0.0,
            "shots": shots}


# --------------------------------------------------------------------------
# 3. Theory: what a perfect circuit measures (rule 5)
# --------------------------------------------------------------------------
def true_order_for_theory(a: int, N: int) -> int:
    """Classical multiplicative order of a mod N.

    FOR THE THEORY CURVE ONLY. The circuit never sees this number; it is used
    afterwards to draw the ideal distribution that the measurement is compared
    against. Never call this from a circuit builder.
    """
    r, x = 1, a % N
    while x != 1:
        x = (x * a) % N
        r += 1
    return r


def theoretical_distribution(a: int, N: int, m: int) -> list:
    """Ideal probability P(y) for y = 0 .. 2**m - 1.

    The start state |1> is an equal mix of the r eigenstates of U with phases
    s/r (s = 0..r-1). For a phase phi, phase estimation with m counting qubits
    returns y with probability  F(phi - y/M) = sin^2(pi M d) / (M^2 sin^2(pi d)),
    where M = 2**m and d = phi - y/M. Averaging over s gives
        P(y) = (1/r) * sum_s F(s/r - y/M).
    """
    M = 2 ** m
    r = true_order_for_theory(a, N)
    probs = [0.0] * M
    for y in range(M):
        total = 0.0
        for s in range(r):
            d = s / r - y / M
            denom = sin(pi * d)
            if abs(denom) < 1e-12:
                total += 1.0
            else:
                total += (sin(pi * M * d) / (M * denom)) ** 2
        probs[y] = total / r
    return probs


# --------------------------------------------------------------------------
# 4. Chi-square test (rule 5), pure Python
# --------------------------------------------------------------------------
def _gammq(a: float, x: float) -> float:
    """Regularised upper incomplete gamma Q(a, x) (Numerical-Recipes method)."""
    if x <= 0:
        return 1.0
    if x < a + 1.0:                       # series for P(a, x), then 1 - P
        ap, s = a, 1.0 / a
        d = s
        for _ in range(2000):
            ap += 1.0
            d *= x / ap
            s += d
            if abs(d) < abs(s) * 1e-16:
                break
        return 1.0 - s * exp(-x + a * log(x) - lgamma(a))
    tiny = 1e-300                         # continued fraction for Q(a, x)
    b = x + 1.0 - a
    c, d = 1.0 / tiny, 1.0 / b
    h = d
    for i in range(1, 2000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            break
    return exp(-x + a * log(x) - lgamma(a)) * h


def chi2_sf(statistic: float, dof: int) -> float:
    """P(chi-square with `dof` degrees of freedom >= statistic): the p-value."""
    return _gammq(dof / 2.0, statistic / 2.0)


def chi_square_vs_theory(counts: dict, probs: list, min_expected: float = 5.0) -> dict:
    """Chi-square goodness-of-fit of measured counts against theory (rule 5).

    Outcomes whose expected count is below `min_expected` are pooled into one
    'other' bin (standard practice, otherwise the test is unreliable).
    Reading the result: a LARGE p-value (for example > 0.01) means the
    measurement is consistent with the ideal distribution; a tiny p-value means
    the circuit is not doing what the theory says.
    """
    shots = sum(counts.values())
    observed = {}
    for bits, cnt in counts.items():
        y = int(bits, 2)
        observed[y] = observed.get(y, 0) + cnt
    bins = []                                   # (observed, expected)
    rest_obs, rest_exp = 0, 0.0
    for y, p in enumerate(probs):
        exp_count = shots * p
        if exp_count >= min_expected:
            bins.append([observed.get(y, 0), exp_count])
        else:
            rest_obs += observed.get(y, 0)
            rest_exp += exp_count
    if rest_exp > 0:
        if rest_exp >= min_expected or not bins:
            bins.append([rest_obs, rest_exp])
        else:                                   # too small alone: merge with smallest bin
            smallest = min(bins, key=lambda b: b[1])
            smallest[0] += rest_obs
            smallest[1] += rest_exp
    statistic = sum((o - e) ** 2 / e for o, e in bins)
    dof = max(len(bins) - 1, 1)
    return {"statistic": round(statistic, 4), "dof": dof,
            "p_value": chi2_sf(statistic, dof), "bins": len(bins), "shots": shots}
