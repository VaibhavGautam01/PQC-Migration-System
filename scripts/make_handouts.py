"""Short PDF handouts. Usage: python scripts/make_handouts.py advisor|before_after|quantum_lab|all [OUT_DIR]
Text stays within Latin-1 so the built-in PDF fonts render it. Numbers come from code and data files only.
"""
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import build_cbom_v2
import pqc_advisor
import risk_report_sections as rrs

BASE = getSampleStyleSheet()
CELL = ParagraphStyle("cell", parent=BASE["BodyText"], fontSize=8, leading=10)
BODY = ParagraphStyle("body", parent=BASE["BodyText"], fontSize=9.5, leading=12)


def _table(rows, widths=None):
    data = [[Paragraph(f"<b>{escape(str(c))}</b>" if r == 0 else escape(str(c)), CELL) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return t


def _build(path, title, blocks):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    story = [Paragraph(escape(title), BASE["Title"])]
    for b in blocks:
        if b[0] == "h":
            story.append(Paragraph(escape(b[1]), BASE["Heading3"]))
        elif b[0] == "p":
            story.append(Paragraph(escape(b[1]), BODY))
        elif b[0] == "t":
            story.append(_table(*b[1:]))
        story.append(Spacer(1, 6))
    SimpleDocTemplate(str(path), pagesize=A4, title=title, leftMargin=36, rightMargin=36,
                      topMargin=36, bottomMargin=36).build(story)
    print(f"wrote {path}")


def advisor(out_dir):
    recs = pqc_advisor.load_recommendations()
    rows = [["Layer", "Today", "Recommended", "Standard", "Sizes (bytes)"]]
    for r in recs.values():
        sizes = ", ".join(f"{k}: {v:,}" for k, v in r["sizes_bytes"].items()) or "n/a"
        rows.append([f"{r['layer']} {r['layer_name']}", r["today"], r["technique"], r["standard"], sizes])
    blocks = [("p", "ML-KEM, ML-DSA, SLH-DSA and AES-GCM are classical algorithms built to resist quantum attacks. "
                    "They run on ordinary computers."),
              ("t", rows, [95, 95, 140, 70, 123]), ("h", "Where to use it")]
    blocks += [("p", f"{r['layer']} {r['layer_name']}: {r['where_to_use']}") for r in recs.values()]
    blocks += [("h", "Limits"),
               ("p", "The prototype libraries (kyber-py, dilithium-py) are educational and not hardened against timing "
                     "attacks. Production route: liboqs-python.")]
    if recs["L1"].get("qkd_note"):
        blocks += [("h", "QKD note"), ("p", recs["L1"]["qkd_note"])]
    _build(Path(out_dir) / "pqc_advisor_handout.pdf", "PQC advisor: where ML-KEM, ML-DSA and AES-256 go", blocks)


def before_after(out_dir):
    scores = rrs.read_scores()
    recs = pqc_advisor.load_recommendations()
    blocks = [("p", "The percentage is a transparent weighted score from 0 to 100. It is not the probability of an attack. "
                    "Its assumptions are written down and shown as scenarios.")]
    for project, spec in build_cbom_v2.PROJECTS.items():
        rows = [["Layer", "Overall % before", "Overall % after", "Recommendation"]]
        for layer, _ in spec["components"]:
            n = rrs.layer_numbers(scores, project, layer)
            rows.append([layer, rrs.fmt(n.get("overall")), rrs.fmt(n.get("after_overall")), recs[layer]["technique"]])
        blocks += [("h", f"{project.capitalize()} project (pinned commit {spec['commit']})"), ("t", rows, [50, 100, 100, 273])]
    rows = [["Case", "Quantum %", "Classical %", "Overall %"]] + [list(c) for c in rrs.REFERENCE_CASES]
    blocks += [("h", "Worked reference values (model definition, not project measurements)"),
               ("t", rows, [220, 100, 100, 103])]
    _build(Path(out_dir) / "before_after_handout.pdf", "Risk score: before and after migration", blocks)


def load_evidence():
    runs = []
    for name in ("quantum_runs.json", "quantum_runs_q6.json", "quantum_runs_q7.json"):
        p = ROOT / "data" / name
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8-sig"))
        if isinstance(data, dict):
            data = data.get("runs", [])
        runs += [r for r in data if isinstance(r, dict) and "algorithm" in r]
    return runs


def quantum_lab(out_dir):
    rows = [["Algorithm", "Qubits", "Depth", "Where it ran", "Outcome"]]
    for r in load_evidence():
        where = r.get("label") or r.get("backend") or "backend not recorded"
        outcome = r.get("outcome") or r.get("success_rate") or "-"
        rows.append([r.get("algorithm"), r.get("qubits", "-"), r.get("depth", "-"), where, outcome])
    blocks = [("p", "Every row comes from a saved evidence record (algorithm, qubits, depth, backend, seeds). "
                    "All quantum results are simulator, toy size, unless a real backend is named."),
              ("t", rows, [110, 45, 45, 213, 110]),
              ("h", "Honest limits"),
              ("p", "Shor and Grover circuits here are toy size. Resource figures for real sizes are published estimates, "
                    "not measurements. BB84 is a simulated protocol; real QKD needs optical hardware. "
                    "No quantum advantage is claimed.")]
    _build(Path(out_dir) / "quantum_lab_handout.pdf", "Quantum Lab: what was run and where", blocks)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = sys.argv[2] if len(sys.argv) > 2 else str(ROOT / "outputs" / "handouts")
    jobs = {"advisor": advisor, "before_after": before_after, "quantum_lab": quantum_lab}
    for name in (jobs if what == "all" else [what]):
        jobs[name](out)