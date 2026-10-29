"""
q10_dlog.py - Q10: Shor's algorithm for the discrete logarithm (the CIRCUIT BUILDER).

THE QUESTION THE CIRCUIT ANSWERS
---------------------------------
Public: a prime p, a generator g (of order r, found separately by Q1's order-finding circuit
on the SAME g and p), and h = g^x mod p. Find the SECRET x. This is the hard problem behind
Diffie-Hellman key exchange and DSA signatures - see dlog_post.py's module docstring for the
full derivation and an empirical check against a known instance.

CIRCUIT, two counting registers of t qubits each, A and B, plus a work register of n qubits
    A, B    : put into superposition with Hadamards
    work    : starts at |1>
    for each bit j of A: controlled-multiply work by g^(2**j) mod p          (public: g, p)
    for each bit j of B: controlled-multiply work by (g^-x)^(2**j) mod p,
                         i.e. by h^(-2**j) mod p                             (public: h, p)
    inverse QFT on A, inverse QFT on B (separately)
    measure A into classical register "ya", measure B into classical register "yb"

This reuses the SAME oracle-building block as Q1 (a controlled modular-multiplication matrix
from a classical constant, `pow(g, 2**j, p)` or `pow(pow(h, -1, p), 2**j, p)`) and the SAME
inverse-QFT gate list - both imported from src/q1_shor_pe.py rather than rewritten, so there is
exactly one implementation of each to keep correct. x itself never appears in the circuit: only
g, h and p do (all public), and h^-1 is computed classically only to build the oracle input,
exactly as Q1's rule-8 allowance for pow(a, x, N) permits.

ONE COMBINED CLASSICAL REGISTER, NOT TWO
------------------------------------------
Both registers measure into ONE classical register of 2*t bits (qc.measure(A + B, out)),
exactly the single-register pattern src/q1_shor_pe.py already uses and that has been proven
correct by real runs (Q1 correctly found the periods of N=15, 21, 35 on real Aer hardware with
this exact convention). A's qubits map to the LOW clbits (0..t-1), B's to the HIGH clbits
(t..2t-1). Reading the returned bitstring the same way Q1 does (leftmost character = highest
clbit = most significant), the first t characters of the string hold B's value and the last t
characters hold A's value - q10_run.py's parse_counts() does this split.
(An earlier two-separate-classical-register version of this file produced ambiguous, Qiskit-
version-dependent results in testing - see q10_run.py's module docstring for why this was
changed, and run --self-test before trusting any Q10 output on a new machine.)

Aer simulator, toy size. Verified (see dlog_post.py) against known (p, g, x) instances with a
second, independent numpy simulation before this file was written.
"""
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit.circuit.library import UnitaryGate

from src.q1_shor_pe import apply_inverse_qft, controlled_modmul_matrix


def layout(p: int, t: int) -> dict:
    """Qubit numbers of register A, register B and the work register."""
    n = p.bit_length()
    A = list(range(t))
    B = list(range(t, 2 * t))
    work = list(range(2 * t, 2 * t + n))
    return {"A": A, "B": B, "work": work, "n": n, "total": 2 * t + n}


def default_counting_bits(p: int) -> int:
    """2 * bits(p) counting qubits per register: enough precision for dlog_post.py's rounding."""
    return 2 * p.bit_length()


def build_dlog(g: int, h: int, p: int, t: int = None, measure: bool = True) -> QuantumCircuit:
    """Build the two-register discrete-log phase-estimation circuit.

    g, h, p : the question. x is NOT a parameter here; it exists only in what h was computed
              from, which this circuit never sees. Change g and h (keeping p and the hidden x)
              and the SAME code answers a new question (rule 6).
    t       : counting qubits per register (default 2 * bits(p)).
    """
    if not 1 < g < p or not 1 < h < p:
        raise ValueError(f"need 1 < g, h < p (got g={g}, h={h}, p={p})")
    t = t or default_counting_bits(p)
    lay = layout(p, t)
    A, B, work, n = lay["A"], lay["B"], lay["work"], lay["n"]

    qc = QuantumCircuit(QuantumRegister(t, "a"), QuantumRegister(t, "b"),
                        QuantumRegister(n, "wrk"), name=f"q10_dlog_p{p}")
    if measure:
        out = ClassicalRegister(2 * t, "y")              # ONE register; see module docstring
        qc.add_register(out)

    qc.x(work[0])                                   # work register = |1>
    qc.h(A); qc.h(B)                                 # both counting registers in superposition

    h_inv = pow(h, -1, p)                            # oracle input only; see rule 8
    for j in range(t):                               # controlled-multiply by g^(2**j) mod p
        mult = pow(g, 2 ** j, p)
        gate = UnitaryGate(controlled_modmul_matrix(mult, p, n), label=f"C-g^(2^{j})")
        qc.append(gate, [A[j]] + list(work))
    for j in range(t):                               # controlled-multiply by (h^-1)^(2**j) mod p
        mult = pow(h_inv, 2 ** j, p)
        gate = UnitaryGate(controlled_modmul_matrix(mult, p, n), label=f"C-h^(-2^{j})")
        qc.append(gate, [B[j]] + list(work))

    apply_inverse_qft(qc, A)                         # the two registers are transformed
    apply_inverse_qft(qc, B)                         # independently, not jointly

    if measure:
        qc.measure(A + B, out)                           # A -> low clbits, B -> high clbits
    return qc
