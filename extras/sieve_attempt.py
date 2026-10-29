"""
sieve_attempt.py - the stretch goal (Week 4 Day 2): try a classical factoring tool against the
pinned project's real 256-bit (or 512-bit) RSA key.

WHAT THIS IS, HONESTLY
-----------------------
This is NOT a quantum attack and NOT a general number field sieve (writing a real GNFS is a
multi-year engineering effort, far beyond a stretch goal). It is two well-known, genuinely
useful CLASSICAL factoring techniques, run with a strict time budget:
  * Pollard's rho           fast when N has a small-ish factor; O(N^(1/4)) expected time
  * Pollard's p-1           fast when N has a factor p where p-1 is "smooth" (only small
                            prime powers divide it) - a real weakness some RSA key generators
                            have had historically
Neither is expected to factor a genuinely random 256-bit RSA modulus in any reasonable time -
that is exactly the point of RSA. Running this and reporting "not completed" IS the correct,
honest result for a well-generated key, per the plan's own risk table: "If not done, the
report says so and quotes no time" - this script instead quotes the time it DID spend, which
is more informative than silence.

Usage (from the project root, venv active):
  python extras/sieve_attempt.py --n <the pinned project's real modulus, as a decimal integer>
  python extras/sieve_attempt.py --n <modulus> --budget-seconds 120
  python extras/sieve_attempt.py --project data/targets/final-year-part1 --budget-seconds 120
                                   # reads the modulus out of the pinned project, if it exposes one
  python extras/sieve_attempt.py --self-test             # quick correctness check on small composites

HOW TO GET THE REAL N
-----------------------
The pinned project's real 256-bit or 512-bit modulus is wherever its RSA key generation code
stores it (e.g. a saved key file, or a constant in its key-generation module) - this script
does not know that location, so pass --n directly, or point --project at a module that exposes
the public modulus and adapt load_modulus_from_project() below to read it.
"""
import argparse
import json
import math
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL_NAME = "sieve_attempt.py (Pollard's rho + Pollard's p-1)"
TOOL_VERSION = "1.0 (this project, not a third-party library)"


def pollards_rho(n: int, deadline: float, seed: int = 0) -> int | None:
    """Pollard's rho factoring. Returns a non-trivial factor, or None if not found by `deadline`."""
    if n % 2 == 0:
        return 2
    rng = random.Random(seed)
    while time.perf_counter() < deadline:
        c = rng.randrange(1, n - 1)
        x = y = rng.randrange(2, n - 1)
        d = 1
        while d == 1:
            if time.perf_counter() >= deadline:
                return None
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = math.gcd(abs(x - y), n)
        if 1 < d < n:
            return d
        # d == n: this (c, start) pair failed; try another
    return None


def pollards_p_minus_1(n: int, deadline: float, bound: int = 200_000) -> int | None:
    """Pollard's p-1 factoring: finds p if p-1 is `bound`-smooth. Returns a factor or None."""
    a = 2
    for prime_power in _smooth_exponents(bound):
        if time.perf_counter() >= deadline:
            return None
        a = pow(a, prime_power, n)
        d = math.gcd(a - 1, n)
        if 1 < d < n:
            return d
        if d == n:
            return None               # bound too large for this n; a smaller bound might work
    return None


def _smooth_exponents(bound: int):
    """Prime powers <= bound, via a simple sieve (good enough for a stretch-goal tool)."""
    sieve = bytearray([1]) * (bound + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(bound ** 0.5) + 1):
        if sieve[i]:
            for j in range(i * i, bound + 1, i):
                sieve[j] = 0
    for i, is_prime in enumerate(sieve):
        if not is_prime:
            continue
        power = i
        while power * i <= bound:
            power *= i
        yield power


def attempt(n: int, budget_seconds: float) -> dict:
    """Run both tools against n, sharing the time budget. Returns a result dict."""
    t0 = time.perf_counter()
    deadline = t0 + budget_seconds
    half_deadline = t0 + budget_seconds / 2

    factor = pollards_p_minus_1(n, half_deadline)
    tool_used = "Pollard's p-1"
    if factor is None:
        factor = pollards_rho(n, deadline)
        tool_used = "Pollard's rho" if factor else "both tried"
    elapsed = time.perf_counter() - t0

    if factor:
        other = n // factor
        return {"completed": True, "factors": [factor, other], "tool": tool_used,
               "elapsed_seconds": round(elapsed, 3), "budget_seconds": budget_seconds}
    return {"completed": False, "factors": None, "tool": "Pollard's p-1 then Pollard's rho "
           "(both tried, neither found a factor)", "elapsed_seconds": round(elapsed, 3),
           "budget_seconds": budget_seconds}


def load_modulus_from_project(project_dir: str) -> int:
    """Try to read the pinned project's real public modulus. ADAPT THIS to the project's actual
    key-storage format; raises NotImplementedError until someone fills it in, so this script
    never silently reports a fake N."""
    raise NotImplementedError(
        "load_modulus_from_project() does not know this project's key file format yet. "
        "Pass --n <the real modulus as a decimal integer> directly instead, or edit this "
        "function once you know where the pinned project stores its public key.")


def self_test() -> int:
    """A quick correctness check on small composites (seconds, not the real stretch goal)."""
    cases = [91, 3233, 589 * 617]            # 7x13, 61x53, two more primes
    print("=== sieve_attempt.py self-test (small composites, NOT the real 256-bit goal) ===")
    ok = True
    for n in cases:
        result = attempt(n, budget_seconds=5)
        good = result["completed"] and result["factors"][0] * result["factors"][1] == n
        ok &= good
        print(f"N={n}: {'PASS' if good else 'FAIL'} - {result}")
    print("\nSELF-TEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, help="the modulus to attempt (decimal integer)")
    ap.add_argument("--project", help="pinned project folder (needs load_modulus_from_project "
                    "adapted to its key format first)")
    ap.add_argument("--budget-seconds", type=float, default=120,
                    help="stop and report 'not completed' after this many seconds (default 120)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--json", help="also write the result to this JSON file")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.n is None and args.project is None:
        ap.error("give --n <modulus>, or --project <pinned project folder>, or --self-test")

    try:
        n = args.n if args.n is not None else load_modulus_from_project(args.project)
    except NotImplementedError as exc:
        print(f"Cannot get N automatically: {exc}")
        return 2

    print(f"Tool: {TOOL_NAME}\nVersion: {TOOL_VERSION}\nN ({n.bit_length()} bits): {n}\n"
         f"Time budget: {args.budget_seconds} s\n")
    result = attempt(n, args.budget_seconds)
    result.update({"tool_name": TOOL_NAME, "tool_version": TOOL_VERSION, "n_bits": n.bit_length()})

    if result["completed"]:
        p, q = result["factors"]
        print(f"COMPLETED: factored in {result['elapsed_seconds']} s using {result['tool']}.")
        print(f"  N = {p} x {q}")
        print(f"  check: p * q == N -> {p * q == n}")
    else:
        print(f"NOT COMPLETED: {result['tool']}; ran for {result['elapsed_seconds']} s "
             f"(budget was {args.budget_seconds} s) with no factor found.")
        print("This is the expected, honest result for a well-generated RSA key at this size - "
             "report it exactly as 'not completed', with the tool, version and time above, "
             "per the plan's risk-table rule for this stretch goal.")

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {out}")
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
