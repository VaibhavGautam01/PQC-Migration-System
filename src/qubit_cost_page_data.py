"""
qubit_cost_page_data.py - data for the qubit-cost (F2) table on the dashboard 'Risk score' page.

Pure functions (no Streamlit), so they can be tested. Three kinds of number are kept apart and
labelled, never mixed:

  * FORMULA   F2 uses q = 2n + 3 logical qubits (risk_score.f2_qubit_cost). This is what the score uses.
  * MEASURED  Q4: transpiler metrics of the gate-level Q2 Shor circuits for n = 4 to 8
              (outputs/q4_metrics.json). Aer simulator / transpiler, toy size.
  * ESTIMATE  published figures (Gidney and Ekera 2021) and, when it exists, the Q4 fit extrapolated
              to real key sizes (outputs/q4_fit.json). Estimates are never shown as measurements.

The extrapolation file is optional. Its format is a proposal to agree with Yatharth (Q4 fit owner):
  {"label": "...", "rows": [{"bits": 1024, "depth": 123, "two_qubit_gates": 456}, ...]}
Without the file, extrapolation_rows() returns [] and the page says it is not available yet.
"""
import json
from pathlib import Path

try:                                   # package import (tests) or plain import (streamlit run)
    from src import physical_estimates as pe
    from src import risk_score as rs
except ImportError:
    import physical_estimates as pe
    import risk_score as rs

ROOT = Path(__file__).resolve().parent.parent
Q4_PATH = ROOT / "outputs" / "q4_metrics.json"
FIT_PATH = ROOT / "outputs" / "q4_fit.json"
SIZES = (512, 1024, 2048, 3072)
LABEL_MEASURED = "Aer simulator / transpiler, toy size (measured)"
LABEL_ESTIMATE = "ESTIMATE, not measured"


def _load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def size_rows(sizes=SIZES, weights=None):
    """F2 formula next to the published figures, one row per RSA size. All published values are estimates."""
    rows = []
    for n in sizes:
        pub = pe.published_estimate(n)
        rows.append({
            "RSA bits": n,
            "F2 logical qubits (2n+3)": 2 * n + 3,
            "F2 score (0 to 100)": round(rs.f2_qubit_cost(n, weights), 1),
            "Gidney-Ekera abstract circuit, logical (estimate)": round(pe.gidney_ekera_logical(n)),
            "Published physical qubits (estimate)": f"{pub['physical_qubits']:,}" if pub else "no figure published here",
        })
    return rows


def measured_rows(path=None):
    """Q4 measured rows (toy sizes). [] if outputs/q4_metrics.json is missing."""
    data = _load(path or Q4_PATH)
    if not data:
        return []
    rows = []
    for r in data.get("rows", []):
        full = r.get("full")
        sim = r.get("simulated_iteration")
        rows.append({
            "n (bits)": r["n"], "N": r["N"],
            "qubits measured": r["iteration"]["qubits"],
            "qubits 2n+3": r["qubits_2n_plus_3"],
            "one iteration: depth": r["iteration"]["depth"],
            "one iteration: two-qubit gates": r["iteration"]["two_qubit_gates"],
            "full circuit: two-qubit gates": f"{full['two_qubit_gates']:,}" if full else "not transpiled",
            "2n x iteration (estimate)": r["estimate_full_two_qubit_gates"],
            "iteration checked by simulation": "-" if sim is None else ("yes" if sim["correct"] else "NO"),
        })
    return rows


def qubits_match_formula(path=None):
    """True when every measured circuit uses exactly 2n+3 qubits, False if one differs, None if no data."""
    rows = measured_rows(path)
    if not rows:
        return None
    return all(r["qubits measured"] == r["qubits 2n+3"] for r in rows)


def extrapolation_rows(path=None):
    """Extrapolated circuit size from the Q4 fit, every row an ESTIMATE. [] until outputs/q4_fit.json exists."""
    data = _load(path or FIT_PATH)
    if not data:
        return []
    return [{"RSA bits": r["bits"], "depth (estimate)": r.get("depth"),
             "two-qubit gates (estimate)": r.get("two_qubit_gates"), "kind": LABEL_ESTIMATE}
            for r in data.get("rows", [])]


def summary_text(path=None):
    """One honest sentence for the page about how measured qubits compare with the formula."""
    m = qubits_match_formula(path)
    if m is None:
        return "No Q4 metrics yet. Run: python src/metrics_run.py"
    if m:
        return ("The gate-level Shor circuits use exactly 2n+3 qubits for n = 4 to 8, which is the count the "
                "F2 formula uses. Depth and gate counts grow with n; measured values exist only for toy sizes.")
    return "At least one measured circuit does not use 2n+3 qubits: check outputs/q4_metrics.json before quoting F2."
