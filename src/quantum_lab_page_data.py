"""
quantum_lab_page_data.py - data preparation for the dashboard 'Quantum Lab' page
(Week 3 Day 2).

Pure functions (no Streamlit, no Qiskit), so they can be tested. They read the evidence
records in data/quantum_runs.json (rule 4) and run the evidence gate and the static guard.
Every number on the page comes from a saved run. Aer simulator, toy size.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# evidence_gate.py imports "from src import ...", so the repo root must be on the path when
# the dashboard runs as "streamlit run src/live_dashboard.py" (only src/ is there by default).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import evidence_gate as EG  # noqa: E402
from src import quantum_guard as QG  # noqa: E402
from src import quantum_runs as QR  # noqa: E402

DEFAULT_LABEL = "Aer simulator, toy size"

# Planned techniques (Must items) and the algorithm name their run records use.
PLANNED = [
    ("Q1", "Shor order finding by phase estimation", "shor_pe"),
    ("Q2", "Shor at gate level (Beauregard, 2n+3 qubits)", "shor_gate"),
    ("Q3", "Grover on a toy block cipher", "grover"),
]


def load_runs(path=None):
    """All evidence records (empty list if the file is missing)."""
    return QR.load_runs(path)


def label_of(run):
    """Rule 11: every result states where it ran."""
    return run.get("label") or DEFAULT_LABEL


def inputs_text(run):
    return ", ".join(f"{k} = {v}" for k, v in run.get("inputs", {}).items())


def evidence_rows(runs):
    """One row per run for the evidence table."""
    rows = []
    for r in runs:
        chi = r.get("chi_square") or {}
        rows.append({
            "run": r["run_id"], "algorithm": r["algorithm"], "inputs": inputs_text(r),
            "qubits": r["qubits"], "depth": r["depth"], "shots": r["shots"],
            "success rate": round(r["success_rate"], 3),
            "chi-square p": chi.get("p_value"),
            "backend": f"{r['backend']} {r['backend_version']}",
            "qiskit": r["qiskit_version"],
            "seed": f"{r['seed_simulator']} / {r['seed_transpiler']}",
            "label": label_of(r),
        })
    return rows


def run_labels(runs):
    """Short labels for a run picker, in file order."""
    return [f"{r['algorithm']} | {inputs_text(r)} | {r['question_group']}" for r in runs]


def histogram_rows(run, top=16):
    """Measured counts, biggest first. Bitstrings are exactly as the backend returned them."""
    items = sorted(run["counts"].items(), key=lambda kv: -kv[1])[:top]
    total = sum(run["counts"].values()) or 1
    return [{"bitstring": b, "count": c, "share": round(c / total, 4)} for b, c in items]


def diagram_text(run, root=ROOT, max_lines=40):
    """(shown text, total lines, path) of the saved circuit diagram, or (None, 0, path)."""
    path = Path(root) / run.get("diagram_file", "")
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return None, 0, str(run.get("diagram_file"))
    return "\n".join(lines[:max_lines]), len(lines), str(run.get("diagram_file"))


def progress_rows(runs):
    """Which planned Must techniques have evidence records yet."""
    rows = []
    for qid, name, algo in PLANNED:
        n = sum(1 for r in runs if r.get("algorithm") == algo)
        rows.append({"item": qid, "technique": name, "runs saved": n,
                     "status": "has evidence" if n else "no evidence yet"})
    return rows


def gate_summary(path=None, root=ROOT):
    """(n_runs, errors, warnings) from the evidence gate."""
    return EG.run_gate(path, root)


def guard_problems():
    """Static guard findings (empty list = clean)."""
    return QG.scan_all()


def question_rows(runs):
    """Change-the-question test (rule 6) per group."""
    groups = sorted({r.get("question_group") for r in runs if r.get("question_group")})
    rows = []
    for g in groups:
        members = [r for r in runs if r.get("question_group") == g]
        rows.append({"group": g, "runs": len(members),
                     "different inputs": len({inputs_text(r) for r in members}),
                     "passes": bool(QR.check_change_the_question(runs, g))})
    return rows


def verification_rows(runs, errors, warnings, problems):
    """Checks per rule, each with a plain pass or fail and what it means."""
    cross = [r for r in runs if r.get("cross_check")]
    cross_ok = [r for r in cross if r["cross_check"].get("agree")]
    chi = [r for r in runs if r.get("chi_square")]
    return [
        {"check": "Evidence gate (rule 4)", "result": "PASS" if not errors else "FAIL",
         "detail": f"{len(runs)} runs, {len(errors)} errors, {len(warnings)} warnings"},
        {"check": "Static guard (rule 8)", "result": "PASS" if not problems else "FAIL",
         "detail": "no classical shortcut found in the circuit builders" if not problems
                   else f"{len(problems)} finding(s)"},
        {"check": "Second simulation method (rule 9)",
         "result": "PASS" if runs and len(cross_ok) == len(runs) else "PARTIAL",
         "detail": f"{len(cross_ok)} of {len(runs)} runs cross-checked and agree"},
        {"check": "Chi-square against theory (rule 5)",
         "result": "PASS" if runs and len(chi) == len(runs) else "PARTIAL",
         "detail": f"{len(chi)} of {len(runs)} runs have a chi-square record"},
    ]
