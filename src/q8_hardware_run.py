"""
q8_hardware_run.py - Week 5 Day 1: run a REAL tiny circuit on IBM Quantum hardware, if
access is confirmed, and compare it with the Aer simulator and (optionally) a noise model.

WHAT IT RUNS
-------------
A single qubit, Hadamard then measure - the smallest honest "real randomness" demonstration
(matches Q7's scope: "A one-qubit circuit"). This keeps real hardware runtime to a few
seconds and a handful of shots, respecting the very limited free-tier runtime the plan notes
(IBM's Open Plan: up to about 10 minutes per month, when last checked - confirm your own
account's current limit with src/q8_check_access.py before running this).

WHY SO SMALL
-------------
Q8's own scope (Section 10) is "small circuits (Q7, a 2 to 3 qubit Grover, a tiny Q1 case)",
not a full demonstration - real hardware time is scarce and shared across the team. This
script runs the Q7-sized case; extending it to a tiny Q1 or Grover case is a copy of this
same pattern with a different circuit, once this one is confirmed working and the team has
agreed to spend more of the monthly runtime budget on it.

BEFORE RUNNING THIS
---------------------
    python -m src.q8_check_access
must show a reachable service and at least one operational backend. This script does not
repeat that check in detail; it fails early and clearly if the service is not reachable.

Usage (from the project root, venv active):
  python -m src.q8_hardware_run --dry-run              # build + transpile only, submit nothing
  python -m src.q8_hardware_run                         # real hardware run (uses runtime budget)
  python -m src.q8_hardware_run --shots 256 --save      # save the evidence record

HONEST LABELLING
-----------------
Every result from this script is labelled with the REAL backend name it ran on, never "Aer
simulator, toy size" - rule 11 requires every quantum result to say where it actually ran.
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


def build_circuit():
    """The circuit: H then measure, on one qubit. Matches Q7's scope exactly."""
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
    qr = QuantumRegister(1, "q")
    cr = ClassicalRegister(1, "c")
    qc = QuantumCircuit(qr, cr, name="q8_single_qubit_hadamard")
    qc.h(qr[0])
    qc.measure(qr[0], cr[0])
    return qc


def run_on_aer(qc, shots: int):
    """The same circuit on the Aer simulator, for comparison (not the hardware run itself)."""
    from qiskit import transpile
    from qiskit_aer import AerSimulator
    from src.qconfig import SEED
    backend = AerSimulator()
    compiled = transpile(qc, backend, optimization_level=0, seed_transpiler=SEED)
    counts = backend.run(compiled, shots=shots, seed_simulator=SEED).result().get_counts()
    return {str(k): int(v) for k, v in counts.items()}


def pick_backend(service):
    """The least-busy OPERATIONAL backend with at least 1 qubit - any real backend works for
    this tiny circuit, so "least busy" just minimises queue time, not a capability need."""
    candidates = [b for b in service.backends() if b.status().operational and b.num_qubits >= 1]
    if not candidates:
        raise RuntimeError("no operational backends available on this account right now")
    return service.least_busy(operational=True, min_num_qubits=1)


def run_on_hardware(qc, shots: int):
    """Submit the circuit to real IBM Quantum hardware via the Sampler primitive."""
    from qiskit import transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from src.qconfig import SEED

    service = QiskitRuntimeService()
    backend = pick_backend(service)
    # real hardware needs real transpilation (routing, basis gates), unlike Aer's level-0 passthrough
    compiled = transpile(qc, backend, optimization_level=1, seed_transpiler=SEED)

    sampler = SamplerV2(mode=backend)
    t0 = time.perf_counter()
    job = sampler.run([compiled], shots=shots)
    result = job.result()
    runtime = time.perf_counter() - t0

    counts = result[0].data.c.get_counts()
    return {"backend_name": backend.name, "counts": {str(k): int(v) for k, v in counts.items()},
           "job_id": job.job_id(), "runtime_seconds": round(runtime, 3),
           "depth": compiled.depth(), "gate_counts": {str(k): int(v) for k, v in compiled.count_ops().items()},
           "seed_transpiler": SEED}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shots", type=int, default=128, help="kept small: real hardware time is scarce")
    ap.add_argument("--dry-run", action="store_true", help="build and transpile only, submit nothing")
    ap.add_argument("--save", action="store_true", help="append evidence to data/quantum_runs.json")
    args = ap.parse_args()

    try:
        import qiskit_ibm_runtime                              # noqa: F401
    except ImportError:
        print("qiskit-ibm-runtime is not installed. Run `python -m src.q8_check_access` first; "
             "it explains how to install it and check your account access.")
        return 2

    qc = build_circuit()
    print("Circuit: single-qubit Hadamard + measure (matches Q7's scope).\n")

    if args.dry_run:
        print(qc.draw(output="text"))
        print("\n--dry-run: not submitting to hardware or Aer. Remove --dry-run to actually run.")
        return 0

    print(f"Running on the Aer simulator first (for comparison), {args.shots} shots ...")
    aer_counts = run_on_aer(qc, args.shots)
    print(f"  Aer simulator, toy size: {aer_counts}")

    diagram_dir = ROOT / "docs" / "circuits"
    diagram_dir.mkdir(parents=True, exist_ok=True)
    (diagram_dir / "q8_single_qubit_hadamard.txt").write_text(str(qc.draw(output="text")),
                                                              encoding="utf-8")

    print("\nSubmitting to real IBM Quantum hardware ...")
    try:
        from src import quantum_runs as QR
        hw = run_on_hardware(qc, args.shots)
    except Exception as exc:
        print(f"\nCould not run on real hardware: {exc}\n"
             "Run `python -m src.q8_check_access` to check account access and limits first.")
        return 1

    print(f"  Backend: {hw['backend_name']}")
    print(f"  Counts:  {hw['counts']}")
    print(f"  Job ID:  {hw['job_id']}")
    print(f"  Runtime: {hw['runtime_seconds']} s")

    shots_total = sum(hw["counts"].values())
    zeros = hw["counts"].get("0", 0)
    # "success" has no single-shot meaning for a Hadamard+measure circuit (both outcomes are
    # correct); the schema still requires a success_rate in [0, 1], so this reports how close
    # the split came to the ideal 50/50 (1.0 = perfectly balanced, 0.0 = all one outcome) -
    # a genuine randomness-quality number, not a placeholder.
    balance_score = 1.0 - abs(zeros / shots_total - 0.5) * 2 if shots_total else 0.0

    import qiskit
    try:
        import qiskit_ibm_runtime
        backend_version = f"qiskit-ibm-runtime {qiskit_ibm_runtime.__version__}"
    except Exception:
        backend_version = "unknown (qiskit-ibm-runtime version not detected)"

    record = {
        "run_id": f"q8-{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}",
        "timestamp_utc": QR.now_utc(), "algorithm": "q8_hadamard_hardware",
        "question_group": "q8_real_hardware",
        "inputs": {"description": "single-qubit Hadamard, matches Q7's scope"},
        "qubits": 1, "depth": hw["depth"], "gate_counts": hw["gate_counts"],
        "shots": args.shots, "backend": hw["backend_name"], "backend_version": backend_version,
        "qiskit_version": qiskit.__version__,
        "seed_simulator": -1,       # not applicable: real hardware is not Aer-seeded (see notes)
        "seed_transpiler": hw["seed_transpiler"],
        "job_id": hw["job_id"], "counts": hw["counts"],
        "success_rate": round(balance_score, 4),
        "runtime_seconds": hw["runtime_seconds"],
        "diagram_file": "docs/circuits/q8_single_qubit_hadamard.txt",
        "label": f"real quantum hardware: {hw['backend_name']}", "simulated": False,
        "result": {"aer_comparison_counts": aer_counts, "balance_score": round(balance_score, 4)},
        "notes": ("Q8: real IBM Quantum hardware run, compared with the Aer simulator on the "
                 "same circuit. Rule 11: this result is labelled by its REAL backend name, "
                 "not 'Aer simulator, toy size'. seed_simulator=-1 because real hardware has no "
                 "simulator seed; seed_transpiler was genuinely used for transpilation. "
                 "success_rate here measures outcome balance (1.0=perfect 50/50), not a "
                 "correct/incorrect answer, since both outcomes of H+measure are valid."),
    }
    if args.save:
        QR.append_run(record)
        print(f"\nsaved to {QR.RUNS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
