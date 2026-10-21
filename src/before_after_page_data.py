"""
before_after_page_data.py - data preparation for the dashboard 'Before and after' page
(Week 3 Day 2).

Pure functions (no Streamlit), so they can be tested. They read
outputs/before_after_image.json, written by src/before_after.py. Both rows were scored
by the SAME engine (risk_score.score_layer). A weighted score, NOT a probability.
Formulas and weights only; no simulator result.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "outputs" / "before_after_image.json"

FACTORS = [
    ("f1", "F1 Quantum exposure"),
    ("f2", "F2 Qubit cost"),
    ("f3", "F3 Classical key weakness"),
    ("f4", "F4 Construction weakness"),
    ("f5_eff", "F5 Data lifetime (gated by F1)"),
    ("f6_eff", "F6 Exposure (gated)"),
]


def load(path=None):
    """Return the parsed file, or None if it is missing or broken."""
    p = Path(path) if path else PATH
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def size_options(data):
    """RSA modulus sizes available in the file, in file order."""
    return [r["modulus_bits"] for r in data.get("rows", [])]


def row_for(data, bits):
    """The row for one modulus size, or None."""
    for r in data.get("rows", []):
        if r["modulus_bits"] == bits:
            return r
    return None


def summary(row):
    """Headline numbers for one size."""
    return {"before": row["project_before"], "after": row["project_after"],
            "drop": row["drop"], "before_band": row["before"]["band"],
            "after_band": row["after"]["band"]}


def factor_rows(row):
    """One row per factor: before, after (None = factor does not apply to that setup)."""
    return [{"factor": label, "before": row["before"].get(key), "after": row["after"].get(key)}
            for key, label in FACTORS]


def parts_rows(row):
    """Quantum, classical and overall percentages, before and after."""
    return [{"part": part.title(), "before": row["before"][part], "after": row["after"][part]}
            for part in ("quantum", "classical", "overall")]


def scenario_rows(row):
    """One row per Z scenario (years until a large quantum computer)."""
    return sorted(({"z": int(z), "before": s["before"], "after": s["after"]}
                   for z, s in row["z_scenarios"].items()), key=lambda r: r["z"])


def sensitivity_rows(row):
    """Weight-draw results: how often 'after' stayed below 'before' and the ranges."""
    names = {"narrow_random": "Narrow random weights", "wide_random": "Wide random weights"}
    out = []
    for key, label in names.items():
        s = row.get("sensitivity", {}).get(key)
        if s:
            out.append({"draws": label, "after_below_before": s["after_below_before_fraction"],
                        "before_range": f"{s['before_min']:.1f} to {s['before_max']:.1f}",
                        "after_range": f"{s['after_min']:.1f} to {s['after_max']:.1f}",
                        "smallest_drop": round(s["smallest_drop"], 1)})
    return out


def floor_rows(data):
    """Why the 'after' score is not zero: the factors that stay above 0."""
    return [{"factor": f["factor"], "value": f["value"]} for f in data.get("after_floor", [])]
