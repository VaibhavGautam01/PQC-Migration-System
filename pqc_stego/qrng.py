"""Q7: Hadamard-and-measure bit generator on the Aer simulator (stabilizer method).

HONEST LIMIT: on a simulator the output is pseudo-random (seeded). NOT for production keys.
Real randomness exists only on real quantum hardware. Label: Aer simulator, toy size.
Each bit is one qubit put in |+> with a Hadamard gate and measured.
"""
import json
import time
from pathlib import Path

import qiskit
import qiskit_aer
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

CHUNK = 1024


def generate_bits(n_bits, seed, evidence_path=None):
    bits = []
    chunk_index = 0
    t0 = time.perf_counter()
    last = None
    while len(bits) < n_bits:
        size = min(CHUNK, n_bits - len(bits))
        qseed = seed + chunk_index
        qc = QuantumCircuit(size, size)
        qc.h(range(size))
        qc.measure(range(size), range(size))
        sim = AerSimulator(method="stabilizer", seed_simulator=qseed)
        tc = transpile(qc, sim, seed_transpiler=qseed)
        mem = sim.run(tc, shots=1, memory=True, seed_simulator=qseed).result().get_memory()[0]
        bits += [int(c) for c in reversed(mem)]
        chunk_index += 1
        last = tc
    if evidence_path:
        record = {
            "algorithm": "QRNG (Hadamard and measure)", "inputs": {"n_bits": n_bits, "chunk": CHUNK},
            "qubits": last.num_qubits, "depth": last.depth(), "gate_counts": dict(last.count_ops()),
            "shots": 1, "backend": f"AerSimulator(method=stabilizer) qiskit {qiskit.__version__} "
                                   f"qiskit-aer {qiskit_aer.__version__}",
            "seed_simulator": seed, "seed_transpiler": seed,
            "run_seconds": round(time.perf_counter() - t0, 4),
            "label": "Aer simulator, toy size (pseudo-random, not for production keys)",
        }
        path = Path(evidence_path)
        runs = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        runs.append(record)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(runs, indent=2), encoding="utf-8")
    return bits