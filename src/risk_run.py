"""
risk_run.py - wire the risk model to findings, layers and assumptions (Week 1 Day 4).

For each project it scores layer L1 (message encryption: textbook RSA) with
risk_score.score_layer(), using the key size IN USE, the construction and the
exposure, and the agreed assumptions (X, Y, Z) from data/manual_facts.json.
Z is shown as a range over its scenarios, not as one number.
Layers beyond L1 are scored where the code has them (video L2 frame-selection key, video L3
CRC32). Layers with no protection at all are listed and left out of the average.
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


# Other layers with something to score (evidence: layer map, docs/layer_map.md).
OTHER_LAYERS = {
    "image": {},
    "video": {
        "L2": {"name": "Frame-selection key", "today": "SHA-256 of a passphrase (frames 0 to 255 only)",
               "category": "symmetric", "effective_bits": 128,
               "construction": "deterministic_or_oracle", "exposure": "bypassable",
               "evidence": "frame_selector.py:32"},
        "L3": {"name": "Integrity", "today": "CRC32 (not cryptographic)",
               "category": "none", "construction": "deterministic_or_oracle", "exposure": "bypassable",
               "evidence": "rsa_crypto.py:137 and :180"},
    },
}
# Layers that do not exist in the project: no protection at all, left out of the average.
NO_PROTECTION = {"image": ["L2", "L3", "L5"], "video": ["L5"]}
PENDING_REASON = "F1 category 'none' is not in data/risk_weights.json yet (comes with weights v1.0)"


def _score(cfg, modulus_bits, x, y, z, weights):
    return R.score_layer("shor_broken", cfg["construction"], cfg["exposure"],
                         modulus_bits=modulus_bits, x_years=x, y_years=y, z_years=z,
                         weights=weights)


def _round(d):
    return {k: (round(v, 1) if isinstance(v, float) else v) for k, v in d.items()}


def _score_other(cfg, x, y, z_list, central_z, weights):
    """Score a non-RSA layer. Returns None if the engine cannot score its category yet."""
    kw = {"effective_bits": cfg["effective_bits"]} if "effective_bits" in cfg else {}

    def one(zz):
        return _round(R.score_layer(cfg["category"], cfg["construction"], cfg["exposure"],
                                    x_years=x, y_years=y, z_years=zz, weights=weights, **kw))
    try:
        score = one(central_z)
        scenarios = {str(zz): one(zz) for zz in z_list}
    except KeyError:
        return None
    return {"name": cfg["name"], "today": cfg["today"], "evidence": cfg["evidence"],
            "category": cfg["category"], "construction": cfg["construction"],
            "exposure": cfg["exposure"], "score": score, "z_scenarios": scenarios}


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

    z_list = A.z_scenarios(assume)
    others, pending = {}, []
    for lid, ocfg in OTHER_LAYERS[project].items():
        entry = _score_other(ocfg, x, y, z_list, z, weights)
        if entry is None:
            pending.append(lid)
        else:
            others[lid] = entry

    layer_scores = [layer["overall"]] + [e["score"]["overall"] for e in others.values()]
    proj = R.project_score(layer_scores, weights)
    proj_by_z = {}
    for zz in z_list:
        vals = [scenarios[str(zz)]["overall"]] + [e["z_scenarios"][str(zz)]["overall"] for e in others.values()]
        proj_by_z[zz] = R.project_score(vals, weights)
    evidence = None
    if findings is not None:
        m = L.build_layer_map(findings)
        evidence = {"L1_findings": len(m[project].get("L1", []))}

    return {
        "project": project, "repo": cfg["repo"],
        "layers_scored": ["L1"] + list(others),
        "layers_not_scored_yet": pending,
        "pending_reason": PENDING_REASON if pending else None,
        "no_protection": NO_PROTECTION[project],
        "other_layers": others,
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
    ap.add_argument("--out", default=None,
                    help="output file (default outputs/risk_scores.json)")
    args = ap.parse_args(argv)
    projects = ("image", "video") if args.project == "both" else (args.project,)
    out = run(projects, out_path=args.out)
    for p, r in out["projects"].items():
        s = r["L1"]["score"]
        print(f"{p}: {r['project_score']}% ({r['band']}), "
              f"L1 quantum {s['quantum']}%, L1 classical {s['classical']}%, "
              f"Z range {r['z_range']['min']}-{r['z_range']['max']}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
