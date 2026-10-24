"""
q2_shor_run.py
--------------
Runs the Q2 gate-level Shor circuit (q2_shor.py), does the classical
post-processing the algorithm defines (continued fractions, gcd), times one
iteration, and builds the evidence record (rule 4).

  python src/shor_run.py --N 15 --a 7 --shots 20
  python src/shor_run.py --time-iteration --N 35 --a 2
  python src/shor_run.py --N 15 --a 7 --shots 20 --save   # append to data/quantum_runs.json

All results: Aer simulator, toy size.
"""
import argparse
import datetime
import json
import math
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from qiskit import QuantumCircuit, transpile  # noqa: E402
import qiskit  # noqa: E402
import qiskit_aer  # noqa: E402
from qiskit_aer import AerSimulator  # noqa: E402

from q2_arith import controlled_modmul  # noqa: E402
from q2_shor import build_shor_ipea, shor_layout  # noqa: E402
import shor_post as SP  # noqa: E402
import quantum_runs as QR  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RUNS_FILE = ROOT / "data" / "quantum_runs.json"
DIAGRAM_DIR = ROOT / "docs" / "circuits"
QUESTION_GROUP = "q2_shor_gate"      # runs that differ only in N and a (rule 6)
LABEL = "Aer simulator, toy size"
SEED_SIM = 12345
SEED_TRANSPILE = 12345


def factors_from_measurement(y: int, m: int, a: int, N: int):
    """Classical post-processing for one measured value y (phase = y / 2**m).

    Uses the shared helpers in shor_post.py (continued fractions, then gcd).
    The period check lives there, not here, so this runner has no period loop
    (static guard, rule 8). Returns (p, q) or None.
    """
    return SP.factors_from_measurement(y, m, a, N)


def run_shor(a: int, N: int, shots: int, m: int = None):
    """Run the circuit on Aer. Returns (record, circuit)."""
    m = 2 * N.bit_length() if m is None else m
    qc = build_shor_ipea(a, N, m)
    backend = AerSimulator()
    t0 = time.perf_counter()
    compiled = transpile(qc, backend, seed_transpiler=SEED_TRANSPILE)
    t_transpile = time.perf_counter() - t0
    t0 = time.perf_counter()
    counts = backend.run(compiled, shots=shots, seed_simulator=SEED_SIM).result().get_counts()
    t_run = time.perf_counter() - t0

    found = {}
    successes = 0
    for bits, cnt in counts.items():
        f = factors_from_measurement(int(bits, 2), m, a, N)
        if f:
            found[f] = found.get(f, 0) + cnt
            successes += cnt
    record = {
        "algorithm": "Shor order finding, gate level (Beauregard, iterative phase estimation)",
        "id": f"q2-shor-N{N}-a{a}-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "label": LABEL, "N": N, "a": a, "n_bits": N.bit_length(), "phase_bits": m,
        "qubits": qc.num_qubits, "depth": qc.depth(), "gate_counts": dict(qc.count_ops()),
        "shots": shots, "backend": getattr(backend, "name", "AerSimulator"),
        "qiskit_version": qiskit.__version__, "qiskit_aer_version": qiskit_aer.__version__,
        "seed_simulator": SEED_SIM, "seed_transpiler": SEED_TRANSPILE,
        "counts": counts, "factors_found": {f"{p}x{q}": c for (p, q), c in found.items()},
        "success_rate": successes / shots,
        "transpile_seconds": round(t_transpile, 3), "run_seconds": round(t_run, 3),
        "diagram_file": None,
        "chi_square": None,
        "pending": ["chi-square against the theoretical distribution (rule 5)",
                    "change-the-question comparison (rule 6)", "circuit diagram file"],
    }
    return record, qc


def time_one_iteration(a: int, N: int) -> dict:
    """Time ONE controlled modular multiplication (one phase-estimation step)."""
    lay = shor_layout(N)
    qc = QuantumCircuit(lay["qubits"], lay["qubits"])
    qc.x(lay["x"][0])
    qc.x(lay["c"])
    controlled_modmul(qc, lay["c"], lay["x"], lay["b"], lay["anc"], a % N, N)
    qc.measure(range(lay["qubits"]), range(lay["qubits"]))
    backend = AerSimulator()
    t0 = time.perf_counter()
    compiled = transpile(qc, backend, seed_transpiler=SEED_TRANSPILE)
    t_transpile = time.perf_counter() - t0
    t0 = time.perf_counter()
    counts = backend.run(compiled, shots=1, seed_simulator=SEED_SIM).result().get_counts()
    t_run = time.perf_counter() - t0
    key = next(iter(counts))
    x_value = int(key, 2) & (2 ** lay["n"] - 1)
    m = 2 * lay["n"]
    return {"N": N, "a": a, "qubits": lay["qubits"], "label": LABEL,
            "gates_before_transpile": sum(qc.count_ops().values()),
            "gates_after_transpile": sum(compiled.count_ops().values()),
            "transpile_seconds": round(t_transpile, 3), "run_seconds": round(t_run, 3),
            "x_after": x_value, "x_expected": a % N,
            "estimate_seconds_per_shot": round(m * t_run, 1),
            "estimate_note": f"ESTIMATE: {m} iterations x one-iteration run time; real time per shot may differ"}


def write_diagram(qc, N: int, a: int) -> str:
    """Write a structure file for the circuit and return its path relative to the repo root.

    The full text drawing of a gate-level Shor circuit is megabytes long (N=15 alone is 2.6 MB), so
    it is not committed. This file holds what a reviewer needs: register layout, gate counts and the
    start of the instruction sequence, run-length encoded. It is a SUMMARY of the circuit, not a drawing.
    """
    lay = shor_layout(N)
    names = [ins.operation.name for ins in qc.data]
    runs = []
    for name in names:
        if runs and runs[-1][0] == name:
            runs[-1][1] += 1
        else:
            runs.append([name, 1])
    lines = [f"Shor order finding, gate level (Beauregard, iterative phase estimation). {LABEL}.",
             f"N = {N}, a = {a}, qubits = {qc.num_qubits}, phase bits = {qc.num_clbits}, depth = {qc.depth()}, "
             f"instructions = {len(names)}",
             "This is a structure summary, not a full drawing (the full text drawing is megabytes long).",
             "",
             "Registers (qubit indices):",
             f"  x (value register, {lay['n']} qubits): {lay['x']}",
             f"  b (accumulator, {len(lay['b'])} qubits): {lay['b']}",
             f"  anc (overflow ancilla): {lay['anc']}",
             f"  c (single control qubit, reused each round): {lay['c']}",
             "",
             "Gate counts (before transpiling): " + ", ".join(f"{k} {v}" for k, v in sorted(qc.count_ops().items())),
             "",
             f"First 60 of {len(runs)} runs of identical instructions (name x count):"]
    lines += [f"  {name} x {cnt}" for name, cnt in runs[:60]]
    DIAGRAM_DIR.mkdir(parents=True, exist_ok=True)
    out = DIAGRAM_DIR / f"q2_shor_gate_N{N}_a{a}.txt"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out.relative_to(ROOT).as_posix()


def to_evidence(record: dict, diagram_file: str) -> dict:
    """Convert run_shor()'s record into the evidence schema of quantum_runs.py (rule 4)."""
    top = max(record["factors_found"].items(), key=lambda kv: kv[1])[0] if record["factors_found"] else None
    factors = [int(x) for x in top.split("x")] if top else []
    return {
        "run_id": record["id"],
        "timestamp_utc": QR.now_utc(),
        "algorithm": "shor_gate",
        "question_group": QUESTION_GROUP,
        "inputs": {"N": record["N"], "a": record["a"], "phase_bits": record["phase_bits"]},
        "qubits": record["qubits"], "depth": record["depth"], "gate_counts": record["gate_counts"],
        "shots": record["shots"], "backend": record["backend"],
        "backend_version": record["qiskit_aer_version"], "qiskit_version": record["qiskit_version"],
        "seed_simulator": record["seed_simulator"], "seed_transpiler": record["seed_transpiler"],
        "counts": record["counts"], "success_rate": record["success_rate"],
        "runtime_seconds": round(record["transpile_seconds"] + record["run_seconds"], 3),
        "diagram_file": diagram_file, "label": record["label"], "simulated": True,
        "result": {"factors": factors, "factors_found": record["factors_found"]},
        "notes": "chi-square against the theoretical distribution (rule 5) and a second-method "
                 "cross-check (rule 9) are not done yet; diagram_file is a structure summary",
    }


def save_record(record, qc, path=RUNS_FILE):
    """Validate and append the run to data/quantum_runs.json ({"schema_version": 1, "runs": [...]})."""
    QR.append_run(to_evidence(record, write_diagram(qc, record["N"], record["a"])), path)


def print_record(r):
    print(f"{r['label']}: N={r['N']} a={r['a']}  qubits={r['qubits']}  phase bits={r['phase_bits']}  shots={r['shots']}")
    print(f"depth={r['depth']}  gates={r['gate_counts']}")
    print(f"transpile {r['transpile_seconds']} s, run {r['run_seconds']} s")
    top = sorted(r["counts"].items(), key=lambda kv: -kv[1])[:8]
    print("top outcomes (y, count):", [(int(b, 2), c) for b, c in top])
    print(f"factors found: {r['factors_found'] or 'none'}   success rate: {r['success_rate']:.0%}")
    print("pending (not done yet):", "; ".join(r["pending"]))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--N", type=int, required=True)
    ap.add_argument("--a", type=int, required=True)
    ap.add_argument("--shots", type=int, default=20)
    ap.add_argument("--time-iteration", action="store_true")
    ap.add_argument("--save", action="store_true", help="append the record to data/quantum_runs.json")
    args = ap.parse_args()
    if args.time_iteration:
        for k, v in time_one_iteration(args.a, args.N).items():
            print(f"  {k}: {v}")
    else:
        rec, circuit = run_shor(args.a, args.N, args.shots)
        print_record(rec)
        if args.save:
            save_record(rec, circuit)
            print("saved to", RUNS_FILE)