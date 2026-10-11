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
from fractions import Fraction

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

if __name__ == "__main__":
    SHOTS = 1024

    circuit = build_shor_circuit()
    print(f"Shor's circuit: N={N}, a={A}")
    print(f"Qubits: {circuit.num_qubits}  |  Classical bits: {circuit.num_clbits}")

    print(f"\nRunning on AerSimulator ({SHOTS} shots)...")
    counts = run_shor_circuit(SHOTS)

    print(f"\n{'Bitstring':<10}{'Decimal':>8}{'Count':>8}{'Phase':>8}  Guessed period r")
    print("-" * 56)
    for bitstring, count in sorted(counts.items()):
        decimal = int(bitstring, 2)
        phase = decimal / 2 ** N_COUNT
        guess_r = Fraction(phase).limit_denominator(N).denominator
        print(f"{bitstring:<10}{decimal:>8}{count:>8}{phase:>8.2f}  {guess_r}")

    # Checks
    assert sum(counts.values()) == SHOTS, "Shot count mismatch"
    # The true period is 4, which divides 2^4 = 16, so an ideal simulation
    # can only produce phases 0, 1/4, 1/2 and 3/4 (decimals 0, 4, 8, 12).
    assert {int(b, 2) for b in counts} <= {0, 4, 8, 12}, "Unexpected outcomes"
    print("\n[PASS] Circuit executed on the simulator; phases match period r = 4.")

        # Day 2: classical post-processing
    print("\nFactor extraction from each measured outcome:")
    for bitstring in sorted(counts):
        print(f"  {bitstring} -> {factors_from_bitstring(bitstring)}")
