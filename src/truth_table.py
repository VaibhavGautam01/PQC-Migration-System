"""
truth_table.py - rule 9 harness (Q12): check a reversible block against plain Python.

verify_basis_map() runs the block on computational-basis inputs (all of them for small
n, random ones for larger n), reads the exact output basis state from the statevector
and compares it with a plain Python function. A block that is not a clean permutation
of basis states (output spread over several states) also fails.
Qubit order: qubit 0 is the least significant bit (qiskit order).
Aer simulator, toy size (statevector method).
"""
import random

from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


def all_inputs(n_qubits):
    return list(range(2 ** n_qubits))


def random_inputs(n_qubits, k, seed=12345):
    """k distinct random inputs (all of them if k >= 2**n_qubits)."""
    if k >= 2 ** n_qubits:
        return all_inputs(n_qubits)
    return sorted(random.Random(seed).sample(range(2 ** n_qubits), k))


def run_block(n_qubits, apply_block, x):
    """Prepare basis state x, apply the block, return (output state or None, probability)."""
    qc = QuantumCircuit(n_qubits)
    for i in range(n_qubits):
        if (x >> i) & 1:
            qc.x(i)
    apply_block(qc)
    probs = Statevector(qc).probabilities()
    best = max(range(len(probs)), key=lambda j: probs[j])
    return best, float(probs[best])


def verify_basis_map(n_qubits, apply_block, expected, inputs=None, tol=1e-6):
    """Return a list of failures (empty list = the block matches `expected` on every input).

    expected(x) -> the output basis state (an integer) for input x.
    """
    failures = []
    for x in (all_inputs(n_qubits) if inputs is None else inputs):
        out, p = run_block(n_qubits, apply_block, x)
        want = expected(x)
        if p < 1 - tol:
            failures.append(f"input {x}: output is spread over several states (best p={p:.4f})")
        elif out != want:
            failures.append(f"input {x}: got {out}, expected {want}")
    return failures
