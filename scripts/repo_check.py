"""
repo_check.py - repository consistency check (Week 4 Day 4 / Week 5 Day 3).

Checks, with no network and no simulator:
  1. no generated file is tracked by git (needs git; skipped without it)
  2. the findings count in README.md and docs/final_report.md equals outputs/findings.json
  3. the weights version named in README.md and docs/risk_model.md equals data/risk_weights.json
     and data/risk_weights.lock.json
  4. no known stale number is left in README.md or docs/final_report.md
  5. (--count-tests) the test count in the README badge equals the tests run_tests.py runs
  6. open FILL markers in the report chapters are listed (information, not a failure)
  7. (--release) the release gate: no FILL marker and no "CONFIRM WITH SIR" marker left in docs/, the evidence
     gate passes in strict mode, and no tracked file has uncommitted changes

  python scripts/repo_check.py                 # fast checks
  python scripts/repo_check.py --count-tests   # also compare the README test count (about 10 seconds)
  python scripts/repo_check.py --release       # everything above, before the v2.0.0 tag

Exit code 0 = no problem found, 1 = at least one problem.
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Files that scripts generate. They must not be tracked (rule: do not commit generated files).
GENERATED = ["legacy_log.txt", "docs/risk_report_sections.md", "*.zip", "*.pkl", "outputs/tmp_*",
             "outputs/risk_scores_*.json", "outputs/*.png", "outputs/toykeys/*", "outputs/mapped_findings.json"]
# Numbers that were true once and are wrong now.
STALE = ["26 findings", "26 of 26 findings", "372 tests", "504 tests", "504_passing", "about 8 bits",
         "frozen as v0.1", "Weights v0.1"]


def tracked_files(root=ROOT):
    """Tracked file names, or None when git is not available."""
    try:
        p = subprocess.run(["git", "ls-files"], cwd=str(root), capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.splitlines() if p.returncode == 0 else None


def read(root, rel):
    try:
        return (Path(root) / rel).read_text(encoding="utf-8-sig")
    except OSError:
        return None


def check_generated_not_tracked(tracked):
    if tracked is None:
        return ["SKIP: git is not available, tracked files not checked"], []
    bad = sorted(f for f in tracked if any(fnmatch.fnmatch(f, pat) for pat in GENERATED))
    return [], [f"tracked generated file: {f}  (fix: git rm --cached {f}, and add it to .gitignore)" for f in bad]


def findings_count(root):
    raw = read(root, "outputs/findings.json")
    if raw is None:
        return None
    data = json.loads(raw)
    return len(data["findings"] if isinstance(data, dict) else data)


def check_findings_count(root):
    n = findings_count(root)
    if n is None:
        return ["SKIP: outputs/findings.json not found"], []
    problems = []
    for rel in ("README.md", "docs/final_report.md"):
        text = read(root, rel)
        if text is None:
            continue
        for m in re.finditer(r"(?<!RSA \()(?<!SHA \()\b(\d+)\s+findings\b", text):
            if int(m.group(1)) != n and int(m.group(1)) > 5:       # small counts are per-project rows
                problems.append(f"{rel}: says {m.group(1)} findings, outputs/findings.json has {n}")
    return [], sorted(set(problems))


def check_weights_version(root):
    w = read(root, "data/risk_weights.json")
    if w is None:
        return ["SKIP: data/risk_weights.json not found"], []
    version = json.loads(w)["version"]
    problems = []
    lock = read(root, "data/risk_weights.lock.json")
    if lock and json.loads(lock).get("version") != version:
        problems.append(f"data/risk_weights.lock.json has version {json.loads(lock).get('version')}, weights file has {version}")
    for rel, pattern in (("README.md", r"frozen as (v\d+\.\d+)"), ("docs/risk_model.md", r"^# Risk Model \((v\d+\.\d+)\)")):
        text = read(root, rel)
        if text is None:
            continue
        for m in re.finditer(pattern, text, flags=re.M):
            if m.group(1) != version:
                problems.append(f"{rel}: names weights {m.group(1)}, weights file is {version}")
    return [], problems


def check_stale_numbers(root):
    problems = []
    for rel in ("README.md", "docs/final_report.md"):
        text = read(root, rel)
        if text is None:
            continue
        problems += [f"{rel}: stale text {s!r}" for s in STALE if s in text]
    return [], problems


def badge_test_count(root):
    text = read(root, "README.md")
    m = re.search(r"Tests-(\d+)_passing", text or "")
    return int(m.group(1)) if m else None


# The same folders run_tests.py runs (a test checks they stay equal).
TEST_DIRS = ["tests", "notebook"]


def count_tests(root=ROOT):
    """Number of test cases run_tests.py would run, counted the way run_tests.py discovers them."""
    import unittest
    sys.path[:0] = [str(Path(root)), str(Path(root) / "src")]
    total = 0
    for name in TEST_DIRS:
        folder = Path(root) / name
        suite = unittest.defaultTestLoader.discover(start_dir=str(folder), pattern="test_*.py",
                                                    top_level_dir=str(folder))
        total += suite.countTestCases()
    return total


def check_test_count(root):
    actual, badge = count_tests(root), badge_test_count(root)
    if badge is None:
        return [], ["README.md: no 'Tests-N_passing' badge found"]
    if badge != actual:
        return [], [f"README.md: badge says {badge} tests, run_tests.py runs {actual} (fix: set both README numbers to {actual})"]
    return [f"OK: README test count {badge} matches"], []


def fill_markers(root):
    out = []
    for path in sorted((Path(root) / "docs").rglob("*.md")):
        n = len(re.findall(r"\bFILL\b", path.read_text(encoding="utf-8-sig", errors="replace")))
        if n:
            out.append(f"{path.relative_to(root).as_posix()}: {n} FILL marker(s) still open")
    return out


def marker_lines(root, word):
    """docs/ lines that still contain the marker word (case sensitive)."""
    out = []
    for path in sorted((Path(root) / "docs").rglob("*.md")):
        for i, line in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
            if word in line and not line.lstrip().startswith(("Status:", "#")) and "markers" not in line.lower():
                out.append(f"{path.relative_to(root).as_posix()}:{i}")
    return out


def check_release(root=ROOT, data_dir=None):
    """The extra checks for the release tag. Returns problems only."""
    problems = []
    for word, what in (("FILL", "open FILL marker"), ("CONFIRM WITH SIR", "open CONFIRM WITH SIR marker")):
        for where in marker_lines(root, word):
            problems.append(f"{what} at {where}")
    sys.path[:0] = [str(Path(root))]
    from src import evidence_gate
    _, errors, warnings = evidence_gate.run_gate(root=Path(root), strict=True, data_dir=data_dir)
    problems += [f"evidence gate (strict): {e}" for e in errors + warnings]
    try:
        p = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=str(root),
                           capture_output=True, text=True, timeout=30)
        if p.returncode == 0:
            problems += [f"uncommitted change: {line[3:]}" for line in p.stdout.splitlines() if line.strip()]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return problems


def run_checks(root=ROOT, tracked="auto", count_tests=False):
    """Return (notes, problems). tracked='auto' asks git."""
    tracked = tracked_files(root) if tracked == "auto" else tracked
    notes, problems = [], []
    checks = [lambda: check_generated_not_tracked(tracked), lambda: check_findings_count(root),
              lambda: check_weights_version(root), lambda: check_stale_numbers(root)]
    if count_tests:
        checks.append(lambda: check_test_count(root))
    for check in checks:
        n, p = check()
        notes += n
        problems += p
    notes += fill_markers(root)
    return notes, problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--count-tests", action="store_true")
    ap.add_argument("--release", action="store_true", help="also run the release gate")
    args = ap.parse_args(argv)
    notes, problems = run_checks(count_tests=args.count_tests or args.release)
    if args.release:
        problems += check_release()
    for n in notes:
        print(n)
    for p in problems:
        print("PROBLEM:", p)
    print(f"\n{len(problems)} problem(s) found." if problems else "\nNo problem found.")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
