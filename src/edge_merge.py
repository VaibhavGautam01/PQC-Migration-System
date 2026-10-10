"""
edge_merge.py - Add edge-case flags (padding, indirect usage) to the
combined findings report built by run_all.py.

Adds an "edge_flag" key to RSA findings that use textbook modular
exponentiation without padding, plus a top-level "edge_cases" section
per project and an "edge_case_totals" summary.
"""
from pathlib import Path

from edge_cases import check_padding, find_indirect_usage


def add_edge_flags(report, targets):
    """report: dict built by run_all.py. targets: {project: folder}."""
    per_project = {}
    total_padding = 0
    total_indirect = 0

    for project, folder in targets.items():
        root = Path(folder)
        findings = [f for f in report["findings"] if f["project"] == project]

        padding = []
        for f in findings:
            if "MODEXP" not in f["pattern_id"]:
                continue
            path = root / f["file"]
            if not path.is_file():
                continue
            flag = check_padding(path, f["line"])
            if flag:
                flag["file"] = f["file"]
                f["edge_flag"] = flag["flag"]
                padding.append(flag)

        providers = {f["file"] for f in findings}
        indirect = find_indirect_usage(root, provider_files=providers)

        per_project[project] = {"padding": padding, "indirect_usage": indirect}
        total_padding += len(padding)
        total_indirect += len(indirect)

    report["edge_cases"] = per_project
    report["edge_case_totals"] = {
        "padding": total_padding,
        "indirect_usage": total_indirect,
    }
    return report