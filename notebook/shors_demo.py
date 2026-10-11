"""
shor_demo.py
------------
Circuit SKELETON for Shor's algorithm, factoring N = 15 with a = 7.

Status (Week 1, Day 4): the circuit is BUILT and printed, but NOT yet
executed on the simulator. Running it comes in Week 2.

Registers:
    counting register : N_COUNT qubits (phase estimation, measured)
    work register     : 4 qubits (holds a^x mod 15, starts at |1>)
"""

import math
import sys
import argparse
from fractions import Fraction

import numpy as np
from qiskit.circuit.library import UnitaryGate

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

# Windows consoles often default to cp1252, which can't print Qiskit's
# box-drawing characters. Force UTF-8 so circuit.draw() works everywhere.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


N = 15
A = 7           # must be coprime to N; the period of 7^x mod 15 is 4
N_COUNT = 4     # counting qubits (4 is enough for N = 15, a = 7)
N_WORK = 4      # 4 qubits can represent values 0..15


def c_amod15(a: int, power: int):
    """Return a controlled gate that multiplies the work register by a^power mod 15.

    For N = 15 the multiplication is a fixed pattern of SWAP and X gates.
    Only the values of a coprime to 15 are supported.
    """
    if a not in (2, 4, 7, 8, 11, 13):
        raise ValueError("a must be one of 2, 4, 7, 8, 11, 13 (coprime to 15)")

    u = QuantumCircuit(N_WORK)
    for _ in range(power):
        if a in (2, 13):
            u.swap(2, 3)
            u.swap(1, 2)
            u.swap(0, 1)
        if a in (7, 8):
            u.swap(0, 1)
            u.swap(1, 2)
            u.swap(2, 3)
        if a in (4, 11):
            u.swap(1, 3)
            u.swap(0, 2)
        if a in (7, 11, 13):
            for q in range(N_WORK):
                u.x(q)

    gate = u.to_gate()
    gate.name = f"{a}^{power} mod {N}"
    return gate.control()


def qft_dagger(n: int):
    """Return the inverse Quantum Fourier Transform on n qubits as a gate."""
    qc = QuantumCircuit(n)
    for qubit in range(n // 2):
        qc.swap(qubit, n - qubit - 1)
    for j in range(n):
        for m in range(j):
            qc.cp(-math.pi / float(2 ** (j - m)), m, j)
        qc.h(j)
    qc.name = "QFT_dagger"
    return qc.to_gate()


def build_shor_circuit(a: int = A, n_count: int = N_COUNT) -> QuantumCircuit:
    """Build (but do not run) the Shor's order-finding circuit for N = 15."""
    if math.gcd(a, N) != 1:
        raise ValueError(f"a={a} shares a factor with N={N}; the factors are already known")

    qc = QuantumCircuit(n_count + N_WORK, n_count)

    # 1. Superposition on the counting register
    for q in range(n_count):
        qc.h(q)

    # 2. Work register starts as |1>
    qc.x(n_count)

    # 3. Controlled modular multiplications: qubit k controls a^(2^k) mod N
    work_qubits = list(range(n_count, n_count + N_WORK))
    for q in range(n_count):
        qc.append(c_amod15(a, 2 ** q), [q] + work_qubits)

    # 4. Inverse QFT on the counting register
    qc.append(qft_dagger(n_count), range(n_count))

    # 5. Measure the counting register
    qc.measure(range(n_count), range(n_count))
    return qc

def run_shor_circuit(shots: int = 1024, a: int = A) -> dict:
    """Run the order-finding circuit on the Aer simulator.

    Returns:
        Dict mapping measured bitstrings to counts, e.g. {'0100': 261, ...}.
    """
    circuit = build_shor_circuit(a)
    simulator = AerSimulator()
    compiled = transpile(circuit, simulator)
    result = simulator.run(compiled, shots=shots).result()
    return result.get_counts()

def factors_from_period(r: int, a: int = A, n: int = N):
    """Classical post-processing: turn a guessed period r into factors of n.

    Returns a sorted tuple of the two factors, or None if r is unusable.
    A guessed r is only valid if a^r mod n == 1 (this rejects the
    wrong guesses r = 1 and r = 2 that the unlucky phases produce).
    """
    if r <= 0 or r % 2 != 0 or pow(a, r, n) != 1:
        return None
    x = pow(a, r // 2, n)
    if x == n - 1:                      # a^(r/2) = -1 mod n gives only trivial factors
        return None
    for f in (math.gcd(x - 1, n), math.gcd(x + 1, n)):
        if f not in (1, n):
            return tuple(sorted((f, n // f)))
    return None


def factors_from_bitstring(bitstring: str, a: int = A, n: int = N, n_count: int = N_COUNT):
    """Measured counting-register bitstring -> factors of n (or None)."""
    phase = int(bitstring, 2) / 2 ** n_count
    r = Fraction(phase).limit_denominator(n).denominator
    return factors_from_period(r, a, n)


def run_shor_attempts(n_attempts: int, a: int = A) -> list:
    """Run the circuit n_attempts times; return one bitstring per attempt."""
    circuit = build_shor_circuit(a)
    simulator = AerSimulator()
    compiled = transpile(circuit, simulator)
    result = simulator.run(compiled, shots=n_attempts, memory=True).result()
    return result.get_memory()


# ---------------------------------------------------------------------
# Second case: N = 21  (Week 2, Day 3)
# ---------------------------------------------------------------------
N21 = 21
A21 = 2            # coprime to 21; the period of 2^x mod 21 is 6
N_COUNT21 = 8      # more counting qubits: the period 6 does not divide 2^n
N_WORK21 = 5       # 5 qubits can hold values 0..31, enough for 0..20


def controlled_modmul_gate(multiplier: int, n: int, n_work: int):
    """Return a gate: if the control qubit is 1, work register x -> (multiplier * x) mod n.

    Built as an exact permutation matrix. Values x >= n are left unchanged,
    so the matrix stays unitary. multiplier must be coprime to n.
    Gate qubit order: [control, work_0 (LSB), ..., work_{n_work-1}].
    """
    if math.gcd(multiplier, n) != 1:
        raise ValueError(f"multiplier {multiplier} must be coprime to {n}")
    dim_w = 2 ** n_work
    size = 2 * dim_w
    matrix = np.zeros((size, size))
    for x in range(dim_w):
        y = (multiplier * x) % n if x < n else x
        matrix[2 * x, 2 * x] = 1             # control = 0: identity
        matrix[1 + 2 * y, 1 + 2 * x] = 1     # control = 1: multiply
    return UnitaryGate(matrix, label=f"x{multiplier} mod {n}")


def build_shor_circuit_n21(a: int = A21, n_count: int = N_COUNT21) -> QuantumCircuit:
    """Build the Shor's order-finding circuit for N = 21."""
    if math.gcd(a, N21) != 1:
        raise ValueError(f"a={a} shares a factor with N={N21}")

    qc = QuantumCircuit(n_count + N_WORK21, n_count)
    work_qubits = list(range(n_count, n_count + N_WORK21))

    for q in range(n_count):
        qc.h(q)
    qc.x(work_qubits[0])                     # work register starts as |1>

    for q in range(n_count):                 # qubit q controls a^(2^q) mod N
        multiplier = pow(a, 2 ** q, N21)
        qc.append(controlled_modmul_gate(multiplier, N21, N_WORK21), [q] + work_qubits)

    qc.append(qft_dagger(n_count), range(n_count))
    qc.measure(range(n_count), range(n_count))
    return qc


def run_shor_attempts_n21(n_attempts: int, a: int = A21) -> list:
    """Run the N = 21 circuit; return one measured bitstring per attempt."""
    circuit = build_shor_circuit_n21(a)
    simulator = AerSimulator()
    compiled = transpile(circuit, simulator)
    result = simulator.run(compiled, shots=n_attempts, memory=True).result()
    return result.get_memory()

# ---------------------------------------------------------------------
# Live presentation runner (Week 4, Day 1)
# ---------------------------------------------------------------------
def _banner(text: str) -> None:
    print("\n" + "=" * 64)
    print(text)
    print("=" * 64)


def _pause(enabled: bool) -> None:
    if enabled:
        input("\n   [Press Enter to continue]")


def classical_period(a: int, n: int):
    """Brute-force the period of a^x mod n. Returns (r, sequence)."""
    seq, x = [1], 1
    for r in range(1, n + 1):
        x = (x * a) % n
        seq.append(x)
        if x == 1:
            return r, seq
    return None, seq


def demo_case(n, a, n_count, n_work, runner, expected, shots, pause):
    """Run one narrated Shor's demo. Returns True if the factors were found."""
    _banner(f"SHOR'S ALGORITHM DEMO: factor N = {n}")

    # Step 1
    print(f"\nSTEP 1: choose a number a that shares no factor with N")
    print(f"   N = {n}, a = {a}, gcd(a, N) = {math.gcd(a, n)}  (1 means they are coprime)")
    _pause(pause)

    # Step 2
    r_true, seq = classical_period(a, n)
    print(f"\nSTEP 2: the secret is the PERIOD r of  a^x mod N")
    print(f"   {a}^x mod {n} for x = 0, 1, 2, ...  ->  {', '.join(map(str, seq))}")
    print(f"   The sequence repeats after r = {r_true} steps.")
    print("   A classical computer must search for r; Shor's finds it quickly.")
    _pause(pause)

    # Step 3
    print(f"\nSTEP 3: build the quantum circuit")
    print(f"   Counting register : {n_count} qubits (measured at the end)")
    print(f"   Work register     : {n_work} qubits (holds a^x mod N)")
    print(f"   Total qubits      : {n_count + n_work}")
    _pause(pause)

    # Step 4
    print(f"\nSTEP 4: run on the Aer simulator ({shots} shots)...")
    attempts = runner(shots)
    tally = {}
    for b in attempts:
        tally[b] = tally.get(b, 0) + 1
    print("   Done.")
    _pause(pause)

    # Step 5
    print(f"\nSTEP 5: read the measured phases (top outcomes)")
    print(f"   {'Bitstring':<{n_count + 2}}{'Count':>7}{'Phase':>8}{'r guess':>9}   Factors")
    print("   " + "-" * (n_count + 36))
    for b, c in sorted(tally.items(), key=lambda kv: -kv[1])[:6]:
        phase = int(b, 2) / 2 ** n_count
        r_guess = Fraction(phase).limit_denominator(n).denominator
        f = factors_from_bitstring(b, a, n, n_count)
        print(f"   {b:<{n_count + 2}}{c:>7}{phase:>8.3f}{r_guess:>9}   {f if f else 'none (unlucky)'}")
    print("   Some outcomes give a wrong period. That is normal: Shor's is probabilistic.")
    _pause(pause)

    # Step 6
    winners = [b for b, _ in sorted(tally.items(), key=lambda kv: -kv[1])
               if factors_from_bitstring(b, a, n, n_count) == expected]
    results = [factors_from_bitstring(b, a, n, n_count) for b in attempts]
    successes = sum(r == expected for r in results)

    print(f"\nSTEP 6: turn one good measurement into the factors")
    if winners:
        b = winners[0]
        phase = int(b, 2) / 2 ** n_count
        r = Fraction(phase).limit_denominator(n).denominator
        x = pow(a, r // 2, n)
        print(f"   Measured {b} -> phase {phase:.3f} -> period r = {r}")
        print(f"   x = {a}^({r}/2) mod {n} = {x}")
        print(f"   gcd(x - 1, N) = gcd({x - 1}, {n}) = {math.gcd(x - 1, n)}")
        print(f"   gcd(x + 1, N) = gcd({x + 1}, {n}) = {math.gcd(x + 1, n)}")
    else:
        print("   No successful outcome this time. Run again (it is random).")
    _pause(pause)

    # Result
    _banner("RESULT")
    print(f"   Success rate: {successes}/{shots} = {successes / shots:.0%} of shots found the factors")
    ok = bool(winners) and set(results) <= {None, expected}
    if ok:
        p, q = expected
        print(f"   {n} = {p} x {q}   (check: {p} * {q} = {p * q})")
        print("   [PASS]")
    else:
        print("   [FAIL] Unexpected result. Do not present; investigate.")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Narrated Shor's algorithm demo")
    parser.add_argument("--case", choices=["15", "21", "both"], default="both")
    parser.add_argument("--shots", type=int, default=1024)
    parser.add_argument("--pause", action="store_true",
                        help="wait for Enter between steps (for live presentation)")
    args = parser.parse_args()

    _banner("PQC MIGRATION ADVISOR: Shor's algorithm on a quantum simulator")
    print("Shor's algorithm factors the number inside an RSA key.")
    print("Here we use tiny numbers so a laptop can simulate it.")
    print("Real RSA-2048 needs thousands of logical qubits (see risk report).")
    _pause(args.pause)

    ok = True
    if args.case in ("15", "both"):
        ok &= demo_case(N, A, N_COUNT, N_WORK,
                        lambda s: run_shor_attempts(s), (3, 5), args.shots, args.pause)
    if args.case in ("21", "both"):
        ok &= demo_case(N21, A21, N_COUNT21, N_WORK21,
                        lambda s: run_shor_attempts_n21(s), (3, 7), args.shots, args.pause)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())