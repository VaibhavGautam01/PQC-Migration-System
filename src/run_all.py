"""
run_all.py - Week 1 Day 5: scan BOTH target repos and write ONE findings.json.

Why this file exists:
  scanner.py scans one folder at a time. The rest of the pipeline
  (quantum_mapper.py, edge_cases.py, qubit_estimator.py) needs a single input
  file, so this script merges both scans and tags every finding with the
  project it came from.

Usage (run from the repo root):
    python src/run_all.py
Output:
    outputs/findings.json
"""
import json
import os
import re
import subprocess
import sys

# Make "import scanner" work no matter which folder we run this from.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scanner  # our Stage 1 scanner (uses scan_path and build_report)
from edge_merge import add_edge_flags

# Display name -> local folder. data/targets/ is gitignored, so the target
# repos are never pushed; they must be cloned there first.
TARGETS = {
    "Secure-Video-Steganography": "data/targets/steganography",
    "Final-Year-project-part1": "data/targets/final-year-part1",
}

OUT_PATH = "outputs/findings.json"

# Every finding must carry these keys, because downstream modules read them
# by name. If scanner.py ever drops one, check_schema() will catch it here
# instead of a later stage crashing with a confusing KeyError.
REQUIRED_KEYS = {
    "project", "file", "line", "primitive", "pattern_id", "description",
    "confidence", "key_size", "modulus_bits", "size_basis", "snippet",
    "is_default",
}


def tag_and_sort(project, findings):
    """Add the project name to each finding and sort them.

    Both repos contain files with the same name (app.py, metrics.py), so
    "file" alone is ambiguous. The "project" field fixes that.
    Sorting makes the output order stable, so re-running the script gives an
    identical file and git diffs only show real changes.
    """
    for f in findings:
        f["project"] = project
    return sorted(findings, key=lambda f: (f["file"], f["line"], f["pattern_id"]))


def check_schema(findings):
    """Return a list of problems (empty list = every finding is complete)."""
    problems = []
    for i, f in enumerate(findings):
        missing = REQUIRED_KEYS - set(f)
        if missing:
            where = str(f.get("file")) + ":" + str(f.get("line"))
            problems.append("finding #" + str(i) + " (" + where + ") missing " + str(sorted(missing)))
    return problems


def git_commit(path):
    """Return the HEAD commit hash of a cloned target repo, or None.

    Saving it makes a scan reproducible: anyone can check out the same
    commit of the target project and get the same findings.
    """
    try:
        res = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"],
                             capture_output=True, text=True, timeout=15)
        return res.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def comes_from_default(name, lines, depth=0):
    """True if variable `name` ultimately comes from a function DEFAULT value.

    Both of these count:
        def generate_keypair(bits=256):    # name == "bits"
        half = key_size // 2               # name == "half"; key_size has a default
    A default is not proof of real use: callers may pass a different value.
    """
    if depth > 3:
        return False
    esc = re.escape(name)
    def_rx = re.compile(r"\bdef\s+\w+\s*\(.*\b" + esc + r"\s*(?::\s*\w+)?\s*=\s*\d+")
    div_rx = re.compile(r"^\s*" + esc + r"\s*=\s*(\w+)\s*//\s*\d+")
    for ln in lines:
        if def_rx.search(ln):
            return True
    for ln in lines:
        m = div_rx.match(ln)
        if m and comes_from_default(m.group(1), lines, depth + 1):
            return True
    return False


def mark_defaults(root, findings):
    """Add finding["is_default"] = True when key_size is only a default value.

    Fixes the dashboard overcount: rsa_utils.py defaults (bits=256) are not
    the sizes really used (callers pass bits=128).
    """
    cache = {}
    for f in findings:
        f["is_default"] = False
        m = re.match(r"resolved from '(\w+)'", f.get("size_basis") or "")
        if not m:
            continue
        path = os.path.join(root, f["file"])
        if path not in cache:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                cache[path] = fh.read().splitlines()
        f["is_default"] = comes_from_default(m.group(1), cache[path])


def main():
    projects = {}      # per-project summary (counts), copied from scanner
    all_findings = []  # merged list of every finding from both repos

    for name, path in TARGETS.items():
        if not os.path.isdir(path):
            print("missing target folder:", path, "(clone it under data/targets first)")
            return 1
        # scan_path walks the folder; tag_and_sort labels and orders results
        found = tag_and_sort(name, scanner.scan_path(path))
        mark_defaults(path, found)  # flag sizes that are only defaults
        projects[name] = scanner.build_report(path, found)["summary"]
        projects[name]["commit"] = git_commit(path)  # reproducibility
        all_findings.extend(found)

    # Safety net: refuse to write a file that downstream stages cannot read.
    problems = check_schema(all_findings)

    # Overall count per primitive (RSA / SHA / ...), useful for the team review.
    overall = {}
    for f in all_findings:
        overall[f["primitive"]] = overall.get(f["primitive"], 0) + 1

    report = {
        "schema_version": "1.1",                    # bump if field names change
        "scanner_version": scanner.SCANNER_VERSION,  # which scanner produced this
        "projects": projects,
        "by_primitive": overall,
        "total_findings": len(all_findings),
        "findings": all_findings,
    }

    add_edge_flags(report, TARGETS)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    print("Wrote", OUT_PATH, "-", len(all_findings), "findings")
    for name, s in projects.items():
        print(" ", name, "->", s["total_findings"], "findings,", s["by_primitive"])
    print("  Overall by primitive:", ", ".join(k + "=" + str(v) for k, v in sorted(overall.items())))
    if problems:
        print("  Schema check: FAILED")
        for p in problems:
            print("   -", p)
        return 1
    print("  Schema check: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
