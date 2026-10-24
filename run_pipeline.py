"""
run_pipeline.py - poori pipeline ek command mein (Issue #2)

Chain: scan -> risk score -> mapper + estimator (risk report) -> PQC advisor report
       -> before/after migration score -> evidence gate -> tests.
Phir check karta hai ki committed outputs badle ya nahi.
Usage (repo root se): python run_pipeline.py [--project image|video|both]
Exit code: 0 = sab pass aur outputs unchanged, 1 = kuch fail ya badla, 2 = --input (not built yet)
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
ADVISOR_OUTPUT = ROOT / "docs" / "pqc_advisor_report.md"
BEFORE_AFTER = {"image": ROOT / "outputs" / "before_after_image.json",
                "video": ROOT / "outputs" / "before_after_video.json"}
PROJECTS = ("image", "video", "both")

# Scan ke liye target repos yahan hone chahiye (git submodules).
TARGETS = [ROOT / "data" / "targets" / "steganography",
           ROOT / "data" / "targets" / "final-year-part1"]

def build_steps(project="both"):
    """Stages in order: scan -> risk score -> mapper/report -> advisor -> before/after -> gate -> tests.

    A single-project run writes outputs/risk_scores_<project>.json so it never
    overwrites the committed outputs/risk_scores.json (which holds both projects).
    Tests always run last. The numbers in the titles follow the order.
    """
    if project not in PROJECTS:
        raise ValueError(f"unknown project {project!r}")
    risk = ["-m", "src.risk_run", "--project", project]
    if project != "both":
        risk += ["--out", f"outputs/risk_scores_{project}.json"]
    stages = [
        ("Scan both targets (scanner + edge flags)", ["src/run_all.py"]),
        (f"Risk score ({project})", risk),
        ("Mapper + estimator -> risk report", ["generate_risk_report.py"]),
        ("PQC advisor report (layer by layer)", ["scripts/advisor_report.py"]),
    ]
    if project in ("image", "both"):
        stages.append(("Before/after migration score (image)", ["src/before_after.py"]))
    if project in ("video", "both"):
        stages.append(("Before/after migration score (video)", ["src/before_after_video.py"]))
    stages += [
        ("Evidence gate (quantum run records)", ["-m", "src.evidence_gate"]),
        ("Test suite", ["run_tests.py"]),
    ]
    return [(f"{i}. {title}", args) for i, (title, args) in enumerate(stages, 1)]


def outputs_for(project="both"):
    """Committed outputs the pipeline must leave unchanged for this project."""
    out = list(OUTPUTS) + [ADVISOR_OUTPUT]
    if project == "both":
        out.append(RISK_OUTPUT)
    out += [path for name, path in BEFORE_AFTER.items() if project in (name, "both")]
    return out


STEPS = build_steps("both")


def digest(path):
    """File ka short hash (Windows CRLF aur LF ka fark ignore)."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()[:12]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the whole pipeline.")
    ap.add_argument("--project", choices=PROJECTS, default="both")
    ap.add_argument("--input", metavar="STEGO_IMAGE",
                    help="Stego Analyzer: not built yet (planned Week 6)")
    args = ap.parse_args(argv)
    if args.input:
        print("--input (Stego Analyzer) is not implemented yet. Planned for Week 6: upload, detect the "
              "hiding method, extract, identify the cipher, attack (toy size) or estimate, report.")
        return 2
    project = args.project
    outputs = outputs_for(project)

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
