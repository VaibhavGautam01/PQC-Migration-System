"""Stage 7 exports: CSV and PDF of an analyzer report.  Owner: Uday (written in Week 6, please review).

The report dict (schema in docs/analyzer_spec.md) is built and checked by pipeline.py and schema.py. These
functions only write it out. Both outputs carry the result, the label of every quantum result, the limits and
the words "weighted score, not a probability".
"""
import csv
from pathlib import Path


def flatten(report, prefix=""):
    """Turn the nested report into (field, value) rows. Bytes are never put in the rows."""
    rows = []
    for key, value in report.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            rows += flatten(value, name + ".")
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    rows += flatten(item, f"{name}[{i}].")
                else:
                    rows.append((f"{name}[{i}]", item))
        else:
            rows.append((name, value))
    return rows


def export_csv(report, path):
    rows = flatten({k: v for k, v in report.items() if k != "stage_log"})
    rows += [(f"stage.{r['stage']}", r["status"]) for r in report.get("stage_log", [])]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["field", "value"])
        w.writerows(rows)
    return Path(path)


def _lines(report):
    a = report.get("attack") or {}
    s = report.get("score")
    lines = ["Stego Analyzer report", "",
             f"Image: {report['input']['file']}", f"SHA-256: {report['input']['sha256']}",
             f"Created (UTC): {report['created_utc']}", f"Pipeline: {report['pipeline_status']}", ""]
    if report.get("hiding"):
        lines.append(f"Hiding method: {report['hiding']['method']}")
    if report.get("cipher"):
        lines.append(f"Cipher: {report['cipher']['kind']}")
    if report.get("technique"):
        lines.append(f"Technique: {report['technique']['algorithm']} ({report['technique']['reason']})")
    if a.get("state"):
        lines.append(f"Result: {a['state']}" + (f" ({a['label']})" if a.get("label") else ""))
    if a.get("recovered_message"):
        lines.append(f"Recovered message: {a['recovered_message']}")
    if report.get("estimate"):
        lines.append(f"Estimate: {report['estimate'].get('published')}")
    if s:
        lines += ["", f"Risk score: {s['overall']}% ({s['band']}); quantum {s['quantum']}%, classical "
                      f"{s['classical']}%; weights {s['weights_version']}",
                  "A weighted score, not a probability."]
    lines += ["", "Limits:"] + [f"- {x}" for x in report.get("limits", [])]
    return lines


def export_pdf(report, path):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(str(path), pagesize=A4)
    width, height = A4
    y = height - 50
    for line in _lines(report):
        for chunk in ([line[i:i + 95] for i in range(0, len(line), 95)] or [""]):
            if y < 50:
                c.showPage()
                y = height - 50
            c.setFont("Helvetica-Bold" if line == "Stego Analyzer report" else "Helvetica", 10)
            c.drawString(40, y, chunk)
            y -= 14
    c.save()
    return Path(path)
