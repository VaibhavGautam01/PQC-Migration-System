"""
risk_run.py - wire the risk model to findings, layers and assumptions (Week 1 Day 4).

For each project it scores layer L1 (message encryption: textbook RSA) with
risk_score.score_layer(), using the key size IN USE, the construction and the
exposure, and the agreed assumptions (X, Y, Z) from data/manual_facts.json.
Z is shown as a range over its scenarios, not as one number.
Layers L2, L3 and L5 are scored in Week 3 (plan: Week 3 Day 1).
The result is written to outputs/risk_scores.json.

The score is a transparent weighted score, NOT a probability.
"""
import argparse
import json
from pathlib import Path

from src import assumptions as A
from src import layers as L
from src import risk_score as R

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "outputs" / "risk_scores.json"

# L1 evidence from manual_facts.json (size_overrides, padding) and the code.
# primary = the size in use that sets the layer score; the others are shown as variants.
L1_CONFIG = {
    "image": {
        "repo": "Final-Year-project-part1",
        "construction": "no_padding_deterministic",   # textbook RSA, confirmed by hand
        "exposure": "keyless",                        # LSB embedding, no key needed to extract
        "keys": [
            {"label": "main path, generate_keypair(bits=128)", "modulus_bits": 256, "primary": True},
            {"label": "R-channel module, generate_small_keypair()", "modulus_bits": 8, "primary": False},
        ],
    },
    "video": {
        "repo": "Secure-Video-Steganography",
        "construction": "no_padding_deterministic",
        "exposure": "bypassable",                     # keyed, but the header scan finds the frames
        "keys": [
            {"label": "UI default", "modulus_bits": 2048, "primary": True},
            {"label": "UI option / function default", "modulus_bits": 1024, "primary": False},
        ],
    },
}


def _score(cfg, modulus_bits, x, y, z, weights):
    return R.score_layer("shor_broken", cfg["construction"], cfg["exposure"],
                         modulus_bits=modulus_bits, x_years=x, y_years=y, z_years=z,
                         weights=weights)


def _round(d):
    return {k: (round(v, 1) if isinstance(v, float) else v) for k, v in d.items()}


def score_project(project, assume=None, weights=None, findings=None):
    """Score one project ('image' or 'video'); return a JSON-ready dict."""
    if project not in L1_CONFIG:
        raise ValueError(f"unknown project {project!r}")
    weights = weights or R.load_weights()
    assume = assume or A.load_assumptions(project)
    cfg = L1_CONFIG[project]
    x = assume["secret_years"]["value"]
    y = assume["migration_years"]["value"]
    z = assume["quantum_years"]["value"]
    primary = next(k for k in cfg["keys"] if k["primary"])

    layer = _round(_score(cfg, primary["modulus_bits"], x, y, z, weights))
    scenarios = {str(zz): _round(_score(cfg, primary["modulus_bits"], x, y, zz, weights))
                 for zz in A.z_scenarios(assume)}
    variants = [{"label": k["label"], "modulus_bits": k["modulus_bits"],
                 **_round(_score(cfg, k["modulus_bits"], x, y, z, weights))}
                for k in cfg["keys"] if not k["primary"]]

    layer_scores = [layer["overall"]]
    proj = R.project_score(layer_scores, weights)
    proj_by_z = {zz: R.project_score([s["overall"]], weights) for zz, s in scenarios.items()}
    evidence = None
    if findings is not None:
        m = L.build_layer_map(findings)
        evidence = {"L1_findings": len(m[project].get("L1", []))}

    return {
        "project": project, "repo": cfg["repo"],
        "layers_scored": ["L1"],
        "layers_not_scored_yet": ["L2", "L3", "L5"],
        "L1": {"key_in_use": primary, "construction": cfg["construction"],
               "exposure": cfg["exposure"], "score": layer,
               "z_scenarios": scenarios, "variants": variants},
        "project_score": round(proj, 1),
        "band": R.band(proj, weights),
        "z_range": {"min": round(min(proj_by_z.values()), 1), "max": round(max(proj_by_z.values()), 1)},
        "evidence": evidence,
    }


def run(projects=("image", "video"), out_path=None, findings_path=None):
    weights = R.load_weights()
    try:
        findings = L.load_findings(findings_path)
    except FileNotFoundError:
        findings = None
    out = {
        "note": "Transparent weighted score, not a probability. Simulator-based quantum inputs, toy size.",
        "weights_version": weights["version"],
        "assumptions": {
            "X_secret_years": A.load_assumptions()["secret_years"]["value"],
            "Y_migration_years": A.load_assumptions()["migration_years"]["value"],
            "Z_scenarios": A.z_scenarios(A.load_assumptions()),
            "agreed_with_sir": A.load_assumptions()["agreed_with_sir"],
            "agreed_date": A.load_assumptions()["agreed_date"],
        },
        "projects": {p: score_project(p, weights=weights, findings=findings) for p in projects},
    }
    path = Path(out_path) if out_path else OUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Score the image and/or video project.")
    ap.add_argument("--project", choices=["image", "video", "both"], default="both")
    args = ap.parse_args(argv)
    projects = ("image", "video") if args.project == "both" else (args.project,)
    out = run(projects)
    for p, r in out["projects"].items():
        s = r["L1"]["score"]
        print(f"{p}: {r['project_score']}% ({r['band']}), "
              f"quantum {s['quantum']}%, classical {s['classical']}%, "
              f"Z range {r['z_range']['min']}-{r['z_range']['max']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
