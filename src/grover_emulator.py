"""
grover_emulator.py - an INDEPENDENT numpy simulator for the gate lists of q3_grover.py and
q11_counting.py.

WHY IT EXISTS (rule 9, second simulation method)
------------------------------------------------
Aer is one simulator. This file is a second, separately written one: it applies the same
("h" / "x" / "mcx" / "swap" / "cp") gate tuples to a plain numpy state vector. If Aer and this
emulator both agree with the sine-squared theory, a bug in either the Qiskit conversion or the
gate list is very unlikely. It is also used to check blocks by truth table.

Supported gate tuples: ("h", q), ("x", q), ("mcx", controls, target), ("swap", a, b) and
("cp", angle, control, target) (controlled phase; needed for the inverse QFT used by Q11's
quantum counting).

Qubit q is bit q of the basis-state index (little-endian, the same convention as Qiskit), so
index = sum of bit_q * 2**q.
Not a quantum computer - a classical simulation, so it stops scaling past ~25 qubits.
"""
import numpy as np


def emulate(ops, num_qubits: int, initial_index: int = 0) -> np.ndarray:
    """Run gate list `ops` on |initial_index> and return the final state vector."""
    size = 2 ** num_qubits
    state = np.zeros(size, dtype=complex)
    state[initial_index] = 1.0
    index = np.arange(size)
    bit = [((index >> q) & 1).astype(bool) for q in range(num_qubits)]   # bit[q][i] = qubit q of i
    root_half = 1 / np.sqrt(2)
    for op in ops:
        if op[0] == "h":
            q = op[1]
            v = state.reshape(-1, 2, 1 << q)
            a, b = v[:, 0, :], v[:, 1, :]
            state = np.stack(((a + b) * root_half, (a - b) * root_half), axis=1).reshape(-1)
        elif op[0] == "swap":
            a, b = op[1], op[2]
            state = state[np.where(bit[a] != bit[b], index ^ (1 << a) ^ (1 << b), index)]
        elif op[0] == "cp":
            _, angle, c, t = op
            state = state * np.where(bit[c] & bit[t], np.exp(1j * angle), 1.0)
        else:
            if op[0] == "x":
                controls, target = (), op[1]
            else:                                           # ("mcx", controls, target)
                controls, target = op[1], op[2]
            active = np.ones(size, dtype=bool)
            for c in controls:
                active &= bit[c]
            # swap the amplitudes of |..0..> and |..1..> on the target wherever all controls are 1
            state = state[np.where(active, index ^ (1 << target), index)]
    return state


def register_probabilities(state: np.ndarray, qubits) -> np.ndarray:
    """Probability of each value of the given qubits (first listed qubit = least significant)."""
    n = int(np.log2(state.size))
    probs = np.abs(state) ** 2
    result = np.zeros(2 ** len(qubits))
    index = np.arange(state.size)
    value = np.zeros(state.size, dtype=int)
    for pos, q in enumerate(qubits):
        value |= ((index >> q) & 1) << pos
    np.add.at(result, value, probs)
    return result


def run_classical(ops, bits: dict) -> dict:
    """Run a gate list that has only x / mcx gates on classical bit values (truth tables).

    `bits` maps qubit -> 0/1 and is copied; missing qubits start at 0. Raises on "h", "swap", "cp".
    """
    b = dict(bits)
    for op in ops:
        if op[0] in ("h", "swap", "cp"):
            raise ValueError("run_classical can only apply x / mcx gates")
        controls, target = ((), op[1]) if op[0] == "x" else (op[1], op[2])
        if all(b.get(c, 0) for c in controls):
            b[target] = b.get(target, 0) ^ 1
    return b
