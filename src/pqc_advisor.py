"""PQC advisor: loads data/pqc_recommendations.json and answers per layer."""
import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "pqc_recommendations.json"
REQUIRED = ("layer", "name", "today", "technique", "parameter_set", "standard",
            "sizes_bytes", "quantum_role", "rationale", "tradeoffs", "where_to_use")


@dataclass(frozen=True)
class Recommendation:
    layer: str
    name: str
    today: str
    technique: str
    parameter_set: str
    standard: str
    sizes_bytes: dict
    quantum_role: str
    rationale: str
    tradeoffs: str
    where_to_use: str


def load_recommendations(path=DEFAULT_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    recs, seen = {}, set()
    for i, rec in enumerate(data["recommendations"]):
        missing = [k for k in REQUIRED if k not in rec]
        if missing:
            raise ValueError(f"record {i} missing fields: {missing}")
        if rec["layer"] in seen:
            raise ValueError(f"duplicate layer {rec['layer']}")
        seen.add(rec["layer"])
        recs[rec["layer"]] = Recommendation(**{k: rec[k] for k in REQUIRED})
    return recs


def recommend(layer, path=DEFAULT_PATH):
    recs = load_recommendations(path)
    if layer not in recs:
        raise KeyError(f"no recommendation for layer {layer}")
    return recs[layer]
