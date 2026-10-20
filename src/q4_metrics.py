"""
q4_metrics.py
-------------
Q4: circuit builders and metric helpers for measured resource scaling.

For n = 4 to 8 the moduli are fixed semiprimes with exactly n bits (listed in
MODULI, not computed). The circuits are the Q2 gate-level circuits:
  * iteration_circuit(n): ONE controlled modular multiplication (one phase
    estimation step), the part that repeats 2n times;
  * full circuit: q2_shor.build_shor_ipea(a, N).
Q1 is NOT used here: its dense unitaries give gate counts that say nothing
about Shor's real cost.

Metrics come from transpiling to a fixed basis (cx, rz, sx, x) at optimisation
level 0, so counts are comparable between sizes. Everything is Aer-simulator /
transpiler output for toy sizes; extrapolations are estimates and are labelled so.
"""
from qiskit import QuantumCircuit, transpile

from q2_arith import controlled_modmul
from q2_shor import build_shor_ipea, shor_layout

MODULI = {4: 15, 5: 21, 6: 35, 7: 77, 8: 221}        # 3x5, 3x7, 5x7, 7x11, 13x17
BASE = 2
BASIS = ["cx", "rz", "sx", "x"]
SEED = 12345


def modulus_for(n: int) -> int:
    if n not in MODULI:
        raise ValueError(f"n must be one of {sorted(MODULI)}")
    N = MODULI[n]
    assert N.bit_length() == n and N % 2 == 1
    return N


def iteration_circuit(n: int, a: int = BASE) -> QuantumCircuit:
    """One controlled modular multiplication for the n-bit modulus (no measurement)."""
    N = modulus_for(n)
    lay = shor_layout(N)
    qc = QuantumCircuit(lay["qubits"])
    controlled_modmul(qc, lay["c"], lay["x"], lay["b"], lay["anc"], a % N, N)
    return qc


def full_circuit(n: int, a: int = BASE) -> QuantumCircuit:
    """The complete gate-level Shor circuit (2n phase bits) for the n-bit modulus."""
    return build_shor_ipea(a, modulus_for(n))


def transpiled_metrics(qc: QuantumCircuit) -> dict:
    """Transpile to the fixed basis and read qubits, depth, size and gate counts."""
    compiled = transpile(qc, basis_gates=BASIS, optimization_level=0, seed_transpiler=SEED)
    ops = dict(compiled.count_ops())
    return {"qubits": compiled.num_qubits, "depth": compiled.depth(), "size": compiled.size(),
            "two_qubit_gates": ops.get("cx", 0), "gate_counts": ops}