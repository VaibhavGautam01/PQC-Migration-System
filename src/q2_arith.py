"""
q2_arith.py
-----------
Q2, building blocks for gate-level Shor (Beauregard, 2n+3 qubits):
  * QFT and inverse QFT
  * Draper QFT adder (phi_add): adds a constant a to a register in Fourier space
  * Beauregard modular adder: (b + a) mod N, optionally controlled

Everything is built from real gates (H, controlled-phase, CNOT, X, SWAP).
No order-finding, factoring or key-search helpers are used (rule 8).
Qubit order: register[0] is the least significant bit.
Aer simulator, toy size.
"""

import math


def qft_gates(qc, qubits):
    """Append the QFT (little-endian, with swaps) on `qubits`."""
    n = len(qubits)
    for j in reversed(range(n)):
        qc.h(qubits[j])
        for m in reversed(range(j)):
            qc.cp(math.pi / 2 ** (j - m), qubits[m], qubits[j])
    for i in range(n // 2):
        qc.swap(qubits[i], qubits[n - i - 1])


def qft_dagger_gates(qc, qubits):
    """Append the inverse QFT on `qubits` (exact inverse of qft_gates)."""
    n = len(qubits)
    for i in range(n // 2):
        qc.swap(qubits[i], qubits[n - i - 1])
    for j in range(n):
        for m in range(j):
            qc.cp(-math.pi / 2 ** (j - m), qubits[m], qubits[j])
        qc.h(qubits[j])


def phi_add(qc, qubits, a, controls=(), sign=+1):
    """Add (sign=+1) or subtract (sign=-1) the constant a, in Fourier space.

    `qubits` must already be in the Fourier basis (after qft_gates). The sum
    is taken mod 2**len(qubits). If `controls` is given, the addition only
    happens when every control qubit is 1.
    """
    m = len(qubits)
    a %= 2 ** m
    for k, q in enumerate(qubits):
        angle = sign * 2 * math.pi * a / 2 ** (m - k)
        if controls:
            qc.mcp(angle, list(controls), q)
        else:
            qc.p(angle, q)


def modular_adder_phi(qc, b, anc, a, N, controls=()):
    """Beauregard modular adder, in Fourier space.

    b: n+1 qubits (LSB first, top qubit is the overflow bit) holding a value
       0 <= b < N, already in the Fourier basis.
    anc: one ancilla qubit, must start at 0 and is returned to 0.
    Computes b -> (b + a) mod N if all `controls` are 1, else leaves b alone.
    Requires 0 <= a < N and N < 2**(len(b) - 1).
    """
    if not (0 <= a < N):
        raise ValueError("need 0 <= a < N")
    if N >= 2 ** (len(b) - 1):
        raise ValueError("register b needs n+1 qubits with N < 2**n")
    msb = b[-1]
    phi_add(qc, b, a, controls)
    phi_add(qc, b, N, sign=-1)
    qft_dagger_gates(qc, b)
    qc.cx(msb, anc)
    qft_gates(qc, b)
    phi_add(qc, b, N, controls=[anc])
    phi_add(qc, b, a, controls, sign=-1)
    qft_dagger_gates(qc, b)
    qc.x(msb)
    qc.cx(msb, anc)
    qc.x(msb)
    qft_gates(qc, b)
    phi_add(qc, b, a, controls)