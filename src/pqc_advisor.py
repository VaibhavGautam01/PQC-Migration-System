"""PQC advisor: loads and validates layer-by-layer recommendations."""
import json
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "pqc_recommendations.json"
REQUIRED = {"layer", "layer_name", "today", "technique", "parameter_set", "standard",
            "quantum_status", "sizes_bytes", "rationale", "trade_offs", "where_to_use"}


def load_recommendations(path=DEFAULT_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    records = data.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("recommendations file has no records")
    seen = set()
    for rec in records:
        missing = REQUIRED - rec.keys()
        if missing:
            raise ValueError(f"record {rec.get('layer')} missing fields: {sorted(missing)}")
        if rec["layer"] in seen:
            raise ValueError(f"duplicate layer {rec['layer']}")
        seen.add(rec["layer"])
        if not isinstance(rec["sizes_bytes"], dict):
            raise ValueError(f"{rec['layer']}: sizes_bytes must be an object")
    return {rec["layer"]: rec for rec in records}


def advise(layer, path=DEFAULT_PATH):
    recs = load_recommendations(path)
    if layer not in recs:
        raise KeyError(f"no recommendation for layer {layer}")
    return recs[layer]


def sizes_table_markdown(path=DEFAULT_PATH):
    lines = ["| Layer | Technique | Parameter set | Sizes (bytes) |", "|---|---|---|---|"]
    for rec in load_recommendations(path).values():
        sizes = ", ".join(f"{k}: {v:,}" for k, v in rec["sizes_bytes"].items()) or "n/a"
        lines.append(f"| {rec['layer']} | {rec['technique']} | {rec['parameter_set']} | {sizes} |")
    return "\n".join(lines)


if __name__ == "__main__":
    print(sizes_table_markdown())