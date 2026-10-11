"""build_dashboard.py - builds docs/final_dashboard.md from the pipeline outputs.

Pipeline position:
    findings.json -> quantum_mapper -> cbom -> build_dashboard -> final_dashboard.md

Every number in the dashboard is computed from the data files; nothing is typed
in by hand. Sections: Summary, Detection, Mapping, Risk, Demo, Conclusion.

Standard library only (plus quantum_mapper and cbom from this repo).
"""

import json
import os
import sys

import quantum_mapper as qm

TITLE = "# Final Dashboard: AI-Powered PQC Migration Advisor"
SECTIONS = ("Summary", "Detection", "Mapping", "Risk", "Demo", "Conclusion")
PENDING = "_Not generated yet._"

# ---------------------------------------------------------------------------
# Context: everything the sections need, computed once
# ---------------------------------------------------------------------------
def build_context(findings_path, facts_path=None):
    """Load findings, apply confirmed overrides, map them. Returns a context dict."""
    findings, _problems, ov_report = qm.prepare_findings(findings_path, facts_path)
    mapped = qm.map_findings(findings)
    ctx = {"mapped": mapped, "overrides": ov_report,
           "caveats": qm.collect_caveats(mapped, ov_report)}
    return ctx

# ---------------------------------------------------------------------------
# Section renderers (each returns Markdown without the section header)
# ---------------------------------------------------------------------------
def _group_by_project(mapped):
    """Map project name -> list of mapped findings (insertion order sorted by name)."""
    groups = {}
    for item in mapped:
        groups.setdefault(item.get("project") or "(unknown project)", []).append(item)
    return dict(sorted(groups.items()))


def _count_text(values):
    """'high 5, medium 2' style summary of a list of labels ('-' if none)."""
    counts = {}
    for value in values:
        if value:
            counts[str(value)] = counts.get(str(value), 0) + 1
    return ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) or "-"


def render_summary(ctx):
    """Headline numbers: findings, projects, quantum exposure, open data caveats."""
    mapped = ctx["mapped"]
    projects = _group_by_project(mapped)
    shor = sum(1 for m in mapped if m["quantum_algorithm"] == qm.SHOR)
    grover = sum(1 for m in mapped if m["quantum_algorithm"] == qm.GROVER)
    unknown = sum(1 for m in mapped if m["canonical_primitive"] is None)
    lines = [
        f"- **Findings:** {len(mapped)} across {len(projects)} project(s): "
        + ", ".join(projects) + ".",
        f"- **Broken by Shor's algorithm** (RSA, ECC, DSA, DH): {shor} finding(s).",
        f"- **Weakened by Grover's algorithm** (AES, SHA): {grover} finding(s). "
        "This is a quadratic speed-up, not a full break.",
        f"- **Unrecognised primitives:** {unknown}.",
        f"- **Open data caveats:** {len(ctx['caveats'])} (listed under Mapping).",
    ]
    return "\n".join(lines)


def render_detection(ctx):
    """Per-project detection table plus a note on what the scanner cannot see."""
    lines = ["| Project | Findings | Files | Primitives | Confidence |", "|---|---|---|---|---|"]
    for project, items in _group_by_project(ctx["mapped"]).items():
        files = {m.get("file") for m in items}
        prims = sorted({m["canonical_primitive"] or "(unrecognised)" for m in items})
        lines.append(f"| {cb_md(project)} | {len(items)} | {len(files)} | {', '.join(prims)} | "
                     f"{_count_text(m.get('confidence') for m in items)} |")
    lines += ["", "The scanner is pattern-based. Facts it cannot see, such as the key size a "
              "function is called with, come from manual review (`data/manual_facts.json`)."]
    confirmed = sum(1 for o in ctx["overrides"] if o["confirmed"])
    pending = sum(1 for o in ctx["overrides"] if not o["confirmed"])
    if ctx["overrides"]:
        lines.append(f"Manual size overrides: {confirmed} confirmed and applied, {pending} unconfirmed (not applied).")
    return "\n".join(lines)


def render_mapping(ctx):
    """Per-primitive mapping table plus the data caveats."""
    rows = {}
    for m in ctx["mapped"]:
        rows.setdefault(m["canonical_primitive"], []).append(m)
    lines = ["| Primitive | Findings | Quantum algorithm | Impact | Recommended replacement |",
             "|---|---|---|---|---|"]
    order = list(qm.PRIMITIVE_TABLE) + [None]
    for prim in order:
        if prim not in rows:
            continue
        first = rows[prim][0]
        lines.append(f"| {cb_md(prim or '(unrecognised)')} | {len(rows[prim])} | {cb_md(first['quantum_algorithm'])} | "
                     f"{cb_md(first['impact'])} | {cb_md(first['pqc_replacement'])} |")
    lines += ["", "**Data caveats**", ""]
    lines += [f"- {c}" for c in ctx["caveats"]] or ["- None."]
    return "\n".join(lines)


def cb_md(value):
    """Escape a value for a Markdown table cell ('-' for empty)."""
    if value is None or value == "":
        return "-"
    return str(value).replace("|", "\\|").replace("\n", " ")


# ---------------------------------------------------------------------------
# Assembly and CLI
# ---------------------------------------------------------------------------
RENDERERS = {
    "Summary": render_summary,
    "Detection": render_detection,
    "Mapping": render_mapping,
}


def build_dashboard(ctx):
    """Assemble the full dashboard Markdown. Sections without a renderer say so."""
    parts = [TITLE, "",
             "Generated by `src/build_dashboard.py` from the pipeline data files. "
             "Re-run it instead of editing this file by hand.", ""]
    for name in SECTIONS:
        renderer = RENDERERS.get(name)
        parts += [f"## {name}", "", renderer(ctx) if renderer else PENDING, ""]
    return "\n".join(parts)


VALUE_FLAGS = ["--facts", "--out"]
USAGE = "usage: build_dashboard.py FINDINGS.json [--facts FILE] [--out FILE]"


def main(argv=None):
    """CLI entry point: build the dashboard and write it (default docs/final_dashboard.md)."""
    parsed = cb_parse(list(sys.argv[1:] if argv is None else argv), VALUE_FLAGS)
    if parsed is None or len(parsed[0]) != 1:
        print(USAGE)
        return 2
    paths, values, _ = parsed
    out = values["--out"] or os.path.join("docs", "final_dashboard.md")
    ctx = build_context(paths[0], values["--facts"])
    text = build_dashboard(ctx)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Dashboard written to {out} ({len(ctx['mapped'])} findings)")
    return 0


def cb_parse(args, value_flags):
    """Minimal argument parser. Returns (paths, values, {}) or None on error."""
    values = {flag: None for flag in value_flags}
    paths = []
    it = iter(args)
    for arg in it:
        if arg in values:
            value = next(it, None)
            if value is None:
                return None
            values[arg] = value
        else:
            paths.append(arg)
    return paths, values, {}


if __name__ == "__main__":
    sys.exit(main())
