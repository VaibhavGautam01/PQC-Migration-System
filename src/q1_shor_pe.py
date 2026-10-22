"""
q1_shor_pe.py - Q1: Shor order finding by quantum phase estimation.

WHAT THIS BUILDS
----------------
A real quantum circuit that finds the period r of  f(x) = a**x mod N  for
N = 15, 21, 35 (any small N works - nothing here is hard-coded to one N).

    counting register (m qubits)  |0..0> --H--*---*---*-- ... --[inverse QFT]--measure
                                              |   |   |
    work register (n qubits)      |0..01> ---U---U^2-U^4-- ...      (U|x> = |a*x mod N>)

  1. Put the work register in |1>.
  2. Put every counting qubit in superposition with a Hadamard gate.
  3. Counting qubit j controls U^(2**j). U^(2**j) multiplies the work register
     by (a**(2**j) mod N).  This "kicks back" a phase onto the counting qubits.
  4. The inverse QFT turns that phase into a number y with y / 2**m close to s / r.
  5. Measure the counting register. Classical code (shor_post.py) turns y into
     r with continued fractions, then into factors with gcd.

HONEST LIMITS (say these in the viva)
-------------------------------------
* U is built as a dense matrix on a classical computer from pow(a, x, N).
  That is the "oracle the algorithm is given" (rule 8 allows it), but it does
  NOT scale: this file proves the algorithm is correct, not that it is cheap.
  Resource counts (Q4) must use the Q2 gate-level circuits, NOT these circuits.
* The period is never computed here. It exists only as a measured histogram.
* Aer simulator, toy size.

STATIC GUARD (rule 8)
---------------------
This file is scanned by src/quantum_guard.py. It must not import sympy, call
order-finding / factoring helpers, or loop over candidate periods.
pow(a, 2**j, N) is allowed: it only builds the oracle.
"""
from math import gcd, pi

import numpy as np
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import UnitaryGate


def default_counting_bits(N: int) -> int:
    """2n counting qubits give enough precision for continued fractions (n = bits of N)."""
    return 2 * N.bit_length()


def controlled_modmul_matrix(multiplier: int, N: int, n: int) -> np.ndarray:
    """Matrix of 'controlled multiply by `multiplier` mod N' on 1 + n qubits.

    Qiskit is little-endian, so with qubit order [control, work0, work1, ...]
    the basis state number is  i = control + 2 * x  (x = value of work register).

      control = 0 : nothing happens
      control = 1 : x -> (multiplier * x) mod N        (only for x < N)
      x >= N      : left alone (these states are never reached from |1>,
                    but this keeps the matrix a valid permutation = unitary)
    """
    dim = 2 ** (n + 1)
    matrix = np.zeros((dim, dim), dtype=complex)
    for c in (0, 1):
        for x in range(2 ** n):
            new_x = (multiplier * x) % N if (c == 1 and x < N) else x
            matrix[c + 2 * new_x, c + 2 * x] = 1.0
    return matrix


def inverse_qft_ops(m: int) -> list:
    """Gate list of the inverse QFT on m qubits (qubit 0 = least significant).

    This is Qiskit's QFT circuit (with its final swaps) run backwards with
    negated angles. Written as plain data so a test can check it against the
    inverse discrete Fourier transform without needing qiskit.
    Entries: ("swap", i, j), ("cp", angle, control, target), ("h", qubit).
    """
    ops = []
    for i in range(m // 2):                         # undo the bit-reversal first
        ops.append(("swap", i, m - 1 - i))
    for j in range(m):
        for k in range(j):                          # controlled phase rotations
            ops.append(("cp", -pi / 2 ** (j - k), k, j))
        ops.append(("h", j))
    return ops


def apply_inverse_qft(qc: QuantumCircuit, qubits: list) -> None:
    """Append the inverse QFT, gate by gate, to qc on the given qubits."""
    for op in inverse_qft_ops(len(qubits)):
        if op[0] == "swap":
            qc.swap(qubits[op[1]], qubits[op[2]])
        elif op[0] == "cp":
            qc.cp(op[1], qubits[op[2]], qubits[op[3]])
        else:
            qc.h(qubits[op[1]])


def build_shor_pe(a: int, N: int, m: int = None, measure: bool = True) -> QuantumCircuit:
    """Build the phase-estimation circuit for the order of a mod N.

    a, N    : the question. Change them and the SAME code answers a new question
              (rule 6, change-the-question).
    m       : number of counting qubits (default 2 * bits(N)).
    measure : False gives a circuit without measurements, used only for the exact
              statevector cross-check (rule 9).
    """
    if not 1 < a < N or gcd(a, N) != 1:
        raise ValueError(f"need 1 < a < N and gcd(a, N) = 1 (got a={a}, N={N})")
    n = N.bit_length()
    m = default_counting_bits(N) if m is None else m

    counting = QuantumRegister(m, "cnt")
    work = QuantumRegister(n, "wrk")
    qc = QuantumCircuit(counting, work, name=f"shor_pe_N{N}_a{a}")
    if measure:
        result_bits = ClassicalRegister(m, "y")
        qc.add_register(result_bits)

    qc.x(work[0])                                   # step 1: work register = |1>
    qc.h(counting)                                  # step 2: superposition

    for j in range(m):                              # step 3: controlled-U^(2**j)
        multiplier = pow(a, 2 ** j, N)              # oracle input, allowed by rule 8
        gate = UnitaryGate(controlled_modmul_matrix(multiplier, N, n),
                           label=f"C-U^(2^{j}) x{multiplier} mod {N}")
        qc.append(gate, [counting[j]] + list(work))

    apply_inverse_qft(qc, list(counting))           # step 4: phase -> number

    if measure:                                     # step 5: read the counting register
        qc.measure(counting, result_bits)
    return qc
