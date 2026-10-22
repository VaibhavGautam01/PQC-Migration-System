"""BB84 on the Aer simulator (stabilizer method), toy size, with an ML-DSA-authenticated classical channel.

Label for every result: Aer simulator, toy size. Real QKD needs dedicated optical hardware.
Qubit preparation, basis choice, intercept-resend and measurement are real gates (X, H, measure).
Random bits and bases come from a classical generator, as the protocol defines.
"""
import json
import random
import time
from pathlib import Path

import qiskit
import qiskit_aer
from dilithium_py.ml_dsa import ML_DSA_65
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile
from qiskit_aer import AerSimulator

from pqc_stego.privacy_amp import bits_to_bytes, toeplitz_hash

ABORT_THRESHOLD = 0.11   # commonly cited asymptotic bound near 11 percent. VERIFY a source before quoting.
SAFETY_BITS = 64         # our teaching margin, not a proven security parameter


class QKDAbort(Exception):
    def __init__(self, message, qber=None):
        super().__init__(message)
        self.qber = qber


class AuthChannel:
    """Classical channel where every message is ML-DSA-65 signed. `tamper` models an active attacker."""

    def __init__(self, tamper=None):
        self.tamper = tamper

    def send(self, sender_sk, sender_pk, payload):
        sig = ML_DSA_65.sign(sender_sk, payload)
        wire = self.tamper(payload) if self.tamper else payload
        if not ML_DSA_65.verify(sender_pk, wire, sig):
            raise QKDAbort("classical-channel message failed ML-DSA verification")
        return wire


def build_bb84_circuit(alice_bits, alice_bases, bob_bases, eve_bases=None):
    """basis 0 = Z, basis 1 = X (Hadamard). Eve, if present, intercepts and resends."""
    n = len(alice_bits)
    q = QuantumRegister(n, "q")
    bob = ClassicalRegister(n, "bob")
    if eve_bases is None:
        qc = QuantumCircuit(q, bob)
    else:
        eve = ClassicalRegister(n, "eve")
        qc = QuantumCircuit(q, eve, bob)       # bob is added last, so it is the leftmost register in results
    for i in range(n):
        if alice_bits[i]:
            qc.x(q[i])
        if alice_bases[i]:
            qc.h(q[i])
    qc.barrier()
    if eve_bases is not None:
        for i in range(n):
            if eve_bases[i]:
                qc.h(q[i])
            qc.measure(q[i], eve[i])
            if eve_bases[i]:
                qc.h(q[i])                     # resend the collapsed state in Eve's basis
        qc.barrier()
    for i in range(n):
        if bob_bases[i]:
            qc.h(q[i])
        qc.measure(q[i], bob[i])
    return qc


def _save_evidence(record, path):
    path = Path(path)
    runs = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    runs.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(runs, indent=2), encoding="utf-8")


def run_bb84(n_qubits=1024, seed=None, eve=False, channel=None, threshold=ABORT_THRESHOLD,
             key_bits=256, evidence_path=None):
    rng = random.Random(seed) if seed is not None else random.SystemRandom()
    qseed = seed if seed is not None else rng.randrange(2 ** 31)
    channel = channel or AuthChannel()
    a_pk, a_sk = ML_DSA_65.keygen()
    b_pk, b_sk = ML_DSA_65.keygen()

    alice_bits = [rng.getrandbits(1) for _ in range(n_qubits)]
    alice_bases = [rng.getrandbits(1) for _ in range(n_qubits)]
    bob_bases = [rng.getrandbits(1) for _ in range(n_qubits)]
    eve_bases = [rng.getrandbits(1) for _ in range(n_qubits)] if eve else None

    qc = build_bb84_circuit(alice_bits, alice_bases, bob_bases, eve_bases)
    sim = AerSimulator(method="stabilizer", seed_simulator=qseed)
    tc = transpile(qc, sim, seed_transpiler=qseed)
    t0 = time.perf_counter()
    result = sim.run(tc, shots=1, memory=True, seed_simulator=qseed).result()
    run_seconds = time.perf_counter() - t0
    bob_string = result.get_memory()[0].split()[0]
    bob_bits = [int(c) for c in reversed(bob_string)]   # position i = qubit i

    record = {
        "algorithm": "BB84", "inputs": {"n_qubits": n_qubits, "eve": eve, "threshold": threshold},
        "qubits": tc.num_qubits, "depth": tc.depth(), "gate_counts": dict(tc.count_ops()),
        "shots": 1, "backend": f"AerSimulator(method=stabilizer) qiskit {qiskit.__version__} "
                               f"qiskit-aer {qiskit_aer.__version__}",
        "seed_simulator": qseed, "seed_transpiler": qseed, "run_seconds": round(run_seconds, 4),
        "label": "Aer simulator, toy size",
    }
    try:
        bases_rx = list(channel.send(b_sk, b_pk, bytes(bob_bases)))                      # Bob -> Alice
        keep = [i for i in range(n_qubits) if alice_bases[i] == bases_rx[i]]
        k = max(1, len(keep) // 4)
        sample = sorted(rng.sample(range(len(keep)), k))
        channel.send(a_sk, a_pk, json.dumps({"keep": keep, "sample": sample}).encode())  # Alice -> Bob
        bob_sample = [bob_bits[keep[j]] for j in sample]
        rx = list(channel.send(b_sk, b_pk, bytes(bob_sample)))                           # Bob -> Alice
        alice_sample = [alice_bits[keep[j]] for j in sample]
        qber = sum(x != y for x, y in zip(alice_sample, rx)) / len(sample)
        record.update({"sifted_bits": len(keep), "sample_bits": len(sample), "qber": round(qber, 4)})
        if qber > threshold:
            raise QKDAbort(f"QBER {qber:.3f} is above the threshold {threshold}", qber)
        sample_set = set(sample)
        rest = [j for j in range(len(keep)) if j not in sample_set]
        if len(rest) < key_bits + SAFETY_BITS:
            raise QKDAbort("not enough sifted bits for the requested key", qber)
        alice_rest = [alice_bits[keep[j]] for j in rest]
        bob_rest = [bob_bits[keep[j]] for j in rest]
        seed_bits = [rng.getrandbits(1) for _ in range(len(rest) + key_bits - 1)]
        seed_rx = list(channel.send(a_sk, a_pk, bytes(seed_bits)))                       # Alice -> Bob
        key_a = bits_to_bytes(toeplitz_hash(alice_rest, seed_bits, key_bits))
        key_b = bits_to_bytes(toeplitz_hash(bob_rest, seed_rx, key_bits))
        if key_a != key_b:
            raise QKDAbort("key confirmation failed: Alice and Bob keys differ", qber)
        record.update({"outcome": "key", "key_bits": key_bits, "bits_into_hash": len(rest)})
        return {"key": key_a, "qber": qber, "sifted_bits": len(keep), "record": record}
    except QKDAbort as exc:
        record.update({"outcome": "abort", "reason": str(exc)})
        raise
    finally:
        if evidence_path:
            _save_evidence(record, evidence_path)