"""Markdown sections for the risk report: risk percentages, advisor, before/after, reference cases.

No score is invented. Numbers come only from read_scores(), which reads outputs/risk_scores.json.
If that file is missing every number prints as "not yet scored".
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import build_cbom_v2  # noqa: E402
import pqc_advisor    # noqa: E402

NOT_SCORED = "not yet scored"

# Worked reference values from the risk model specification (plan section 4).
# Assumptions: X = 5, Y = 2, Z = 10 years; F4 = 5 for OAEP and AES-GCM; F6 = 100; F3 n/a for ML-KEM.
REFERENCE_CASES = [
    ("RSA-512 without padding", "84.1", "100.0", "90.4"),
    ("RSA-1024 without padding", "81.6", "80.0", "80.9"),
    ("RSA-2048 with OAEP", "79.1", "8.5", "50.8"),
    ("ML-KEM-768 + AES-256-GCM", "4.5", "5.0", "4.7"),
]


SCORES_PATH = ROOT / "outputs" / "risk_scores.json"
BEFORE_AFTER_PATH = ROOT / "outputs" / "before_after_image.json"


def _r(v):
    return None if v is None else round(v, 1)


def read_scores(scores_path=SCORES_PATH, before_after_path=BEFORE_AFTER_PATH):
    """Read outputs/risk_scores.json (and the image before/after file) into:

    {project: {"layers": {layer: {"quantum": q, "classical": c, "overall": o, "band": b,
                                  "after_overall": a}},
               "project_score": s}}

    A missing or broken file gives {} so every number prints as "not yet scored".
    after_overall is filled only where a before/after result exists (image L1, matched on key size).
    """
    try:
        data = json.loads(Path(scores_path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}
    try:
        ba = json.loads(Path(before_after_path).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        ba = {}
    out = {}
    for project, p in data.get("projects", {}).items():
        layers = {}
        raw = {k: v for k, v in p.items() if re.fullmatch(r"L\d+", k)}
        raw.update(p.get("other_layers") or {})
        for layer, info in raw.items():
            sc = info.get("score") if isinstance(info, dict) else None
            if not sc:
                continue
            layers[layer] = {"quantum": _r(sc.get("quantum")), "classical": _r(sc.get("classical")),
                             "overall": _r(sc.get("overall")), "band": sc.get("band"),
                             "after_overall": None}
        if ba.get("project") == project and "L1" in layers:
            bits = (raw["L1"].get("key_in_use") or {}).get("modulus_bits")
            for row in ba.get("rows", []):
                if row.get("modulus_bits") == bits:
                    layers["L1"]["after_overall"] = _r(row["after"]["overall"])
        out[project] = {"layers": layers, "project_score": _r(p.get("project_score"))}
    return out


def layer_numbers(scores, project, layer):
    return scores.get(project, {}).get("layers", {}).get(layer, {})


def fmt(v):
    return NOT_SCORED if v is None else str(v)


def section_risk_percentages(scores):
    lines = ["## Risk percentages by layer", "",
             "The percentage is a transparent weighted score from 0 to 100. It is not the probability of an attack.", ""]
    for project, spec in build_cbom_v2.PROJECTS.items():
        lines += [f"### {project.capitalize()} project (pinned commit {spec['commit']})", "",
                  "| Layer | Component | Quantum % | Classical % | Overall % | Band |", "|---|---|---|---|---|---|"]
        for layer, component in spec["components"]:
            n = layer_numbers(scores, project, layer)
            lines.append(f"| {layer} | {component} | {fmt(n.get('quantum'))} | {fmt(n.get('classical'))} | "
                         f"{fmt(n.get('overall'))} | {fmt(n.get('band'))} |")
        score = scores.get(project, {}).get("project_score")
        lines += ["", f"Project score (0.7 x worst layer + 0.3 x average): {fmt(score)}", ""]
    return "\n".join(lines)


def section_advisor():
    recs = pqc_advisor.load_recommendations()
    lines = ["## PQC advisor", "",
             "ML-KEM, ML-DSA and AES-GCM are classical algorithms that resist quantum attacks. "
             "The prototype libraries are educational, not production crypto.", "",
             "| Layer | Today | Recommended | Standard | Sizes (bytes) |", "|---|---|---|---|---|"]
    for r in recs.values():
        sizes = ", ".join(f"{k}: {v:,}" for k, v in r["sizes_bytes"].items()) or "n/a"
        lines.append(f"| {r['layer']} | {r['today']} | {r['technique']} | {r['standard']} | {sizes} |")
    return "\n".join(lines) + "\n"


def section_before_after(scores):
    lines = ["## Before and after migration", "",
             "Same scoring engine for both columns. Any remaining floor is explained in the validation chapter.", ""]
    for project, spec in build_cbom_v2.PROJECTS.items():
        lines += [f"### {project.capitalize()} project", "",
                  "| Layer | Overall % before | Overall % after | Recommendation |", "|---|---|---|---|"]
        recs = pqc_advisor.load_recommendations()
        for layer, _ in spec["components"]:
            n = layer_numbers(scores, project, layer)
            lines.append(f"| {layer} | {fmt(n.get('overall'))} | {fmt(n.get('after_overall'))} | {recs[layer]['technique']} |")
        lines.append("")
    return "\n".join(lines)


def section_reference_cases():
    lines = ["## Worked reference values (from the risk model specification)", "",
             "These cases are defined by the model, with X = 5, Y = 2, Z = 10 years. The engine must reproduce them. "
             "They are not measurements of our projects.", "",
             "| Case | Quantum % | Classical % | Overall % |", "|---|---|---|---|"]
    lines += [f"| {c} | {q} | {k} | {o} |" for c, q, k, o in REFERENCE_CASES]
    return "\n".join(lines) + "\n"


def build_markdown():
    scores = read_scores()
    return "\n".join(["# Risk report sections (generated)", "",
                      section_risk_percentages(scores), section_advisor(), section_before_after(scores),
                      section_reference_cases()])


if __name__ == "__main__":
    out = ROOT / "docs" / "risk_report_sections.md"
    out.write_text(build_markdown(), encoding="utf-8")
    print(f"wrote {out}")