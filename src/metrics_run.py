"""
metrics_run.py
--------------
Collects the Q4 circuit metrics (Week 3 Day 2) for n = 4 to 8.

  python src/metrics_run.py                   # one iteration for n = 4..8; full circuit for n = 4..6
  python src/metrics_run.py --full-all        # also transpile the full circuit for n = 7, 8 (slow)
  python src/metrics_run.py --n 4 5           # only some sizes
  python src/metrics_run.py --out outputs/q4_metrics.json

Simulation (correctness check of one iteration) only for n <= 6; n = 7 and 8 are
transpiled only. The estimate "full = 2n x one iteration" is an ESTIMATE.
Fitting and extrapolation to 1024 and 2048 bits come next week.
Aer simulator / transpiler, toy size.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import qiskit  # noqa: E402

from q4_metrics import (BASE, MODULI, full_circuit, iteration_circuit,  # noqa: E402
                        modulus_for, transpiled_metrics)
from shor_run import time_one_iteration  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LABEL = "transpiler metrics and Aer simulator, toy size"
SIM_MAX_N = 6


def collect(ns, full_ns, simulate=True) -> dict:
    rows = []
    for n in ns:
        N = modulus_for(n)
        row = {"n": n, "N": N, "a": BASE, "phase_bits": 2 * n, "qubits_2n_plus_3": 2 * n + 3}
        t0 = time.perf_counter()
        it = transpiled_metrics(iteration_circuit(n))
        row["iteration"] = {**it, "transpile_seconds": round(time.perf_counter() - t0, 2)}
        row["estimate_full_depth"] = 2 * n * it["depth"]
        row["estimate_full_two_qubit_gates"] = 2 * n * it["two_qubit_gates"]
        row["estimate_note"] = "ESTIMATE: 2n x one iteration; the full circuit adds only single-qubit corrections"
        if simulate and n <= SIM_MAX_N:
            sim = time_one_iteration(BASE, N)
            row["simulated_iteration"] = {"x_after": sim["x_after"], "x_expected": sim["x_expected"],
                                          "correct": sim["x_after"] == sim["x_expected"],
                                          "run_seconds": sim["run_seconds"]}
        if n in full_ns:
            t0 = time.perf_counter()
            full = transpiled_metrics(full_circuit(n))
            row["full"] = {**full, "transpile_seconds": round(time.perf_counter() - t0, 2)}
            if it["two_qubit_gates"]:
                row["full_vs_estimate_two_qubit"] = round(full["two_qubit_gates"] / row["estimate_full_two_qubit_gates"], 3)
        rows.append(row)
    return {"label": LABEL, "qiskit_version": qiskit.__version__,
            "basis": ["cx", "rz", "sx", "x"], "optimization_level": 0, "seed_transpiler": 12345,
            "moduli": {str(k): v for k, v in MODULI.items()}, "rows": rows}


def print_table(res):
    print(f"{res['label']}, qiskit {res['qiskit_version']}, basis {res['basis']}, optimisation level 0\n")
    print(f"{'n':<3}{'N':<5}{'qubits':<8}{'iter depth':>11}{'iter cx':>10}{'full cx':>12}{'est 2n*iter cx':>16}  checked by simulation")
    for r in res["rows"]:
        full = r.get("full", {}).get("two_qubit_gates", "-")
        sim = r.get("simulated_iteration")
        chk = "-" if sim is None else ("yes, correct" if sim["correct"] else "NO: WRONG RESULT")
        print(f"{r['n']:<3}{r['N']:<5}{r['qubits_2n_plus_3']:<8}{r['iteration']['depth']:>11}"
              f"{r['iteration']['two_qubit_gates']:>10}{str(full):>12}{r['estimate_full_two_qubit_gates']:>16}  {chk}")
    print("\nEstimates are marked as such; no extrapolation to real key sizes is done here.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, nargs="+", default=[4, 5, 6, 7, 8])
    ap.add_argument("--full-all", action="store_true", help="also transpile the full circuit for n = 7 and 8 (slow)")
    ap.add_argument("--no-sim", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "outputs" / "q4_metrics.json"))
    a = ap.parse_args()
    full_ns = [n for n in a.n if n <= 6 or a.full_all]
    res = collect(a.n, full_ns, simulate=not a.no_sim)
    Path(a.out).parent.mkdir(exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print_table(res)
    print(f"\nWrote {a.out}")