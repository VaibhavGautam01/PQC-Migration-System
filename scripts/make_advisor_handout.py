"""One-page advisor handout from data/pqc_recommendations.json.

Usage: python scripts\make_advisor_handout.py
Writes outputs\handouts\advisor_handout.pdf
"""
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

data = json.loads(Path("data/pqc_recommendations.json").read_text(encoding="utf-8-sig"))
if isinstance(data, dict):
    recs = data.get("recommendations") or data.get("records") or list(data.values())
else:
    recs = data

styles = getSampleStyleSheet()
cell = styles["BodyText"]
cell.fontSize = 8
cell.leading = 10


def p(text):
    return Paragraph(escape(str(text)), cell)


def sizes(d):
    return "; ".join(f"{k.replace('_', ' ')}: {v:,} B" for k, v in (d or {}).items()) or "n/a"


rows = [[p("Layer"), p("Today"), p("Recommended"), p("Standard"), p("Sizes")]]
for r in recs:
    rows.append([p(f"{r.get('layer', '')} {r.get('name', '')}"), p(r.get("today", "")),
                 p(r.get("technique", "")), p(r.get("standard", "")), p(sizes(r.get("sizes_bytes")))])

table = Table(rows, colWidths=[110, 150, 210, 90, 170], repeatRows=1)
table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                           ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                           ("VALIGN", (0, 0), (-1, -1), "TOP")]))

notes = [
    "ML-KEM, ML-DSA and AES-256-GCM are classical algorithms that resist quantum attacks; they run on ordinary computers.",
    "Quantum attack demonstrations (Shor, Grover) and BB84 are simulated: Aer simulator, toy size.",
    "kyber-py and dilithium-py are educational and not hardened; liboqs-python is the production route.",
    "A larger post-quantum payload is easier to detect; see the steganalysis results.",
    "The risk percentage is a transparent weighted score, not a probability.",
]
story = [Paragraph("PQC advisor: where each technique goes", styles["Title"]), table, Spacer(1, 10)]
story += [Paragraph(escape("- " + n), styles["BodyText"]) for n in notes]

out = Path("outputs/handouts")
out.mkdir(parents=True, exist_ok=True)
SimpleDocTemplate(str(out / "advisor_handout.pdf"), pagesize=landscape(A4),
                  leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24).build(story)
print("wrote", out / "advisor_handout.pdf")
