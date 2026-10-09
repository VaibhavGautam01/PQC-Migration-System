"""
verify_qiskit.py
----------------
Sanity check that Qiskit and the Aer simulator work on this machine.
Builds a 2-qubit Bell-state circuit and runs it on the simulator.
Expected result: only '00' and '11' outcomes, roughly 50/50.
"""

import sys

try:
    import qiskit
    from qiskit import QuantumCircuit, transpile
    from qiskit_aer import AerSimulator
except ImportError as exc:
    print(f"[FAIL] Import error: {exc}")
    print("Run: pip install qiskit qiskit-aer")
    sys.exit(1)

print(f"Qiskit version : {qiskit.__version__}")
print("Simulator import: OK")

# Bell-state circuit
qc = QuantumCircuit(2, 2)
qc.h(0)
qc.cx(0, 1)
qc.measure([0, 1], [0, 1])

simulator = AerSimulator()
compiled = transpile(qc, simulator)
result = simulator.run(compiled, shots=1000).result()
counts = result.get_counts()

print(f"Counts (1000 shots): {counts}")

# A Bell state must only ever produce 00 or 11
if set(counts.keys()) <= {"00", "11"} and sum(counts.values()) == 1000:
    print("[PASS] Qiskit and Aer simulator are working.")
else:
    print("[FAIL] Unexpected measurement outcomes.")
    sys.exit(1)