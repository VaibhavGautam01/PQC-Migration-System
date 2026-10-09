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

from qiskit import QuantumCircuit

# Windows consoles often default to cp1252, which can't print Qiskit's
# box-drawing characters. Force UTF-8 so circuit.draw() works everywhere.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from qiskit import QuantumCircuit

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


if __name__ == "__main__":
    circuit = build_shor_circuit()
    print(f"Shor's circuit skeleton: N={N}, a={A}")
    print(f"Qubits: {circuit.num_qubits}  |  Classical bits: {circuit.num_clbits}")
    print(f"Gate counts: {dict(circuit.count_ops())}")
    print()
    print(circuit.draw("text"))

    # Structural checks only: nothing is executed
    assert circuit.num_qubits == N_COUNT + N_WORK
    assert circuit.num_clbits == N_COUNT
    print("\n[PASS] Circuit built successfully (not executed yet).")