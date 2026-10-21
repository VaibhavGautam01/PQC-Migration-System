"""
advisor_page_data.py - data preparation for the dashboard 'PQC advisor' page (Week 2 Day 3).

Pure functions (no Streamlit). They read data/pqc_recommendations.json (written by the
PQC advisor work, one record per layer) and only rely on its JSON layout, so the page
works as soon as that file is in the repository.
ML-KEM, ML-DSA and AES-GCM are classical algorithms that resist quantum attacks.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECOMMENDATIONS_PATH = ROOT / "data" / "pqc_recommendations.json"

SHOWN = ("layer", "layer_name", "today", "technique", "parameter_set", "standard",
         "quantum_status", "sizes_bytes", "rationale", "trade_offs", "where_to_use")


def load_records(path=None):
    """Return the list of layer records in file order, or None if the file is missing or broken."""
    p = Path(path) if path else RECOMMENDATIONS_PATH
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
    records = data.get("records") if isinstance(data, dict) else None
    if not isinstance(records, list) or not records:
        return None
    if any(not isinstance(r, dict) or any(k not in r for k in SHOWN) for r in records):
        return None
    return records


def sizes_text(rec):
    """'public_key: 1,184 B, ciphertext: 1,088 B', or 'n/a' when the layer has no sizes."""
    sizes = rec.get("sizes_bytes") or {}
    return ", ".join(f"{k}: {v:,} B" for k, v in sizes.items()) or "n/a"


def total_bytes(rec):
    """Sum of the listed sizes in bytes (0 if none)."""
    return sum(v for v in (rec.get("sizes_bytes") or {}).values() if isinstance(v, (int, float)))


def status_color(rec):
    """Badge colour: green for quantum-resistant algorithms, blue for symmetric, grey otherwise."""
    s = rec.get("quantum_status", "").lower()
    if "quantum-resistant" in s:
        return "#00E676"
    if "symmetric" in s:
        return "#00B0FF"
    return "#90A4AE"


def overview_rows(records):
    """Table rows: layer, today, recommended technique, parameter set, standard, sizes."""
    return [{"Layer": f"{r['layer']} {r['layer_name']}", "Today": r["today"],
             "Recommended": r["technique"], "Parameter set": r["parameter_set"],
             "Standard": r["standard"], "Sizes": sizes_text(r)} for r in records]


def size_chart_rows(records):
    """Layers that add bytes to the hidden payload, for a bar chart."""
    return [{"layer": f"{r['layer']} {r['technique']}", "bytes": total_bytes(r)}
            for r in records if total_bytes(r) > 0]
