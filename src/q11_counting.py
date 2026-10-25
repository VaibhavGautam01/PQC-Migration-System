"""
q11_counting.py - Q11: Grover with an UNKNOWN number of solutions, by quantum counting
(the CIRCUIT BUILDER).

THE PROBLEM
-----------
Grover's search needs the right number of rounds, about (pi/4) * sqrt(N / M), and that depends on
M, the number of keys that fit the known data. With one known (plaintext, ciphertext) pair M can
be 1, 2 or 3 and the attacker does not know which. Too few or too many rounds and the success
probability collapses (it OVERSHOOTS and falls again). So first COUNT, then search.

THE PLAN
--------
  1. Quantum counting: phase estimation on the Grover iterate G, on t counting qubits.
        counting qubit j controls G^(2**j); an inverse QFT then reads the phase of G.
     G rotates by 2*theta with sin^2(theta) = M / N, so the measured number y satisfies
     y / 2**t close to theta / pi  and  M is about N * sin^2(pi * y / 2**t).
  2. Use the estimated M to choose the number of Grover rounds and run the search.

NO ASSUMED ANSWER, NO KEY (rules 2 and 3)
-----------------------------------------
The circuit gets only public information: the known pair (P, C), and the key bits the attacker
already knows (`known_value`, the high bits of the key; here 2 of 8 bits, so N = 2**free_bits
= 64 unknown-key candidates). It is never told M and never sees the key. The count appears only
as a measured histogram.

WHY THE CONTROLLED GROVER ITERATE IS CHEAP TO BUILD
---------------------------------------------------
Controlled-G needs every gate to be controlled, but only a few really must be:
  * oracle: computing the cipher and un-computing it cancel when the control is 0. Only the gate
    that SETS the match flag needs the extra control. The flag is the only thing that carries
    the sign flip, so with control 0 the flag stays 0 and nothing happens.
  * diffusion H X (multi-controlled Z) X H: only the multi-controlled Z needs the control.
  * sign: H X MCZ X H equals MINUS the textbook diffusion 2|s><s| - I. Plain Grover does not care,
    but inside phase estimation the sign shifts the measured phase by 1/2. A Z gate on the control
    qubit removes it, so that controlled-G is exactly |0><0| (x) I + |1><1| (x) G.

EVERYTHING IS DATA FIRST (like q3_grover.py)
--------------------------------------------
Gates are tuples: ("h", q), ("x", q), ("mcx", controls, target), ("swap", a, b),
("cp", angle, control, target). The independent numpy emulator (grover_emulator.py) runs the same
list as a second method (rule 9), and tests check each block by truth table.

Qubit layout, from low to high:   key (free_bits) | state (8) | flag (1) | counting (t)

Aer simulator, toy size. The cipher is a toy. Quantum counting here is a simulation of the
algorithm at toy size, not a speed-up demonstration.
"""
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

from src.q1_shor_pe import inverse_qft_ops
from src.q3_grover import encrypt_ops, mask_ops, mcz_ops


# ---------------------------------------------------------------- layout and helpers
def layout(free_bits: int, counting_bits: int = 0) -> dict:
    """Qubit numbers of every register for a given number of free key bits and counting qubits."""
    key = list(range(free_bits))
    state = list(range(free_bits, free_bits + 8))
    flag = free_bits + 8
    counting = list(range(free_bits + 9, free_bits + 9 + counting_bits))
    return {"key": key, "state": state, "flag": flag, "counting": counting,
            "n": free_bits + 9 + counting_bits}


def _q3_to_local(free_bits: int) -> dict:
    """Map the qubit numbers used by q3_grover (key 0-7, state 8-15, flag 16) to this layout."""
    mapping = {i: i for i in range(free_bits)}
    mapping.update({8 + j: free_bits + j for j in range(8)})
    mapping[16] = free_bits + 8
    return mapping


def _remap(op, mapping):
    """The same gate with its qubit numbers translated through `mapping`."""
    if op[0] in ("h", "x"):
        return (op[0], mapping[op[1]])
    if op[0] == "mcx":
        return ("mcx", tuple(mapping[c] for c in op[1]), mapping[op[2]])
    if op[0] == "swap":
        return ("swap", mapping[op[1]], mapping[op[2]])
    return ("cp", op[1], mapping[op[2]], mapping[op[3]])


def fix_known_key_bits(ops, free_bits: int, known_value: int):
    """Replace the key qubits the attacker already knows by constants.

    Key bit i >= free_bits is known: bit (i - free_bits) of `known_value`. A CNOT controlled by a
    known 1 becomes a plain gate (control removed); controlled by a known 0 it is dropped.
    """
    constant = {i: (known_value >> (i - free_bits)) & 1 for i in range(free_bits, 8)}
    fixed = []
    for op in ops:
        if op[0] == "mcx" and any(c in constant for c in op[1]):
            if any(constant[c] == 0 for c in op[1] if c in constant):
                continue
            fixed.append(("mcx", tuple(c for c in op[1] if c not in constant), op[2]))
        else:
            fixed.append(op)
    return fixed


# ---------------------------------------------------------------- oracle and diffusion
def pair_block_ops(pair, free_bits: int, known_value: int, control=None) -> list:
    """Set the flag when the candidate key encrypts pair[0] to pair[1].

    compute the cipher, mask, (controlled) multi-controlled NOT onto the flag, unmask, uncompute.
    With `control` given, the flag is only set when that qubit is 1.
    """
    plaintext, ciphertext = pair
    mapping = _q3_to_local(free_bits)
    lay = layout(free_bits)
    enc, out_wires = encrypt_ops(plaintext)
    enc = [_remap(op, mapping) for op in fix_known_key_bits(enc, free_bits, known_value)]
    out = [mapping[w] for w in out_wires]
    mask = mask_ops(out, ciphertext)
    controls = tuple(out) + ((control,) if control is not None else ())
    return enc + mask + [("mcx", controls, lay["flag"])] + mask + list(reversed(enc))


def oracle_ops(pair, free_bits: int, known_value: int, control=None) -> list:
    """Flip the sign of every candidate key that fits the pair (only if `control` is 1, if given)."""
    lay = layout(free_bits)
    block = pair_block_ops(pair, free_bits, known_value, control)
    return block + mcz_ops((lay["flag"],)) + block          # flag set, Z on the flag, flag cleared


def diffusion_ops(free_bits: int, control=None) -> list:
    """Grover diffusion on the key qubits. With `control`, the textbook controlled diffusion."""
    keys = tuple(layout(free_bits)["key"])
    ops = [("h", q) for q in keys] + [("x", q) for q in keys]
    ops += mcz_ops(keys if control is None else keys + (control,))
    ops += [("x", q) for q in keys] + [("h", q) for q in keys]
    if control is not None:
        ops += mcz_ops((control,))                           # Z on the control: removes the -1
    return ops


# ---------------------------------------------------------------- whole algorithms
def counting_ops(pair, free_bits: int, known_value: int, counting_bits: int) -> list:
    """Quantum counting: H on keys and counting qubits, controlled-G^(2**j), inverse QFT."""
    lay = layout(free_bits, counting_bits)
    ops = [("h", q) for q in lay["key"]] + [("h", q) for q in lay["counting"]]
    for j, control in enumerate(lay["counting"]):
        for _ in range(2 ** j):                              # G^(2**j) = G applied 2**j times
            ops += oracle_ops(pair, free_bits, known_value, control)
            ops += diffusion_ops(free_bits, control)
    mapping = {i: q for i, q in enumerate(lay["counting"])}  # QFT qubit i -> counting qubit i
    ops += [_remap(op, mapping) for op in inverse_qft_ops(counting_bits)]
    return ops


def grover_ops(pair, free_bits: int, known_value: int, iterations: int) -> list:
    """Plain Grover search over the free key bits with the given number of rounds."""
    lay = layout(free_bits)
    ops = [("h", q) for q in lay["key"]]
    for _ in range(iterations):
        ops += oracle_ops(pair, free_bits, known_value)
        ops += diffusion_ops(free_bits)
    return ops


# ---------------------------------------------------------------- Qiskit conversion
def ops_to_circuit(ops, num_qubits: int, measure_qubits, name: str = "q11") -> QuantumCircuit:
    """Turn a gate list into a Qiskit circuit and measure `measure_qubits` (bit i <- qubit list[i])."""
    qr = QuantumRegister(num_qubits, "q")
    qc = QuantumCircuit(qr, name=name)
    if measure_qubits:
        out = ClassicalRegister(len(measure_qubits), "y")
        qc.add_register(out)
    for op in ops:
        if op[0] == "h":
            qc.h(qr[op[1]])
        elif op[0] == "x":
            qc.x(qr[op[1]])
        elif op[0] == "swap":
            qc.swap(qr[op[1]], qr[op[2]])
        elif op[0] == "cp":
            qc.cp(op[1], qr[op[2]], qr[op[3]])
        else:                                                # ("mcx", controls, target)
            controls = [qr[c] for c in op[1]]
            if not controls:
                qc.x(qr[op[2]])
            elif len(controls) == 1:
                qc.cx(controls[0], qr[op[2]])
            elif len(controls) == 2:
                qc.ccx(controls[0], controls[1], qr[op[2]])
            else:
                qc.mcx(controls, qr[op[2]])
    if measure_qubits:
        qc.measure([qr[q] for q in measure_qubits], out)
    return qc


def build_counting(pair, free_bits: int, known_value: int, counting_bits: int) -> QuantumCircuit:
    """Quantum-counting circuit; measures the counting register (bit i <- counting qubit i)."""
    lay = layout(free_bits, counting_bits)
    return ops_to_circuit(counting_ops(pair, free_bits, known_value, counting_bits), lay["n"],
                          lay["counting"], f"q11_counting_t{counting_bits}")


def build_grover(pair, free_bits: int, known_value: int, iterations: int) -> QuantumCircuit:
    """Grover circuit on the free key bits; measures the key qubits (bit i <- key qubit i)."""
    lay = layout(free_bits)
    return ops_to_circuit(grover_ops(pair, free_bits, known_value, iterations), lay["n"],
                          lay["key"], f"q11_grover_k{iterations}")
