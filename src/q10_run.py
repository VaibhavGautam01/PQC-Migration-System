"""
q10_run.py - run Q10 (Shor's algorithm for the discrete log) and record the evidence.

!!! RUN THIS FIRST, BEFORE ANYTHING ELSE IN THIS FILE !!!
------------------------------------------------------------
    python -m src.q10_run --self-test
This runs one known instance (p=11, g=2, x=3, so h=8) and checks the circuit recovers x=3.

HISTORY: two earlier attempts at parse_counts() below (first assuming two separate classical
registers with one Qiskit ordering convention, then a single combined register with another
assumed convention) both turned out to be backwards, caught only by checking real measured
data against theory by hand. The CURRENT version is empirically verified, not just reasoned
about: see parse_counts()'s docstring for exactly how. A small-order self-test alone (like
p=11, order r=10) is NOT reliable proof by itself - with only 10 possible values, a WRONG
interpretation has about a 1-in-10 chance of accidentally passing verification when checked
against the hundreds of distinct outcomes a real run produces, as apparently happened here
across two different wrong versions of this function. Trust a larger-order instance (such as
the p=23 ones, order r=22, where a wrong interpretation matching by pure chance is far less
likely) for genuine confidence, not --self-test alone.

WHAT A NORMAL RUN DOES, for public (p, g, h) with secret x hidden in h = g^x mod p
------------------------------------------------------------------------------------
  1. STAGE 1 (order finding): find r = order of g mod p with Q1's existing Shor circuit
     (src.q1_run.run_q1), run on Aer. This is a REAL quantum circuit call, not a shortcut -
     the same circuit that factors N=15/21/35 for Q1.
  2. STAGE 2 (the two-register circuit, q10_dlog.py): run on Aer, get measured (y_a, y_b) pairs.
  3. classical post-processing (dlog_post.py), using ONLY the measured counts and r: recover x,
     verified by checking g**x % p == h.
  4. chi-square test against theory (rule 5) and, for small enough circuits, an exact
     statevector cross-check (rule 9).
  5. save the diagram and an evidence record (rule 4), with --save.

Commands (project root, venv active, one command per line):
  python -m src.q10_run --self-test                         # run this first
  python -m src.q10_run --p 11 --g 2 --x 3                  # one instance, x given (for the demo;
                                                              # a real attacker would not know x)
  python -m src.q10_run --p 23 --g 5 --x 7 --save
  python -m src.q10_run --suite --save                      # a few small instances

All results: Aer simulator, toy size. p is a small prime (p <= 31 keeps the work register at
<= 5 bits and the whole circuit under ~20 qubits with the default counting-qubit count).
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
import qiskit_aer                                            # noqa: E402
from qiskit import transpile                                 # noqa: E402
from qiskit.quantum_info import Statevector                   # noqa: E402
from qiskit_aer import AerSimulator                           # noqa: E402

from src import dlog_post as DP                                # noqa: E402
from src import quantum_runs as QR                             # noqa: E402
from src import shor_post as SP                                 # noqa: E402
from src.q10_dlog import build_dlog, default_counting_bits, layout  # noqa: E402
from src.q1_run import run_q1                                   # noqa: E402  (stage 1: order finding)
from src.qconfig import BACKEND_LABEL, SEED                      # noqa: E402

QUESTION_GROUP = "dlog_change_g_h"           # rule 6: runs that differ only in (g, h), same p
SUITE = [(11, 2, 3), (23, 5, 7), (23, 5, 19)]
SELF_TEST = (11, 2, 3)                       # the instance verified by hand before this file existed
CROSS_CHECK_MAX_QUBITS = 20


def parse_counts(raw_counts: dict, t: int) -> dict:
    """Clean up Aer's raw single-register {"<2t-bit string>": count} keys for dlog_post.py,
    which expects {"ya_bits + yb_bits": count} (t characters each, register A's bits first).

    EMPIRICALLY VERIFIED (not just reasoned from a Qiskit convention - an earlier version of
    this function assumed the opposite and was proven wrong by real measured data): the first
    t characters of Aer's raw key ARE already register A's value and the last t characters
    ARE already register B's value, in the SAME order q10_dlog.py's measure(A + B, out) call
    put them in. So this function is close to a pass-through; it only strips a stray space
    (seen in some Qiskit versions when a circuit uses just one classical register).

    How this was verified: for p=23, g=5, h=17 (secret x=7, order r=22), checking the raw
    measured bits directly (no transformation) against src/dlog_post.py's recovery formula
    correctly found x=7 on every one of the 5 non-degenerate, coprime-vote outcomes tried
    (5/5), while every other tested bit-ordering hypothesis (swapped halves, either half bit-
    reversed, both swapped and reversed) found x=7 on 0 of those same 5 outcomes - not a
    plausible coincidence.
    """
    out = {}
    for key, count in raw_counts.items():
        key = key.replace(" ", "")                     # tolerate a stray space, just in case
        out[key] = out.get(key, 0) + int(count)
    return out


def find_order(g: int, p: int, shots: int = 4096):
    """Stage 1: the order r of g mod p, via Q1's existing Shor circuit (reused unchanged).

    Q1's own run_q1() reports a period only when it ALSO finds non-trivial factors
    (src/shor_post.py analyse_counts: "the period with the most votes that ALSO yields
    factors"). That is right for Q1's own job - factoring a semiprime - but p here is PRIME,
    so there are never non-trivial factors to find, and record["result"]["period"] stays None
    even though the circuit measured the order correctly. (Verified: for a=2, p=11, a realistic
    simulated run gives votes={10: ~85% of shots}, i.e. the order IS found in the raw vote
    tally; Q1's gated "period" field is simply None.) So this function re-derives the order
    from the SAME measured counts directly, via the vote tally shor_post.analyse_counts
    already computes - still only the measured counts and continued-fraction post-processing
    (rule 2), just not gated behind "also factors something".
    """
    record, _ = run_q1(g, p, shots, cross_check=False)
    m = record["inputs"]["counting_qubits"]
    votes = SP.analyse_counts(record["counts"], m, g, p)["votes"]
    if not votes:
        raise RuntimeError(f"order-finding circuit did not resolve the order of {g} mod {p}; "
                           f"try more shots")
    r = max(votes, key=votes.get)
    record["result"]["period"] = r                   # keep the evidence record consistent
    return r, record


def save_diagram(qc, stem: str) -> str:
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


def run_dlog(g: int, h: int, p: int, r: int, shots: int = 4096, t: int = None,
            cross_check: bool = True):
    """Run stage 2 for a known r. Returns the evidence record."""
    t = t or default_counting_bits(p)
    qc = build_dlog(g, h, p, t)
    backend = AerSimulator(method="statevector")
    t0 = time.perf_counter()
    compiled = transpile(qc, backend, optimization_level=0, seed_transpiler=SEED)
    raw_counts = backend.run(compiled, shots=shots, seed_simulator=SEED).result().get_counts()
    runtime = time.perf_counter() - t0
    raw_counts = {str(k): int(v) for k, v in raw_counts.items()}
    print("    [debug] raw Aer count keys, top 5:",
          sorted(raw_counts.items(), key=lambda kv: -kv[1])[:5])
    counts = parse_counts(raw_counts, t)

    found = DP.analyse_counts(counts, t, r, g, h, p)
    stem = f"q10_dlog_p{p}_g{g}"
    record = {
        "run_id": f"q10-p{p}-g{g}-h{h}-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}",
        "timestamp_utc": QR.now_utc(),
        "algorithm": "shor_dlog",
        "question_group": QUESTION_GROUP,
        "inputs": {"p": p, "g": g, "h": h, "order_r": r, "counting_qubits_per_register": t},
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
        "label": BACKEND_LABEL,
        "simulated": True,
        "result": {"x": found["x"], "order_r": r},
        "notes": ("Q10: two-register phase estimation for the discrete log, reusing Q1's "
                  "controlled-modmul and inverse-QFT building blocks. r comes from a separate "
                  "Q1 order-finding circuit run (see the linked q1 run_id), not assumed."),
    }
    if cross_check and compiled.num_qubits <= CROSS_CHECK_MAX_QUBITS:
        # EXACT cross-check (rule 9), independent of Aer sampling and of how Qiskit names
        # classical registers in count-key strings. Statevector.probabilities(qargs) indexes
        # its output with qargs[0] as the LEAST significant bit, so with qargs = A-qubits then
        # B-qubits: idx's low t bits = register A's value, idx's high t bits = register B's.
        qc_exact = build_dlog(g, h, p, t, measure=False)
        lay = layout(p, t)
        exact = Statevector(qc_exact).probabilities(lay["A"] + lay["B"])
        T = 2 ** t
        max_prob = float(exact.max())
        # TIES: when r is even, j=0 and j=r/2 give exactly tied top theoretical probability
        # (seen in practice: p=11 ties (0,0) with (128,128) at 1/r each), so a run's measured
        # top count can legitimately land on EITHER by sampling noise. Accept any outcome
        # within 1e-6 of the true maximum, not just one arbitrarily chosen tied index.
        theory_top_keys = {format(idx & (T - 1), f"0{t}b") + format(idx >> t, f"0{t}b")
                           for idx in range(T * T) if exact[idx] >= max_prob - 1e-9}
        measured_top = max(counts, key=counts.get) if counts else None
        record["cross_check"] = {
            "method": "exact statevector top outcome(s) vs Aer-measured top outcome",
            "theory_top_outcomes": sorted(theory_top_keys), "theory_top_probability": round(max_prob, 6),
            "measured_top_outcome": measured_top, "agree": bool(measured_top in theory_top_keys)}
    return record, qc


def print_report(r: dict) -> None:
    i = r["inputs"]
    print(f"\n=== Q10 discrete log | p={i['p']} g={i['g']} h={i['h']} (order r={i['order_r']}) "
          f"| {r['label']} ===")
    print(f"qubits={r['qubits']}  depth={r['depth']}  shots={r['shots']}  "
          f"time={r['runtime_seconds']} s")
    print(f"x recovered from measurements : {r['result']['x']}")
    print(f"verified: g^x mod p == h      : {pow(i['g'], r['result']['x'], i['p']) == i['h'] if r['result']['x'] is not None else 'N/A (no x found)'}")
    print(f"shots whose single measurement alone gave a verified x : {r['success_rate']:.1%}")
    print(f"diagram saved to              : {r['diagram_file']}")
    if r["result"]["x"] is None:
        top = sorted(r["counts"].items(), key=lambda kv: -kv[1])[:10]
        print("NO x FOUND - top 10 measured outcomes (ya+yb bits, count):")
        for bits, c in top:
            print(f"    {bits}  count={c}")
        print(f"    total distinct outcomes measured: {len(r['counts'])}")


def self_test() -> int:
    p, g, x = SELF_TEST
    h = pow(g, x, p)
    print(f"=== Q10 self-test: p={p}, g={g}, secret x={x} (so h=g^x mod p = {h}) ===")
    print("Finding the order of g with Q1's circuit ...")
    r, order_rec = find_order(g, p)
    print(f"  order r = {r}  (expected 10)")
    print("Running the Q10 two-register circuit ...")
    record, _ = run_dlog(g, h, p, r)
    print_report(record)
    ok = record["result"]["x"] == x
    print("\nSELF-TEST:", "PASS" if ok else "FAIL - see the note at the top of this file")
    print("Caveat: with only r=10 possible values here, a WRONG bit-ordering interpretation "
          "has roughly a 1-in-10 chance of accidentally passing this check (verified against "
          "hundreds of measured outcomes). A clean pass on a larger-order instance, e.g. "
          "`python -m src.q10_run --p 23 --g 5 --x 7`, is much stronger evidence.")
    if not ok:
        print("Measured (ya+yb) counts, top 10:",
              sorted(record["counts"].items(), key=lambda kv: -kv[1])[:10])
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true", help="run the known-answer check first")
    ap.add_argument("--p", type=int, help="prime modulus")
    ap.add_argument("--g", type=int, help="generator (base)")
    ap.add_argument("--x", type=int, help="secret exponent, FOR THE DEMO ONLY (used to build h; "
                    "a real attacker would not have this)")
    ap.add_argument("--h", type=int, help="public h = g^x mod p (give this INSTEAD of --x for a "
                    "genuine 'unknown x' run)")
    ap.add_argument("--shots", type=int, default=4096)
    ap.add_argument("--suite", action="store_true", help=f"run the built-in instances {SUITE}")
    ap.add_argument("--save", action="store_true", help="append evidence to data/quantum_runs.json")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    if args.suite:
        cases = SUITE
    elif args.p and args.g and (args.x is not None or args.h is not None):
        h = args.h if args.h is not None else pow(args.g, args.x, args.p)
        cases = [(args.p, args.g, args.x if args.x is not None else "unknown")]
        h_override = {cases[0]: h}
    else:
        ap.error("give --self-test, or --p/--g with --x or --h, or --suite")

    exit_code = 0
    for p, g, x in cases:
        h = pow(g, x, p) if isinstance(x, int) else locals().get("h_override", {}).get((p, g, x))
        DP.check_inputs(g, h, p)
        r, _ = find_order(g, p, args.shots)
        record, _ = run_dlog(g, h, p, r, args.shots)
        print_report(record)
        if isinstance(x, int):
            print(f"known secret x was: {x}  ->  {'MATCH' if record['result']['x'] == x else 'MISMATCH'}")
        if args.save:
            QR.append_run(record)
            print(f"saved to {QR.RUNS_PATH}")
        if record["result"]["x"] is None:
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
