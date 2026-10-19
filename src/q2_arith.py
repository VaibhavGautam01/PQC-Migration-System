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



def modular_subtractor_phi(qc, b, anc, a, N, controls=()):
    """Modular subtraction in Fourier space: b -> (b - a) mod N.

    Uses (b - a) mod N = (b + (N - a)) mod N, so it reuses the tested adder.
    This is the "undo" step the Q2 multiplier needs. a = 0 changes nothing.
    """
    if not (0 <= a < N):
        raise ValueError("need 0 <= a < N")
    if a == 0:
        return
    modular_adder_phi(qc, b, anc, N - a, N, controls)
# ---------------------------------------------------------------------
# Modular multiplier and exponentiation (Week 2 Day 1)
# ---------------------------------------------------------------------
def _cmult_add(qc, c, x, b, anc, a, N, subtract=False):
    """b -> b +/- (a * x) mod N when control c is 1 (b starts below N).

    Adds (a * 2**i) mod N to b once for every bit x[i] that is 1, using the
    doubly-controlled modular adder (controls: c and x[i]).
    """
    step = modular_subtractor_phi if subtract else modular_adder_phi
    qft_gates(qc, b)
    for i in range(len(x)):
        step(qc, b, anc, (a * 2 ** i) % N, N, controls=[c, x[i]])
    qft_dagger_gates(qc, b)


def controlled_modmul(qc, c, x, b, anc, a, N):
    """Beauregard controlled multiplier: x -> (a * x) mod N if c is 1.

    x: n qubits holding 0 <= x < N (LSB first), with N < 2**n.
    b: n+1 qubits, must start at 0 and is returned to 0.
    anc: one ancilla (starts and ends at 0). Needs gcd(a, N) = 1.
    Steps: b += a*x; swap x and b; b -= a^-1 * x. The modular inverse is
    computed classically to define the gates; it is not order finding.
    """
    a %= N
    if math.gcd(a, N) != 1:
        raise ValueError(f"a={a} must be coprime to N={N}")
    if N >= 2 ** len(x) or len(b) != len(x) + 1:
        raise ValueError("need len(x) = n with N < 2**n, and len(b) = n + 1")
    _cmult_add(qc, c, x, b, anc, a, N)
    for i in range(len(x)):
        qc.cswap(c, x[i], b[i])
    _cmult_add(qc, c, x, b, anc, pow(a, -1, N), N, subtract=True)


def modular_exponentiation(qc, e, x, b, anc, a, N):
    """Quantum modular exponentiation: x -> a**e mod N, e in superposition.

    e: exponent register (LSB first, left unchanged). x must start as |1>.
    Qubit j of e controls multiplication by a**(2**j) mod N, so the exponent
    is built from gates and never computed as a period or a search.
    """
    for j, ctrl in enumerate(e):
        controlled_modmul(qc, ctrl, x, b, anc, pow(a, 2 ** j, N), N)