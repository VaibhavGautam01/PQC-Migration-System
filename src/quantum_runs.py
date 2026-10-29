"""
quantum_runs.py - evidence records for every quantum run (rule 4, Day 2).

data/quantum_runs.json is a JSON object: {"schema_version": 1, "runs": [ ... ]}.
Every run appends one record. Stdlib only, so it runs on any venv.
The evidence gate (QL) calls validate_run() and check_change_the_question().
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS_PATH = ROOT / "data" / "quantum_runs.json"
SCHEMA_VERSION = 1

# field -> type(s). Rule 4 fields first, then rules 5, 6, 7, 9, 10, 11 fields.
REQUIRED = {
    "run_id": str,
    "timestamp_utc": str,
    "algorithm": str,            # e.g. "shor_pe", "shor_gate", "grover", "bb84"
    "question_group": str,       # runs that differ only in the question (rule 6)
    "inputs": dict,              # e.g. {"N": 15, "a": 7} or {"marked_key": 93}
    "qubits": int,
    "depth": int,
    "gate_counts": dict,         # e.g. {"cx": 120, "h": 8}
    "shots": int,
    "backend": str,              # "AerSimulator" or a real backend name
    "backend_version": str,      # qiskit-aer version or backend version
    "qiskit_version": str,
    "seed_simulator": int,
    "seed_transpiler": int,
    "counts": dict,              # measured counts, as returned by the backend
    "success_rate": (int, float),
    "runtime_seconds": (int, float),
    "diagram_file": str,         # path to the saved circuit diagram
    "label": str,                # rule 11: "Aer simulator, toy size" or backend name
    "simulated": bool,
    "result": dict,              # what the run found, e.g. {"period": 4, "factors": [3, 5]}
}
OPTIONAL = {
    "chi_square": dict,          # rule 5: {"statistic":..,"p_value":..,"dof":..}
    "cross_check": dict,         # rule 9: {"method":"statevector vs MPS","agree":true}
    "notes": str,
}


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_run(run):
    """Return a list of problems (empty list = record is valid)."""
    problems = []
    for key, typ in REQUIRED.items():
        if key not in run:
            problems.append(f"missing field: {key}")
        elif isinstance(run[key], bool) and typ is not bool:
            problems.append(f"{key}: bool is not {typ}")
        elif not isinstance(run[key], typ):
            problems.append(f"{key}: wrong type {type(run[key]).__name__}")
    for key, typ in OPTIONAL.items():
        if key in run and not isinstance(run[key], typ):
            problems.append(f"{key}: wrong type {type(run[key]).__name__}")
    if problems:
        return problems
    if run["shots"] <= 0 or run["qubits"] <= 0:
        problems.append("shots and qubits must be positive")
    if sum(run["counts"].values()) != run["shots"]:
        problems.append("counts do not add up to shots")
    if not 0 <= run["success_rate"] <= 1:
        problems.append("success_rate must be between 0 and 1")
    if run["simulated"] and "simulator" not in run["label"].lower():
        problems.append("simulated run must say 'simulator' in its label (rule 11)")
    return problems


def check_change_the_question(runs, group):
    """Rule 6: a group needs >= 2 runs with different inputs AND different results."""
    g = [r for r in runs if r.get("question_group") == group]
    if len(g) < 2:
        return False
    inputs = {json.dumps(r["inputs"], sort_keys=True) for r in g}
    results = {json.dumps(r["result"], sort_keys=True) for r in g}
    return len(inputs) >= 2 and len(results) >= 2


def load_runs(path=None):
    path = Path(path) if path else RUNS_PATH
    if not path.exists():
        return []
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)["runs"]


def extra_run_paths(data_dir=None):
    """data/quantum_runs_*.json (for example the Q6 and Q7 files), sorted. quantum_runs.json is not included."""
    data_dir = Path(data_dir) if data_dir else RUNS_PATH.parent
    return sorted(data_dir.glob("quantum_runs_*.json"))


def load_extra_runs(data_dir=None):
    """Records from the extra run files as (runs, problems).

    A file may hold {"runs": [...]} (the evidence format) or a bare list. A file that cannot be read
    gives a problem string, never a crash. Each returned run carries "_source" (the file name) so the
    gate can say where a bad record came from; remove it with run.pop("_source") before saving.
    """
    runs, problems = [], []
    for path in extra_run_paths(data_dir):
        try:
            with open(path, encoding="utf-8-sig") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            problems.append(f"{path.name}: cannot read file ({exc.__class__.__name__})")
            continue
        items = data.get("runs") if isinstance(data, dict) else data
        if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
            problems.append(f"{path.name}: expected {{\"runs\": [...]}} or a list of records")
            continue
        runs += [dict(x, _source=path.name) for x in items]
    return runs, problems


def load_all_valid_runs(data_dir=None):
    """quantum_runs.json plus every record from the extra files that is already in the evidence format."""
    main = load_runs(Path(data_dir) / "quantum_runs.json" if data_dir else None)
    extra, _ = load_extra_runs(data_dir)
    return main + [{k: v for k, v in r.items() if k != "_source"} for r in extra if not validate_run(r)]


def append_run(run, path=None):
    """Validate, then append. Raises ValueError listing every problem."""
    problems = validate_run(run)
    if problems:
        raise ValueError("; ".join(problems))
    path = Path(path) if path else RUNS_PATH
    runs = load_runs(path)
    if any(r["run_id"] == run["run_id"] for r in runs):
        raise ValueError(f"duplicate run_id: {run['run_id']}")
    runs.append(run)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"schema_version": SCHEMA_VERSION, "runs": runs}, fh, indent=2)
        fh.write("\n")
