"""
q1_demo_batch.py - run every Q1 Shor case MANY times and save the results to
data/demo_results.json (Week 2 Day 2: "save counts with a script, not by hand").

WHY RUN EACH CASE MANY TIMES?
-----------------------------
One run of a quantum circuit is a random sample. A single run that happens to give the right
answer proves little. Repeating the same circuit R times with R different simulator seeds
shows how reliably it works: how many repeats found the factors, and whether the pooled
histogram of all repeats still matches the theory (chi-square, rule 5).

WHAT IT DOES
------------
For each question (N, a):
  1. repeat R times: same circuit, seed = SEED + i, SHOTS shots each         rule 10
  2. per repeat, post-process ONLY the measured counts (shor_post)           rule 2
  3. add all repeats together and run the chi-square test against theory     rule 5
  4. write the details (versions, seeds, per-repeat results, most frequent outcomes, pooled
     chi-square) to data/q1_batch_results.json
  5. merge ONE summary line per N into data/demo_results.json in the format the dashboard
     reads (see demo_results_io.py). The dashboard needs whole-number "runs" and "successes",
     so the detailed file is kept separate and the shared file is never overwritten.

Commands (project root, venv active, one command per line):
  python -m src.q1_demo_batch                          # 4 cases x 20 repeats x 2048 shots
  python -m src.q1_demo_batch --repeats 50 --shots 4096
  python -m src.q1_demo_batch --N 21 --a 2 --repeats 10    # one case, print only unless --save
  python -m src.q1_demo_batch --save                   # write both files (details + dashboard summary)
  python -m src.q1_demo_batch --save-detail-only       # write only data/q1_batch_results.json

All results: Aer simulator, toy size. The theory curve uses the classical period only AFTER
the run, to compare; the circuit never sees it.
"""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import qiskit                                               # noqa: E402
import qiskit_aer                                           # noqa: E402
from qiskit import transpile                                # noqa: E402
from qiskit_aer import AerSimulator                         # noqa: E402

from src import demo_results_io as DRIO                     # noqa: E402
from src import shor_post as SP                             # noqa: E402
from src.q1_shor_pe import build_shor_pe, default_counting_bits  # noqa: E402
from src.qconfig import BACKEND_LABEL, SEED                 # noqa: E402

CASES = [(15, 7), (15, 2), (21, 2), (35, 2)]
DETAIL_PATH = ROOT / "data" / "q1_batch_results.json"       # full details of every repeat
DEMO_PATH = ROOT / "data" / "demo_results.json"             # dashboard format, one line per N


def run_case(a: int, N: int, repeats: int, shots: int) -> dict:
    """Repeat one Shor question `repeats` times with seeds SEED, SEED+1, ... and summarise."""
    SP.check_inputs(a, N)
    m = default_counting_bits(N)
    qc = build_shor_pe(a, N, m)                             # the same circuit every repeat
    backend = AerSimulator(method="statevector")

    pooled, runs, period_votes, factor_votes = {}, [], {}, {}
    t0 = time.perf_counter()
    for i in range(repeats):
        seed = SEED + i                                     # a different, recorded seed per repeat
        compiled = transpile(qc, backend, optimization_level=0, seed_transpiler=seed)
        counts = backend.run(compiled, shots=shots, seed_simulator=seed).result().get_counts()
        counts = {str(k).replace(" ", ""): int(v) for k, v in counts.items()}
        for bits, c in counts.items():                      # add this repeat to the pooled histogram
            pooled[bits] = pooled.get(bits, 0) + c
        found = SP.analyse_counts(counts, m, a, N)          # answer from measured counts only
        runs.append({"seed": seed, "period": found["period"], "factors": found["factors"],
                     "shot_success_rate": round(found["success_rate"], 4),
                     "shots_with_factors": int(round(found["success_rate"] * shots))})
        period_votes[str(found["period"])] = period_votes.get(str(found["period"]), 0) + 1
        key = "none" if not found["factors"] else "x".join(map(str, found["factors"]))
        factor_votes[key] = factor_votes.get(key, 0) + 1
    elapsed = time.perf_counter() - t0

    probs = SP.theoretical_distribution(a, N, m)            # theory, for comparison only
    chi = SP.chi_square_vs_theory(pooled, probs)
    top = sorted(pooled.items(), key=lambda kv: -kv[1])[:8]
    return {
        "N": N, "a": a, "counting_qubits": m, "qubits": qc.num_qubits,
        "repeats": repeats, "shots_per_repeat": shots,
        "repeats_finding_factors": sum(1 for r in runs if r["factors"]),
        "period_found_in_repeats": period_votes,
        "factors_found_in_repeats": factor_votes,
        "mean_shot_success_rate": round(sum(r["shot_success_rate"] for r in runs) / repeats, 4),
        "pooled_chi_square": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in chi.items()},
        "top_outcomes": [{"y": int(b, 2), "count": c} for b, c in top],
        "runs": runs,
        "total_seconds": round(elapsed, 2),
    }


def print_case(c: dict) -> None:
    p = c["pooled_chi_square"]["p_value"]
    print(f"N={c['N']:>2} a={c['a']}: {c['repeats_finding_factors']}/{c['repeats']} repeats found "
          f"the factors {c['factors_found_in_repeats']} | periods {c['period_found_in_repeats']} | "
          f"mean per-shot success {c['mean_shot_success_rate']:.0%} | pooled chi-square p={p:.3f} "
          f"({'consistent with theory' if p > 0.01 else 'DOES NOT MATCH'}) | {c['total_seconds']} s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--N", type=int)
    ap.add_argument("--a", type=int)
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument("--shots", type=int, default=2048)
    ap.add_argument("--save", action="store_true",
                    help=f"write {DETAIL_PATH.relative_to(ROOT)} and merge a summary into "
                         f"{DEMO_PATH.relative_to(ROOT)}")
    ap.add_argument("--save-detail-only", action="store_true",
                    help=f"write only {DETAIL_PATH.relative_to(ROOT)}; leave demo_results.json alone")
    args = ap.parse_args()

    cases = [(args.a, args.N)] if args.N and args.a else [(a, N) for N, a in CASES]
    results = []
    for a, N in cases:
        case = run_case(a, N, args.repeats, args.shots)
        print_case(case)
        results.append(case)

    versions = f"Qiskit {qiskit.__version__}, qiskit-aer {qiskit_aer.__version__}"
    if args.save or args.save_detail_only:
        DETAIL_PATH.parent.mkdir(parents=True, exist_ok=True)
        DETAIL_PATH.write_text(json.dumps({
            "schema_version": 1,
            "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generated_by": "python -m src.q1_demo_batch",
            "label": BACKEND_LABEL,
            "backend": "AerSimulator (statevector)",
            "qiskit_version": qiskit.__version__,
            "qiskit_aer_version": qiskit_aer.__version__,
            "seed_policy": f"repeat i uses seed_simulator = seed_transpiler = {SEED} + i",
            "note": ("Each repeat is a separate run of the same circuit; single-run evidence "
                     "records are in data/quantum_runs.json. Aer simulator, toy size."),
            "cases": results}, indent=2) + "\n", encoding="utf-8")
        print(f"saved {DETAIL_PATH}")
    if args.save:
        DRIO.merge_into_demo_results(DEMO_PATH, results, SEED, versions)
        print(f"merged one summary line per N into {DEMO_PATH} (dashboard format)")
    return 0 if all(c["repeats_finding_factors"] > 0 for c in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
