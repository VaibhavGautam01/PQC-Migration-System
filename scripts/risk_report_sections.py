"""Markdown sections for the risk report: risk percentages, advisor, before/after, reference cases.

No score is invented. Numbers come only from read_scores(); until it is adapted to the real
structure of outputs/risk_scores.json it returns {} and every number prints as "not yet scored".
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import build_cbom_v2  # noqa: E402
import pqc_advisor    # noqa: E402

NOT_SCORED = "not yet scored"

# Only the image project exists in build_cbom_v2 today (commit is hard-coded there).
PROJECTS = {
    "image": {"commit": "bb6d944", "components": build_cbom_v2.IMAGE_COMPONENTS},
}

# Worked reference values from the risk model specification (plan section 4).
# Assumptions: X = 5, Y = 2, Z = 10 years; F4 = 5 for OAEP and AES-GCM; F6 = 100; F3 n/a for ML-KEM.
REFERENCE_CASES = [
    ("RSA-512 without padding", "84.1", "100.0", "90.4"),
    ("RSA-1024 without padding", "81.6", "80.0", "80.9"),
    ("RSA-2048 with OAEP", "79.1", "8.5", "50.8"),
    ("ML-KEM-768 + AES-256-GCM", "4.5", "5.0", "4.7"),
]


def read_scores():
    """ADAPT after you have seen outputs/risk_scores.json. Return:
    {project: {"layers": {layer: {"quantum": x, "classical": y, "overall": z,
                                  "band": b, "after_overall": a}},
               "project_score": s}}
    """
    return {}


def layer_numbers(scores, project, layer):
    return scores.get(project, {}).get("layers", {}).get(layer, {})


def fmt(v):
    return NOT_SCORED if v is None else str(v)


def section_risk_percentages(scores):
    lines = ["## Risk percentages by layer", "",
             "The percentage is a transparent weighted score from 0 to 100. It is not the probability of an attack.", ""]
    for project, spec in PROJECTS.items():
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
    for project, spec in PROJECTS.items():
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