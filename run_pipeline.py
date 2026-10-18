"""
run_pipeline.py - poori pipeline ek command mein (Issue #2)

Chain: scanner (run_all.py) -> mapper + estimator (generate_risk_report.py)
       -> tests. Phir check karta hai ki committed outputs badle ya nahi.
Usage (repo root se): python run_pipeline.py [--project image|video|both]
Exit code: 0 = sab pass aur outputs unchanged, 1 = kuch fail ya badla
"""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Pipeline ke generated outputs; inka hash pehle aur baad mein milate hain.
OUTPUTS = [ROOT / "outputs" / "findings.json",
           ROOT / "docs" / "risk_report.md"]
# Risk scores are only compared for --project both (that is the committed file).
RISK_OUTPUT = ROOT / "outputs" / "risk_scores.json"
PROJECTS = ("image", "video", "both")

# Scan ke liye target repos yahan hone chahiye (git submodules).
TARGETS = [ROOT / "data" / "targets" / "steganography",
           ROOT / "data" / "targets" / "final-year-part1"]

def build_steps(project="both"):
    """Stages in order: scan -> risk score -> mapper/report -> tests (tests always last).

    A single-project run writes outputs/risk_scores_<project>.json so it never
    overwrites the committed outputs/risk_scores.json (which holds both projects).
    """
    if project not in PROJECTS:
        raise ValueError(f"unknown project {project!r}")
    risk = ["-m", "src.risk_run", "--project", project]
    if project != "both":
        risk += ["--out", f"outputs/risk_scores_{project}.json"]
    return [
        ("1. Scan both targets (scanner + edge flags)", ["src/run_all.py"]),
        (f"2. Risk score ({project})", risk),
        ("3. Mapper + estimator -> risk report", ["generate_risk_report.py"]),
        ("4. Test suite", ["run_tests.py"]),
    ]


STEPS = build_steps("both")


def digest(path):
    """File ka short hash (Windows CRLF aur LF ka fark ignore)."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()[:12]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the whole pipeline.")
    ap.add_argument("--project", choices=PROJECTS, default="both")
    project = ap.parse_args(argv).project
    outputs = OUTPUTS + ([RISK_OUTPUT] if project == "both" else [])

    # Khali target folder se scan 0 findings dega aur sab chupchap toot jayega.
    missing = [t for t in TARGETS if not t.is_dir() or not any(t.iterdir())]
    if missing:
        for t in missing:
            print(f"MISSING: {t} khali ya nahi hai. Chalao: git submodule update --init")
        return 1

    before = {p: digest(p) for p in outputs if p.exists()}

    for title, args in build_steps(project):
        print(f"\n=== {title}")
        result = subprocess.run([sys.executable] + args, cwd=ROOT)
        if result.returncode != 0:
            print(f"FAILED: {title} (exit code {result.returncode})")
            return 1

    print("\n=== Output check (pipeline se pehle vs baad)")
    changed = False
    for path in outputs:
        old, new = before.get(path), digest(path)
        state = "NEW" if old is None else (
            "UNCHANGED" if old == new else "CHANGED")
        changed = changed or state != "UNCHANGED"
        print(f"{state:<10}{path.relative_to(ROOT)}  ({old} -> {new})")

    if changed:
        print("\nRESULT: outputs badle. Review karo, phir commit ya git checkout.")
        return 1
    print("\nRESULT: PIPELINE OK, outputs bilkul same, tests pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
