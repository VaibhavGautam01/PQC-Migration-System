"""
q1_run.py - run the Q1 Shor phase-estimation circuit and record the evidence.

WHAT THIS SCRIPT DOES (one run = one question "find the order of a mod N")
-------------------------------------------------------------------------
  1. builds the circuit (q1_shor_pe.py)                       rule 1
  2. transpiles and runs it on the Aer simulator, seeded      rule 10
  3. post-processes ONLY the measured counts (shor_post.py)   rule 2
  4. chi-square test: measured histogram vs theory            rule 5
  5. cross-check on a second method: exact statevector from
     qiskit.quantum_info vs the analytic distribution         rule 9
  6. saves the circuit diagram and appends an evidence record
     to data/quantum_runs.json (only with --save)             rule 4

Commands (run from the project root, venv active):
  python -m src.q1_run --N 15 --a 7                    # one run, print only
  python -m src.q1_run --N 15 --a 7 --save             # also write the evidence record
  python -m src.q1_run --suite --save                  # N = 15, 21, 35 in one go
  python -m src.q1_run --N 21 --a 2 --no-cross-check   # skip the exact cross-check

All results: Aer simulator, toy size.
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import qiskit                                               # noqa: E402
import qiskit_aer                                           # noqa: E402
from qiskit import transpile                                # noqa: E402
from qiskit.quantum_info import Statevector                 # noqa: E402
from qiskit_aer import AerSimulator                         # noqa: E402

from src import quantum_runs as QR                          # noqa: E402
from src import shor_post as SP                             # noqa: E402
from src.q1_shor_pe import build_shor_pe, default_counting_bits  # noqa: E402
from src.qconfig import BACKEND_LABEL, SEED                 # noqa: E402

QUESTION_GROUP = "shor_pe_change_N_a"       # rule 6: runs that differ only in (N, a)
SUITE = [(15, 7), (15, 2), (21, 2), (35, 2)]
CROSS_CHECK_TOLERANCE = 1e-9


def save_diagram(qc, stem: str) -> str:
    """Save the circuit diagram under docs/circuits/ and return its relative path.

    A text drawing is always saved. A PNG is also tried (needs matplotlib);
    if it works the PNG path is returned, otherwise the text file path.
    """
    folder = ROOT / "docs" / "circuits"
    folder.mkdir(parents=True, exist_ok=True)
    txt = folder / f"{stem}.txt"
    txt.write_text(str(qc.draw(output="text", fold=-1)), encoding="utf-8")
    try:
        png = folder / f"{stem}.png"
        qc.draw(output="mpl", filename=str(png))
        return png.relative_to(ROOT).as_posix()
    except Exception:                                       # no matplotlib: text is enough
        return txt.relative_to(ROOT).as_posix()


def exact_cross_check(a: int, N: int, m: int, probs: list) -> dict:
    """Rule 9: a SECOND simulation method.

    qiskit.quantum_info.Statevector computes the exact output state of the same
    circuit (no sampling, different code from Aer). Its probabilities for the
    counting register must equal the analytic theory to ~1e-9.
    """
    qc_exact = build_shor_pe(a, N, m, measure=False)
    exact = Statevector(qc_exact).probabilities(list(range(m)))
    worst = max(abs(float(p) - q) for p, q in zip(exact, probs))
    return {"method": "Aer sampling vs qiskit.quantum_info.Statevector exact vs analytic theory",
            "max_abs_diff": worst, "tolerance": CROSS_CHECK_TOLERANCE,
            "agree": bool(worst < CROSS_CHECK_TOLERANCE)}


def run_q1(a: int, N: int, shots: int = 4096, m: int = None, cross_check: bool = True):
    """Run one Q1 experiment. Returns (evidence_record, circuit)."""
    SP.check_inputs(a, N)
    m = default_counting_bits(N) if m is None else m
    qc = build_shor_pe(a, N, m)

    backend = AerSimulator(method="statevector")
    t0 = time.perf_counter()
    # optimization_level=0: keep our dense unitary blocks as they are (no costly resynthesis)
    compiled = transpile(qc, backend, optimization_level=0, seed_transpiler=SEED)
    counts = backend.run(compiled, shots=shots, seed_simulator=SEED).result().get_counts()
    runtime = time.perf_counter() - t0
    counts = {str(k).replace(" ", ""): int(v) for k, v in counts.items()}

    found = SP.analyse_counts(counts, m, a, N)               # period + factors from counts only
    probs = SP.theoretical_distribution(a, N, m)             # theory, only for comparison
    chi = SP.chi_square_vs_theory(counts, probs)
    stem = f"q1_shor_pe_N{N}_a{a}"
    record = {
        "run_id": f"q1-N{N}-a{a}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}",
        "timestamp_utc": QR.now_utc(),
        "algorithm": "shor_pe",
        "question_group": QUESTION_GROUP,
        "inputs": {"N": N, "a": a, "counting_qubits": m},
        "qubits": compiled.num_qubits,
        "depth": compiled.depth(),
        "gate_counts": {str(k): int(v) for k, v in compiled.count_ops().items()},
        "shots": shots,
        "backend": "AerSimulator",
        "backend_version": qiskit_aer.__version__,
        "qiskit_version": qiskit.__version__,
        "seed_simulator": SEED,
        "seed_transpiler": SEED,
        "counts": counts,
        "success_rate": found["success_rate"],
        "runtime_seconds": round(runtime, 3),
        "diagram_file": save_diagram(qc, stem),
        "label": BACKEND_LABEL,                              # "Aer simulator, toy size"
        "simulated": True,
        "result": {"period": found["period"], "factors": found["factors"]},
        "chi_square": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in chi.items()},
        "notes": ("Q1: dense controlled-U unitaries built from pow(a, 2**j, N); correct but "
                  "does not scale. Gate counts here are NOT resource estimates (use Q2/Q4)."),
    }
    if cross_check:
        record["cross_check"] = exact_cross_check(a, N, m, probs)
    return record, qc


def print_report(r: dict) -> None:
    """Human-readable summary of one run."""
    N, a, m = r["inputs"]["N"], r["inputs"]["a"], r["inputs"]["counting_qubits"]
    print(f"\n=== Q1 Shor phase estimation | N={N} a={a} | {r['label']} ===")
    print(f"qubits={r['qubits']} (counting {m} + work {r['qubits'] - m})  "
          f"depth={r['depth']}  shots={r['shots']}  run time={r['runtime_seconds']} s")
    top = sorted(r["counts"].items(), key=lambda kv: -kv[1])[:6]
    print("most frequent outcomes y (count):", [(int(b, 2), c) for b, c in top])
    print(f"period found from measurements : {r['result']['period']}")
    print(f"factors found                  : {r['result']['factors']}")
    print(f"shots that alone give factors  : {r['success_rate']:.0%}")
    c = r["chi_square"]
    verdict = "consistent with theory" if c["p_value"] > 0.01 else "DOES NOT MATCH THEORY"
    print(f"chi-square vs theory           : stat={c['statistic']} dof={c['dof']} "
          f"p={c['p_value']:.3f} -> {verdict}")
    if "cross_check" in r:
        x = r["cross_check"]
        print(f"exact statevector cross-check  : max diff {x['max_abs_diff']:.2e} -> "
              f"{'AGREE' if x['agree'] else 'DISAGREE'}")
    print(f"diagram saved to               : {r['diagram_file']}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--N", type=int, help="number to factor (e.g. 15, 21, 35)")
    ap.add_argument("--a", type=int, help="base, must be coprime to N (e.g. 7)")
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--suite", action="store_true", help="run N=15, 21, 35 (4 questions)")
    ap.add_argument("--no-cross-check", action="store_true", help="skip the exact statevector check")
    ap.add_argument("--save", action="store_true", help="append evidence to data/quantum_runs.json")
    args = ap.parse_args()

    if args.suite:
        cases = SUITE
    elif args.N and args.a:
        cases = [(args.N, args.a)]
    else:
        ap.error("give --N and --a, or use --suite")

    exit_code = 0
    for N, a in cases:
        record, _ = run_q1(a, N, args.shots, cross_check=not args.no_cross_check)
        print_report(record)
        if args.save:
            QR.append_run(record)                            # validates against rule-4 schema
            print(f"saved to {QR.RUNS_PATH}")
        if record["result"]["factors"] is None:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
