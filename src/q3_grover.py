"""
q3_grover.py - Q3: Grover's search against a toy block cipher (the CIRCUIT BUILDER).

THE QUESTION THE CIRCUIT ANSWERS
--------------------------------
An attacker knows two (plaintext, ciphertext) pairs made with one secret 8-bit key. Which of
the 256 keys encrypts both plaintexts to the right ciphertexts? Grover's algorithm finds it
with about (pi/4) * sqrt(256) = 12 oracle calls instead of ~128 trial encryptions on average.

HOW THE CIRCUIT IS BUILT (all from reversible gates - rule 1)
------------------------------------------------------------
Qubit layout (18 qubits):
    qubits  0..7   KEY register     the search space, put in superposition by Hadamards
    qubits  8..15  STATE register   scratch space where the cipher is computed
    qubits 16..17  FLAG qubits      f1 = "pair 1 matches", f2 = "pair 2 matches"

ORACLE (one Grover "question"), for each known pair (P, C):
    1. load P into the STATE register with X gates               (P is a public constant)
    2. run the toy cipher on the STATE register with CNOT / Toffoli gates. The key bits
       come from the KEY register, so the STATE now holds E_key(P) for EVERY key at once
    3. flip the STATE bits where C has a 0, so "E_key(P) == C" means "all STATE bits are 1"
    4. one multi-controlled NOT sets the flag qubit when all STATE bits are 1
    5. undo steps 3, 2, 1 (every gate is its own inverse, so we replay them backwards);
       the STATE register is clean again and only the flag remembers the result
  Then a controlled-Z on (f1, f2) flips the sign of every key that matches BOTH pairs, and
  the flags are uncomputed again by running the pair blocks in reverse order.
  The answer key is NOT inside the oracle: only the public pairs (P, C) are. Change the pairs
  and the same code attacks a different key (rule 6, change the question).

DIFFUSION: Hadamards, X gates and a multi-controlled Z on the KEY register reflect every
amplitude about the average, which makes the marked key's amplitude grow each round.

EVERYTHING IS DATA FIRST
------------------------
Each function returns a list of simple gate tuples ("operations"):
    ("h", q)                      Hadamard on qubit q
    ("x", q)                      NOT on qubit q
    ("mcx", (c1, c2, ...), t)     NOT on t when all control qubits are 1 (0 controls = plain X)
Keeping the circuit as data lets an independent numpy simulator (grover_emulator.py) run the
SAME gate list as a second method (rule 9), and lets tests check every block by truth table.
ops_to_circuit() turns the list into a real Qiskit QuantumCircuit.

RULES THIS FILE MUST OBEY
-------------------------
* It never imports toy_cipher.py, grover_theory.py or the emulator. The circuit may not be
  able to see the key, the number of solutions or any classical search helper (rule 3).
  tests/test_q3_grover.py checks this with an AST scan.
* No function here takes a `key`; only `pairs` are given (public information).
* The static guard (rule 8) scans this whole file.

Aer simulator, toy size. The cipher is a toy; AES-128/256 and SHA-256 are covered only by
published resource estimates, never by this circuit.
"""
from math import pi

from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

# ---------------------------------------------------------------- qubit layout
KEY = tuple(range(0, 8))             # key register (search space)
STATE = tuple(range(8, 16))          # scratch register holding the cipher state
FLAGS = (16, 17)                     # one flag per known pair
NUM_QUBITS = 18

# The cipher's 4-bit S-box as a gate network on 4 local wires 0..3 (a permutation, because
# every gate is reversible). ("ccx", c1, c2, t) = Toffoli, ("cx", c, t) = CNOT, ("x", t) = NOT.
# Table form (for the tests): [8, 11, 10, 7, 14, 13, 3, 12, 0, 5, 2, 9, 4, 1, 15, 6].
SBOX_NETWORK = (
    ("ccx", 1, 2, 0),
    ("x", 3),
    ("ccx", 0, 1, 3),
    ("cx", 0, 2),
    ("ccx", 2, 3, 1),
    ("ccx", 0, 3, 2),
)


# ---------------------------------------------------------------- small gate helpers
def sbox_ops(wires: tuple) -> list:
    """The S-box network applied to four physical qubits `wires` (wires[0] = local wire 0)."""
    ops = []
    for g in SBOX_NETWORK:
        if g[0] == "x":
            ops.append(("x", wires[g[1]]))
        elif g[0] == "cx":
            ops.append(("mcx", (wires[g[1]],), wires[g[2]]))
        else:
            ops.append(("mcx", (wires[g[1]], wires[g[2]]), wires[g[3]]))
    return ops


def mcz_ops(qubits: tuple) -> list:
    """Multi-controlled Z: flips the sign when ALL given qubits are 1.

    Z = H X H on the last qubit, so a multi-controlled Z is H, multi-controlled X, H.
    """
    *controls, target = qubits
    return [("h", target), ("mcx", tuple(controls), target), ("h", target)]


def mask_ops(wires: list, constant: int) -> list:
    """X gates on the wires whose bit of `constant` is 0.

    After this, "state == constant" is the same as "every wire is 1", which is what a
    multi-controlled NOT can detect. Applying the same mask twice undoes it.
    """
    return [("x", w) for j, w in enumerate(wires) if not (constant >> j) & 1]


# ---------------------------------------------------------------- the cipher as gates
def encrypt_ops(plaintext: int):
    """Gates that compute the toy cipher on the STATE register for a known plaintext.

    Returns (ops, out_wires): out_wires[j] is the physical qubit that holds ciphertext bit j
    when the ops are finished (the bit permutation just renames wires, it costs no gates).
    Every gate is X, CNOT or Toffoli, so replaying the list backwards undoes it.
    """
    ops = []
    wire = list(STATE)                       # wire[j] = qubit currently holding logical bit j

    for j in range(8):                       # load the public plaintext constant
        if (plaintext >> j) & 1:
            ops.append(("x", wire[j]))

    for i in range(8):                       # round 1: XOR the key into the state
        ops.append(("mcx", (KEY[i],), wire[i]))
    ops += sbox_ops(tuple(wire[0:4]))        # S-box on the low nibble
    ops += sbox_ops(tuple(wire[4:8]))        # S-box on the high nibble

    new_wire = [None] * 8                    # linear layer: bit i moves to position 3*i mod 8
    for i in range(8):
        new_wire[(3 * i) % 8] = wire[i]
    wire = new_wire

    for i in range(8):                       # round 2: XOR the key rotated left by 3 bits
        ops.append(("mcx", (KEY[(i - 3) % 8],), wire[i]))
    ops += sbox_ops(tuple(wire[0:4]))
    ops += sbox_ops(tuple(wire[4:8]))
    return ops, wire


def pair_block_ops(pair: tuple, flag: int) -> list:
    """Set `flag` to 1 exactly when the key in KEY encrypts pair[0] to pair[1].

    compute cipher -> mask -> multi-controlled NOT -> unmask -> uncompute cipher.
    Afterwards the STATE register is back to all zeros; only `flag` carries the result.
    """
    plaintext, ciphertext = pair
    enc, out_wires = encrypt_ops(plaintext)
    mask = mask_ops(out_wires, ciphertext)
    return enc + mask + [("mcx", tuple(out_wires), flag)] + mask + list(reversed(enc))


def oracle_ops(pairs) -> list:
    """The Grover oracle: flip the sign of every key consistent with ALL known pairs."""
    flags = FLAGS[:len(pairs)]
    compute = []
    for pair, flag in zip(pairs, flags):
        compute += pair_block_ops(pair, flag)
    # sign flip when every flag is 1; with one pair this is a plain Z on that flag
    phase = mcz_ops(tuple(flags))
    # uncompute the flags: every block is self-inverse, so replay them in reverse order
    uncompute = []
    for pair, flag in reversed(list(zip(pairs, flags))):
        uncompute += pair_block_ops(pair, flag)
    return compute + phase + uncompute


def diffusion_ops() -> list:
    """Grover diffusion on the KEY register: H, X, multi-controlled Z, X, H."""
    ops = [("h", q) for q in KEY]
    ops += [("x", q) for q in KEY]
    ops += mcz_ops(KEY)
    ops += [("x", q) for q in KEY]
    ops += [("h", q) for q in KEY]
    return ops


def grover_ops(pairs, iterations: int) -> list:
    """Full Grover gate list: uniform superposition, then `iterations` x (oracle, diffusion)."""
    ops = [("h", q) for q in KEY]
    for _ in range(iterations):
        ops += oracle_ops(pairs)
        ops += diffusion_ops()
    return ops


# ---------------------------------------------------------------- Qiskit conversion
def ops_to_circuit(ops, measure: bool = True, name: str = "grover_toy_cipher") -> QuantumCircuit:
    """Turn a gate list into a Qiskit circuit (optionally measuring the KEY register)."""
    key = QuantumRegister(8, "key")
    state = QuantumRegister(8, "state")
    flag = QuantumRegister(2, "flag")
    qc = QuantumCircuit(key, state, flag, name=name)
    qubits = list(key) + list(state) + list(flag)          # index i = qubit number i
    if measure:
        out = ClassicalRegister(8, "k")                    # classical bit i <- key qubit i
        qc.add_register(out)
    for op in ops:
        if op[0] == "h":
            qc.h(qubits[op[1]])
        elif op[0] == "x":
            qc.x(qubits[op[1]])
        else:                                              # ("mcx", controls, target)
            controls = [qubits[c] for c in op[1]]
            target = qubits[op[2]]
            if len(controls) == 0:
                qc.x(target)
            elif len(controls) == 1:
                qc.cx(controls[0], target)
            elif len(controls) == 2:
                qc.ccx(controls[0], controls[1], target)
            else:
                qc.mcx(controls, target)
    if measure:
        qc.measure(list(key), out)
    return qc


def build_grover(pairs, iterations: int, measure: bool = True) -> QuantumCircuit:
    """Build the Grover circuit that attacks the key behind the public pairs.

    pairs      : list of (plaintext, ciphertext) known to the attacker. Nothing else.
    iterations : number of (oracle + diffusion) rounds.
    """
    if not 1 <= len(pairs) <= len(FLAGS):
        raise ValueError("this circuit supports one or two known pairs")
    return ops_to_circuit(grover_ops(pairs, iterations), measure,
                          name=f"grover_toy_cipher_k{iterations}")
