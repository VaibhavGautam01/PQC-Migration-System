"""Export findings.json to CSV and PDF.
Usage: python scripts/export_findings.py FINDINGS_JSON OUT_DIR
"""
import csv
import json
import sys
from pathlib import Path

PREFERRED = ["file", "line", "pattern", "algorithm", "key_bits", "severity"]


def load_findings(path):
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return data["findings"] if isinstance(data, dict) and "findings" in data else data


def columns(findings):
    seen = []
    for f in findings:
        for k in f:
            if k not in seen:
                seen.append(k)
    return [k for k in PREFERRED if k in seen] + [k for k in seen if k not in PREFERRED]


def cell(v):
    return v if isinstance(v, (str, int, float)) or v is None else json.dumps(v, ensure_ascii=False)


def write_csv(findings, cols, out):
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for f in findings:
            w.writerow([cell(f.get(c, "")) for c in cols])


def write_pdf(findings, cols, out, source):
    from xml.sax.saxutils import escape
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    shown = cols[:6]  # keep the PDF readable; the CSV has every column
    styles = getSampleStyleSheet()
    cell_style = styles["BodyText"]
    cell_style.fontSize = 7
    cell_style.leading = 8
    rows = [[Paragraph(f"<b>{escape(c)}</b>", cell_style) for c in shown]]
    for f in findings:
        rows.append([Paragraph(escape(str(cell(f.get(c, "")))), cell_style) for c in shown])
    doc = SimpleDocTemplate(str(out), pagesize=landscape(A4), title="Scanner findings")
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    doc.build([
        Paragraph("Scanner findings", styles["Title"]),
        Paragraph(f"Source: {escape(source)}. {len(findings)} findings. Full columns are in the CSV.", styles["Normal"]),
        Spacer(1, 8),
        table,
    ])


def main(findings_path, out_dir):
    findings = load_findings(findings_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    cols = columns(findings)
    write_csv(findings, cols, out / "findings.csv")
    write_pdf(findings, cols, out / "findings.pdf", Path(findings_path).name)
    print(f"wrote {out / 'findings.csv'} and {out / 'findings.pdf'} ({len(findings)} findings)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])