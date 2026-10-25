"""
q11_run.py - run Q11: count the matching keys with quantum counting, then search with Grover.

For each target number of matching keys M (default 1, 2 and 3) the script
  1. MAKES THE QUESTION: a known (plaintext, ciphertext) pair for which exactly M candidate keys
     fit (counting_theory.find_pair_with_matches). The attacker's circuit is NOT told M.
  2. COUNTS: builds the quantum-counting circuit from the pair only, runs it on the Aer simulator,
     and estimates M from the measured counting register (maximum likelihood on the counts).
  3. COMPARES the measured histogram with the ideal one (chi-square, rule 5) and, when the circuit
     is small enough, with the independent numpy emulator (rule 9).
  4. SEARCHES: runs Grover with the rounds chosen from the ESTIMATED M, and for comparison with
     the rounds a naive attacker would use if he assumed one matching key. It checks every found
     key by encrypting (a check, not a search).
  5. saves diagrams and evidence records with --save (rule 4).

WHY step 4 compares two choices: with M = 3 matching keys, 6 rounds (right for M = 1 among 64
candidates) OVERSHOOTS and the success probability falls to a few percent. The counted M
gives the right number of rounds and success close to 1.

Commands (project root, venv active, one command per line):
  python -m src.q11_run --free-bits 4 --counting-bits 5            # quick check, ~18 qubits
  python -m src.q11_run                                           # default: 6 free bits, 7 counting qubits (22 qubits)
  python -m src.q11_run --targets 1 2 --save                      # save evidence records
  python -m src.q11_run --known-value 2 --shots 4096

Size guide: qubits = free bits + 9 + counting qubits. The default of 22 qubits needs roughly
64 MB of memory and a few minutes per instance in Aer. The numpy emulator cross-check is only run
up to 20 qubits.

All results: Aer simulator, toy size. The cipher is a toy; this is a simulation of the algorithm,
not a speed-up claim.
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
from qiskit_aer import AerSimulator                         # noqa: E402

from src import counting_theory as CT                       # noqa: E402
from src import grover_emulator as EM                       # noqa: E402
from src import grover_theory as GT                         # noqa: E402
from src import quantum_runs as QR                          # noqa: E402
from src import shor_post as SP                             # noqa: E402  (chi-square helper)
from src.q11_counting import (build_counting, build_grover, counting_ops, layout,  # noqa: E402
                              ops_to_circuit)
from src.qconfig import BACKEND_LABEL, SEED                 # noqa: E402
# Classical cipher: used ONLY to verify a measured key. Never given to the circuit builder.
from src.toy_cipher import consistent                       # noqa: E402

COUNT_GROUP = "quantum_counting_change_M"                   # rule 6: runs that differ in the pair
SEARCH_GROUP = "grover_after_counting"
EMULATOR_MAX_QUBITS = 20


def save_diagram(qc, stem: str) -> str:
    """Save a text drawing (and a PNG if matplotlib is installed) under docs/circuits/."""
    folder = ROOT / "docs" / "circuits"
    folder.mkdir(parents=True, exist_ok=True)
    txt = folder / f"{stem}.txt"
    txt.write_text(str(qc.draw(output="text", fold=-1)), encoding="utf-8")
    try:
        png = folder / f"{stem}.png"
        qc.draw(output="mpl", filename=str(png), fold=-1)
        return png.relative_to(ROOT).as_posix()
    except Exception:
        return txt.relative_to(ROOT).as_posix()


def run_aer(qc, shots):
    """Transpile (no resynthesis) and run on Aer with the fixed seeds (rule 10)."""
    backend = AerSimulator(method="statevector")
    t0 = time.perf_counter()
    compiled = transpile(qc, backend, optimization_level=0, seed_transpiler=SEED)
    counts = backend.run(compiled, shots=shots, seed_simulator=SEED).result().get_counts()
    counts = {str(k).replace(" ", ""): int(v) for k, v in counts.items()}
    return compiled, counts, time.perf_counter() - t0


def base_record(compiled, counts, shots, runtime, algorithm, group, inputs, result, chi, notes,
                diagram, success_rate):
    """The evidence record fields shared by every Q11 run (rule 4)."""
    return {
        "run_id": f"q11-{algorithm}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}",
        "timestamp_utc": QR.now_utc(),
        "algorithm": algorithm, "question_group": group, "inputs": inputs,
        "qubits": compiled.num_qubits, "depth": compiled.depth(),
        "gate_counts": {str(k): int(v) for k, v in compiled.count_ops().items()},
        "shots": shots, "backend": "AerSimulator",
        "backend_version": qiskit_aer.__version__, "qiskit_version": qiskit.__version__,
        "seed_simulator": SEED, "seed_transpiler": SEED, "counts": counts,
        "success_rate": success_rate, "runtime_seconds": round(runtime, 3),
        "diagram_file": diagram, "label": BACKEND_LABEL, "simulated": True,
        "result": result,
        "chi_square": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in chi.items()},
        "notes": notes,
    }


def count_matches(pair, free, known, t, shots, true_M):
    """Run quantum counting for one pair. Returns (record, estimated M)."""
    N = 2 ** free
    qc = build_counting(pair, free, known, t)
    compiled, counts, runtime = run_aer(qc, shots)
    est = CT.estimate_count_ml(counts, N, t)                 # M from the measured counts only
    peak = CT.estimate_count(counts, N, t)
    theory = CT.counting_distribution(true_M, N, t)          # ideal histogram, for comparison only
    chi = SP.chi_square_vs_theory(counts, theory)
    right = peak["shots_per_estimate"].get(str(true_M), 0) / shots
    diagram = save_diagram(ops_to_circuit(counting_ops(pair, free, known, 1), layout(free, 1)["n"],
                                          layout(free, 1)["counting"]),
                           f"q11_counting_one_controlled_G_M{true_M}")
    inputs = {"pair": list(pair), "free_key_bits": free, "known_key_bits_value": known,
              "counting_qubits": t}
    result = {"estimated_matches": est["estimate"], "peak_outcome": peak["peak_outcome"],
              "peak_estimate_raw": round(peak["estimate_raw"], 3), "true_matches": true_M}
    notes = (f"Q11 quantum counting on the toy cipher with {free} free key bits "
             f"(N={N}); circuit sees only the pair, never M. true_matches is for comparison only. "
             f"Diagram shows ONE controlled Grover iterate (the circuit applies it 2^t - 1 times). "
             f"success_rate = shots whose own rounded estimate equals the true count.")
    record = base_record(compiled, counts, shots, runtime, "quantum_counting", COUNT_GROUP,
                         inputs, result, chi, notes, diagram, right)
    if compiled.num_qubits <= EMULATOR_MAX_QUBITS:           # rule 9: second method
        state = EM.emulate(counting_ops(pair, free, known, t), layout(free, t)["n"])
        probs = EM.register_probabilities(state, layout(free, t)["counting"])
        worst = float(max(abs(p - q) for p, q in zip(probs, theory)))
        record["cross_check"] = {"method": "Aer sampling vs independent numpy emulator vs analytic theory",
                                 "max_abs_diff": worst, "tolerance": 1e-9, "agree": bool(worst < 1e-9)}
    return record, est["estimate"]


def search(pair, free, known, k, shots, assumed_M, true_M, label):
    """Run Grover with k rounds. Returns the evidence record."""
    N = 2 ** free
    qc = build_grover(pair, free, known, k)
    compiled, counts, runtime = run_aer(qc, shots)
    best = max(counts, key=counts.get)
    found = (known << free) | int(best, 2)                   # full 8-bit key = known high bits + found low bits
    verified = consistent(found, [tuple(pair)])              # check the candidate, don't search
    true_keys = CT.matching_free_keys(pair, free, known)     # theory only: which outcomes count as success
    hit = sum(c for b, c in counts.items() if int(b, 2) in set(true_keys)) / shots
    theory_p = GT.success_probability(k, true_M, N)
    stem = f"q11_grover_one_round_M{true_M}"
    diagram = save_diagram(build_grover(pair, free, known, 1), stem)
    inputs = {"pair": list(pair), "free_key_bits": free, "known_key_bits_value": known,
              "iterations": k, "assumed_matches": assumed_M}
    result = {"found_key": found, "verified": bool(verified), "iterations": k,
              "success_theory": round(theory_p, 4), "choice": label}
    chi = SP.chi_square_vs_theory(counts, GT.expected_distribution(k, true_keys, N))
    notes = (f"Q11 follow-up Grover search; rounds chosen from an assumed match count "
             f"({label}). Toy cipher, Aer simulator, toy size.")
    return base_record(compiled, counts, shots, runtime, "grover_after_counting", SEARCH_GROUP,
                       inputs, result, chi, notes, diagram, hit)


def run_target(M, args):
    free, known, t, shots = args.free_bits, args.known_value, args.counting_bits, args.shots
    N = 2 ** free
    pair = CT.find_pair_with_matches(M, free, known)
    if pair is None:
        print(f"\n--- M={M}: this toy cipher has no pair with exactly {M} matching keys "
              f"for {free} free key bits; skipped ---")
        return []
    true_M = len(CT.matching_free_keys(pair, free, known))
    print(f"\n=== Q11 | pair {pair} | {N} candidate keys | true matches {true_M} (hidden from the "
          f"circuit) | {BACKEND_LABEL} ===")
    count_rec, est = count_matches(pair, free, known, t, shots, true_M)
    c = count_rec["chi_square"]
    print(f"quantum counting: {count_rec['qubits']} qubits, depth {count_rec['depth']}, "
          f"{count_rec['runtime_seconds']} s | peak outcome {count_rec['result']['peak_outcome']} | "
          f"ESTIMATED matches = {est} (true {true_M}) | chi2 p={c['p_value']:.3f} "
          f"({'consistent with theory' if c['p_value'] > 0.01 else 'DOES NOT MATCH THEORY'})")
    if "cross_check" in count_rec:
        x = count_rec["cross_check"]
        print(f"   numpy-emulator cross-check: max diff {x['max_abs_diff']:.2e} -> "
              f"{'AGREE' if x['agree'] else 'DISAGREE'}")
    records = [count_rec]
    k_est, k_naive = CT.iterations_for(est, N), CT.iterations_for(1, N)
    for k, assumed, label in ((k_est, est, "rounds from the COUNTED M"),
                              (k_naive, 1, "rounds if one match is assumed")):
        if label.startswith("rounds if") and k_naive == k_est:
            continue
        rec = search(pair, free, known, k, shots, assumed, true_M, label)
        print(f"Grover, {label}: k={k} | key found {rec['result']['found_key']} "
              f"verified={rec['result']['verified']} | measured success {rec['success_rate']:.3f} "
              f"(theory {rec['result']['success_theory']:.3f}) | chi2 p={rec['chi_square']['p_value']:.3f}")
        records.append(rec)
    return records


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--free-bits", type=int, default=6, help="unknown key bits (default 6 -> N=64)")
    ap.add_argument("--counting-bits", type=int, default=7, help="counting qubits t (default 7)")
    ap.add_argument("--known-value", type=int, default=0,
                    help="value of the known high key bits (default 0)")
    ap.add_argument("--targets", type=int, nargs="+", default=[1, 2, 3],
                    help="numbers of matching keys to test (default 1 2 3)")
    ap.add_argument("--shots", type=int, default=2048)
    ap.add_argument("--save", action="store_true", help="append evidence to data/quantum_runs.json")
    args = ap.parse_args()
    if not 1 <= args.free_bits <= 7 or args.known_value >= 2 ** (8 - args.free_bits):
        ap.error("free bits must be 1..7 and known-value must fit in the remaining key bits")

    all_records, bad = [], 0
    for M in args.targets:
        recs = run_target(M, args)
        all_records += recs
        if recs and not all(r["result"].get("verified", True) for r in recs[1:2]):
            bad += 1
    if args.save and all_records:
        for rec in all_records:
            QR.append_run(rec)                               # validates against the rule-4 schema
        print(f"\nsaved {len(all_records)} evidence record(s) to {QR.RUNS_PATH}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
