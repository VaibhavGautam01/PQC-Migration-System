"""
q2_shor.py
----------
Q2: gate-level Shor order finding (Beauregard, 2n+3 qubits) with iterative
phase estimation: ONE control qubit, mid-circuit measurement, reset and
classically controlled phase corrections.

Registers (n = N.bit_length()):
    x    n qubits   starts as |1>, holds a^k mod N
    b    n+1 qubits helper for the multiplier (returned to 0 each iteration)
    anc  1 qubit    ancilla of the modular adder
    c    1 qubit    the single phase-estimation control qubit
Total 2n + 3 qubits. Classical bits: m = 2n, bit t holds the t-th measured
phase bit, so the integer read from the counts is y = phi * 2**m.

This module builds the circuit only. It never computes the period, the
factors or any search (rule 8); gates are NOT skipped when a multiplier
happens to equal 1, because skipping would leak information about the order.
Post-processing (continued fractions, gcd) lives in q2_shor_run.py.
Aer simulator, toy size.
"""
import math

from qiskit import QuantumCircuit

from q2_arith import controlled_modmul


def shor_layout(N: int) -> dict:
    """Qubit indices of each register for modulus N."""
    n = N.bit_length()
    return {"n": n, "x": list(range(n)), "b": list(range(n, 2 * n + 1)),
            "anc": 2 * n + 1, "c": 2 * n + 2, "qubits": 2 * n + 3}


def build_shor_ipea(a: int, N: int, m: int = None) -> QuantumCircuit:
    """Build the order-finding circuit for base a and modulus N (not run here).

    m: number of phase bits (default 2n). Any odd N >= 3 and a coprime to N.
    """
    if N < 3 or N % 2 == 0:
        raise ValueError("N must be an odd number >= 3")
    if math.gcd(a, N) != 1:
        raise ValueError(f"a={a} shares a factor with N={N}")
    lay = shor_layout(N)
    m = 2 * lay["n"] if m is None else m
    if m < 1:
        raise ValueError("m must be at least 1")
    x, b, anc, c = lay["x"], lay["b"], lay["anc"], lay["c"]

    qc = QuantumCircuit(lay["qubits"], m)
    qc.x(x[0])                                   # x = |1>
    for t in range(m):                           # t = 0 measures the least significant phase bit
        qc.h(c)
        controlled_modmul(qc, c, x, b, anc, pow(a, 2 ** (m - 1 - t), N), N)
        for s in range(t):                       # feed-forward correction from earlier bits
            with qc.if_test((qc.clbits[s], 1)):
                qc.p(-2 * math.pi / 2 ** (t - s + 1), c)
        qc.h(c)
        qc.measure(c, t)
        if t < m - 1:
            qc.reset(c)
    return qc