"""Build CBOM v2 entries for the image and video projects.

Risk fields stay null until outputs/risk_scores.json has been wired in (attach_scores).
Fields follow docs/cbom_v2_fields.md.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import pqc_advisor  # noqa: E402

IMAGE_COMPONENTS = [
    # (layer, component as found today)
    ("L1", "RSA (textbook, no padding)"),
]

# Add "video" here once its pinned commit and components are confirmed (see the commands below).
PROJECTS = {
    "image": {"commit": "bb6d944", "components": IMAGE_COMPONENTS},
}


def attach_scores(entry, scores):
    """Fill risk fields from outputs/risk_scores.json once its structure is known."""
    return entry


def build(project="image", scores=None):
    spec = PROJECTS[project]
    recs = pqc_advisor.load_recommendations()
    entries = []
    for layer, component in spec["components"]:
        rec = recs[layer]
        entry = {
            "component": component,
            "project": project,
            "layer": layer,
            "file_line": None,
            "risk_percent": None,
            "band": None,
            "quantum_risk_percent": None,
            "classical_weakness_percent": None,
            "recommendation": rec["technique"],
            "parameter_set": rec["parameter_set"],
            "standard": rec["standard"],
            "post_migration_risk_percent": None,
            "scenario_range_z5_z10_z20": [None, None, None],
            "scanner_version": "v0.4.0",
            "pinned_commit": spec["commit"],
        }
        entries.append(attach_scores(entry, scores) if scores else entry)
    return {"cbom_version": "2.0-draft", "project": project, "entries": entries}


if __name__ == "__main__":
    out = ROOT / "outputs" / "cbom_v2_image.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(build(), indent=2), encoding="utf-8")
    print(f"wrote {out}")