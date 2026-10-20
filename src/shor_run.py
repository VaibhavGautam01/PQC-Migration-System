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

ROOT = Path(__file__).resolve().parent.parent
RUNS_FILE = ROOT / "data" / "quantum_runs.json"
LABEL = "Aer simulator, toy size"
SEED_SIM = 12345
SEED_TRANSPILE = 12345


def factors_from_measurement(y: int, m: int, a: int, N: int):
    """Classical post-processing for one measured value y (phase = y / 2**m).

    Continued fractions give a candidate period r; r (or a small multiple of
    it) is accepted only if a**r mod N == 1. Returns (p, q) or None.
    """
    if y == 0:
        return None
    r0 = Fraction(y, 2 ** m).limit_denominator(N).denominator
    for k in (1, 2, 3, 4):
        r = r0 * k
        if pow(a, r, N) == 1:
            if r % 2:
                return None
            u = pow(a, r // 2, N)
            if u == N - 1:
                return None
            for f in (math.gcd(u - 1, N), math.gcd(u + 1, N)):
                if f not in (1, N):
                    return tuple(sorted((f, N // f)))
            return None
    return None


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


def save_record(record, path=RUNS_FILE):
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    data.append(record)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
        rec, _ = run_shor(args.a, args.N, args.shots)
        print_record(rec)
        if args.save:
            save_record(rec)
            print("saved to", RUNS_FILE)