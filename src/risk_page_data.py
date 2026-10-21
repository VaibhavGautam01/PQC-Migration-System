"""
risk_page_data.py - data preparation for the dashboard 'Risk score' page (Week 2 Day 2).

Pure functions (no Streamlit), so they can be tested. They read outputs/risk_scores.json,
written by src/risk_run.py. The score is a transparent weighted score, NOT a probability.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCORES_PATH = ROOT / "outputs" / "risk_scores.json"

BAND_COLORS = {"Low": "#00E676", "Moderate": "#FFB300", "High": "#FF9100", "Critical": "#FF1744"}

FACTORS = [
    ("f1", "F1 Quantum exposure", "Shor-broken public key = 100"),
    ("f2", "F2 Qubit cost", "from 2n+3 logical qubits; smaller key = cheaper attack"),
    ("f3", "F3 Classical key weakness", "key size against ordinary computers"),
    ("f4", "F4 Construction weakness", "no padding, deterministic encryption = 100"),
    ("f5_eff", "F5 Data lifetime (gated by F1)", "Mosca test with X, Y, Z"),
    ("f6_eff", "F6 Exposure (gated by F3/F4)", "can the ciphertext be extracted without a secret?"),
]


def load_scores(path=None):
    """Return the parsed scores file, or None if it is missing or broken."""
    p = Path(path) if path else SCORES_PATH
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def summary_rows(scores):
    """One row per project: score, band, quantum %, classical %, Z range."""
    rows = []
    for name, p in scores.get("projects", {}).items():
        s = p["L1"]["score"]
        rows.append({"project": name, "score": p["project_score"], "band": p["band"],
                     "quantum": s["quantum"], "classical": s["classical"],
                     "z_min": p["z_range"]["min"], "z_max": p["z_range"]["max"]})
    return rows


def scenario_rows(scores):
    """One row per project and Z scenario (Z = years until a large quantum computer)."""
    rows = []
    for name, p in scores.get("projects", {}).items():
        for z, s in p["L1"]["z_scenarios"].items():
            rows.append({"project": name, "z": int(z), "overall": s["overall"], "band": s["band"]})
    return sorted(rows, key=lambda r: (r["project"], r["z"]))


def factor_rows(project_entry):
    """Factor breakdown of the scored layer: (label, value or None, meaning)."""
    s = project_entry["L1"]["score"]
    return [(label, s.get(key), meaning) for key, label, meaning in FACTORS]


def variant_rows(project_entry):
    """Other key sizes seen in the code, scored with the same engine (not the layer score)."""
    return [{"key": v["label"], "modulus_bits": v["modulus_bits"], "overall": v["overall"],
             "band": v["band"]} for v in project_entry["L1"].get("variants", [])]


def assumptions_note(scores):
    """(text, agreed) for the banner above the scores."""
    a = scores.get("assumptions", {})
    z = ", ".join(str(v) for v in sorted(a.get("Z_scenarios", [])))
    base = (f"X = {a.get('X_secret_years')} years the message must stay secret, "
            f"Y = {a.get('Y_migration_years')} years to migrate, Z = {z} years until a large "
            f"quantum computer (shown as scenarios).")
    if a.get("agreed_with_sir"):
        return f"Assumptions agreed with sir on {a.get('agreed_date')}. {base}", True
    return f"Assumptions NOT yet agreed with sir, so read the Z range, not one number. {base}", False


def layer_rows(project_entry):
    """Every scored layer of a project, one row each (L1 first)."""
    k = project_entry["L1"]["key_in_use"]
    s = project_entry["L1"]["score"]
    rows = [{"Layer": "L1 Message encryption",
             "Today": f"RSA {k['modulus_bits']}-bit, {project_entry['L1']['construction']}",
             "Overall %": s["overall"], "Band": s["band"], "Where": "see layer map"}]
    for lid, e in project_entry.get("other_layers", {}).items():
        rows.append({"Layer": f"{lid} {e['name']}", "Today": e["today"], "Overall %": e["score"]["overall"],
                     "Band": e["score"]["band"], "Where": e["evidence"]})
    return rows


def no_protection_text(project_entry):
    """Sentence listing layers that do not exist (empty string if none)."""
    ids = project_entry.get("no_protection", [])
    if not ids:
        return ""
    return ("No protection at all in this project: " + ", ".join(ids) +
            ". They are left out of the average and not counted as safe.")
