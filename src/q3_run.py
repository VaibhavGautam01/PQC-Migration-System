"""
q3_run.py - run the Q3 Grover circuit against the toy cipher and record the evidence.

ONE "QUESTION" = a secret 8-bit key that the attacker does NOT give to the circuit.
The script uses the secret only to MAKE two known (plaintext, ciphertext) pairs, exactly as
an attacker would observe them. The circuit receives the pairs and nothing else.

WHAT A RUN DOES
---------------
  1. make the pairs from the secret key                        (toy_cipher.make_pairs)
  2. build the Grover circuit from the pairs only              (q3_grover.build_grover)
  3. run it on the Aer simulator with fixed seeds             rule 10
  4. read the answer ONLY from the measured counts: the most frequent key, then VERIFY it by
     encrypting the two plaintexts (a check, not a search)    rule 2
  5. compare the measured histogram with the sin^2 theory     rule 5 (chi-square)
  6. (optional) run the SAME gate list in the independent numpy emulator and compare it with
     theory                                                   rule 9 (second method)
  7. save the circuit diagram and an evidence record          rule 4 (with --save)
A SWEEP repeats step 2-7 for 0, 2, 4 ... 2*k_opt Grover rounds, so you can see the success
probability rise to ~100 % at k_opt (= 12 for one matching key) and fall again.

Commands (project root, venv active, one command per line):
  python -m src.q3_run --key 183                    # one run at the optimal number of rounds
  python -m src.q3_run --key 183 --iterations 5     # one run with 5 rounds
  python -m src.q3_run --key 183 --sweep --save     # the success-vs-iterations curve
  python -m src.q3_run --suite --save               # sweep for keys 183, 42 and 250

All results: Aer simulator, toy size. The cipher is a toy, not AES.
"""
import argparse
import json
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

from src import grover_emulator as EM                       # noqa: E402
from src import grover_theory as GT                         # noqa: E402
from src import quantum_runs as QR                          # noqa: E402
from src import shor_post as SP                             # noqa: E402  (chi-square helper)
from src.q3_grover import KEY, NUM_QUBITS, build_grover, grover_ops  # noqa: E402
from src.qconfig import BACKEND_LABEL, SEED                 # noqa: E402
# The classical cipher is used ONLY to make the attacker's pairs, to count the matching keys
# for the theory curve, and to verify the key the circuit measured. It is never given to the
# circuit builder.
from src.toy_cipher import NUM_KEYS, consistent, keys_matching, make_pairs  # noqa: E402

QUESTION_GROUP = "grover_toy_cipher_change_key"             # rule 6: runs that differ in the pairs
SUITE_KEYS = [183, 42, 250]
CROSS_CHECK_TOLERANCE = 1e-9
SWEEP_PATH = ROOT / "data" / "q3_sweep.json"


def save_diagram(pairs, key: int) -> str:
    """Save a drawing of ONE Grover round (the circuit repeats it k times) and return its path.

    Drawing all 12 rounds would be thousands of gates wide, so one round is drawn. The text
    drawing is always saved; a PNG is also tried (needs matplotlib).
    """
    qc = build_grover(pairs, 1, measure=True)
    folder = ROOT / "docs" / "circuits"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"q3_grover_one_round_key{key}"
    txt = folder / f"{stem}.txt"
    txt.write_text(str(qc.draw(output="text", fold=-1)), encoding="utf-8")
    try:
        png = folder / f"{stem}.png"
        qc.draw(output="mpl", filename=str(png), fold=-1)
        return png.relative_to(ROOT).as_posix()
    except Exception:                                       # no matplotlib: text is enough
        return txt.relative_to(ROOT).as_posix()


def emulator_cross_check(pairs, iterations: int, marked) -> dict:
    """Rule 9: run the same gate list in the independent numpy emulator and compare it to theory."""
    state = EM.emulate(grover_ops(pairs, iterations), NUM_QUBITS)
    probs = EM.register_probabilities(state, list(KEY))
    theory = GT.expected_distribution(iterations, marked, NUM_KEYS)
    worst = float(max(abs(p - t) for p, t in zip(probs, theory)))
    return {"method": "Aer sampling vs independent numpy emulator (same gate list) vs analytic theory",
            "max_abs_diff": worst, "tolerance": CROSS_CHECK_TOLERANCE,
            "agree": bool(worst < CROSS_CHECK_TOLERANCE)}


def run_q3(secret_key: int, iterations: int, shots: int = 2048, cross_check: bool = False,
           diagram_file: str = None):
    """Run one Grover experiment. Returns the evidence record."""
    pairs = make_pairs(secret_key)                          # what the attacker observes
    marked = keys_matching(pairs)                           # theory/verification only
    M = len(marked)

    qc = build_grover(pairs, iterations)                    # the circuit sees ONLY the pairs
    backend = AerSimulator(method="statevector")
    t0 = time.perf_counter()
    # optimization_level=0 keeps our gates exactly as built (no resynthesis of big gates)
    compiled = transpile(qc, backend, optimization_level=0, seed_transpiler=SEED)
    counts = backend.run(compiled, shots=shots, seed_simulator=SEED).result().get_counts()
    runtime = time.perf_counter() - t0
    counts = {str(k).replace(" ", ""): int(v) for k, v in counts.items()}

    # the answer comes from the measured counts only
    best_bits = max(counts, key=counts.get)
    found_key = int(best_bits, 2)
    verified = consistent(found_key, pairs)                 # check the candidate, don't search
    marked_set = set(marked)
    in_marked = sum(c for bits, c in counts.items() if int(bits, 2) in marked_set)

    probs = GT.expected_distribution(iterations, marked, NUM_KEYS)
    chi = SP.chi_square_vs_theory(counts, probs)
    record = {
        "run_id": f"q3-key{secret_key}-k{iterations}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}",
        "timestamp_utc": QR.now_utc(),
        "algorithm": "grover_toy_cipher",
        "question_group": QUESTION_GROUP,
        "inputs": {"pairs": [list(p) for p in pairs], "iterations": iterations, "key_bits": 8},
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
        "success_rate": in_marked / shots,
        "runtime_seconds": round(runtime, 3),
        "diagram_file": diagram_file or save_diagram(pairs, secret_key),
        "label": BACKEND_LABEL,
        "simulated": True,
        "result": {"found_key": found_key, "verified": bool(verified),
                   "matching_keys": M, "iterations": iterations},
        "chi_square": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in chi.items()},
        "notes": ("Q3: toy 8-bit-key cipher, oracle built from X/CNOT/Toffoli gates and the two "
                  "public pairs only. Toy cipher, not AES; real sizes use published estimates."),
    }
    if cross_check:
        record["cross_check"] = emulator_cross_check(pairs, iterations, marked)
    record["_theory_success"] = GT.success_probability(iterations, M, NUM_KEYS)   # removed on save
    return record


def sweep_iterations(M: int, step: int):
    """0, step, 2*step ... up to 2*k_opt, always including k_opt itself."""
    k_opt = GT.optimal_iterations(M, NUM_KEYS)
    ks = set(range(0, 2 * k_opt + 1, step)) | {k_opt}
    return sorted(ks)


def print_report(r: dict) -> None:
    k = r["inputs"]["iterations"]
    c = r["chi_square"]
    verdict = "consistent with theory" if c["p_value"] > 0.01 else "DOES NOT MATCH THEORY"
    print(f"k={k:2d} rounds | key found={r['result']['found_key']:3d} "
          f"verified={r['result']['verified']} | measured success={r['success_rate']:.3f} "
          f"theory={r['_theory_success']:.3f} | chi2 p={c['p_value']:.3f} ({verdict}) "
          f"| depth={r['depth']} | {r['runtime_seconds']} s")
    if "cross_check" in r:
        x = r["cross_check"]
        print(f"        numpy-emulator cross-check: max diff {x['max_abs_diff']:.2e} -> "
              f"{'AGREE' if x['agree'] else 'DISAGREE'}")


def save_sweep_data(secret_key: int, pairs, M: int, records: list) -> None:
    """Write the success-vs-iterations data to data/q3_sweep.json (merged by secret key)."""
    data = json.loads(SWEEP_PATH.read_text(encoding="utf-8")) if SWEEP_PATH.exists() else {}
    data[str(secret_key)] = {
        "label": BACKEND_LABEL, "pairs": [list(p) for p in pairs], "matching_keys": M,
        "k_opt": GT.optimal_iterations(M, NUM_KEYS),
        "points": [{"iterations": r["inputs"]["iterations"], "measured": r["success_rate"],
                    "theory": r["_theory_success"]} for r in records]}
    SWEEP_PATH.parent.mkdir(parents=True, exist_ok=True)
    SWEEP_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    try:                                                    # optional plot, needs matplotlib
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        ks = [p["iterations"] for p in data[str(secret_key)]["points"]]
        fig, ax = plt.subplots(figsize=(6, 3.5))
        ax.plot(ks, [p["theory"] for p in data[str(secret_key)]["points"]], "-", label="theory")
        ax.plot(ks, [p["measured"] for p in data[str(secret_key)]["points"]], "o", label="measured")
        ax.set_xlabel("Grover rounds")
        ax.set_ylabel("success probability")
        ax.set_title(f"Toy cipher, secret key {secret_key} ({BACKEND_LABEL})")
        ax.legend()
        fig.tight_layout()
        out = ROOT / "docs" / "circuits" / f"q3_sweep_key{secret_key}.png"
        fig.savefig(out, dpi=120)
        plt.close(fig)
        print(f"plot saved to {out.relative_to(ROOT).as_posix()}")
    except Exception:
        pass


def attack_one_key(secret_key: int, args) -> int:
    pairs = make_pairs(secret_key)
    M = len(keys_matching(pairs))
    k_opt = GT.optimal_iterations(M, NUM_KEYS)
    print(f"\n=== Q3 Grover | secret key {secret_key} (hidden from the circuit) | pairs {pairs} "
          f"| {M} matching key(s), k_opt={k_opt} | {BACKEND_LABEL} ===")
    if args.sweep:
        ks = sweep_iterations(M, args.step)
    else:
        ks = [args.iterations if args.iterations is not None else k_opt]
    diagram = save_diagram(pairs, secret_key)
    records, exit_code = [], 0
    for k in ks:
        rec = run_q3(secret_key, k, args.shots,
                     cross_check=(k == k_opt and not args.no_cross_check), diagram_file=diagram)
        print_report(rec)
        records.append(rec)
        if k == k_opt and not rec["result"]["verified"]:
            exit_code = 1
    if args.save:
        for rec in records:
            to_save = {k: v for k, v in rec.items() if not k.startswith("_")}
            QR.append_run(to_save)                          # validates against the rule-4 schema
        print(f"saved {len(records)} evidence record(s) to {QR.RUNS_PATH}")
        if args.sweep:
            save_sweep_data(secret_key, pairs, M, records)
    return exit_code


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--key", type=int, help="secret key 0..255 used to make the known pairs")
    ap.add_argument("--iterations", type=int, help="number of Grover rounds (default: optimal)")
    ap.add_argument("--sweep", action="store_true", help="run 0 .. 2*k_opt rounds")
    ap.add_argument("--step", type=int, default=2, help="round step for --sweep (default 2)")
    ap.add_argument("--shots", type=int, default=2048)
    ap.add_argument("--suite", action="store_true", help=f"sweep keys {SUITE_KEYS}")
    ap.add_argument("--no-cross-check", action="store_true", help="skip the numpy-emulator check")
    ap.add_argument("--save", action="store_true", help="append evidence to data/quantum_runs.json")
    args = ap.parse_args()

    if args.suite:
        args.sweep = True
        keys = SUITE_KEYS
    elif args.key is not None:
        keys = [args.key]
    else:
        ap.error("give --key (0..255) or use --suite")
    if any(not 0 <= k < NUM_KEYS for k in keys):
        ap.error("the key must be between 0 and 255")

    code = 0
    for k in keys:
        code |= attack_one_key(k, args)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
