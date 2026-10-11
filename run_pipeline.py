"""
run_pipeline.py - poori pipeline ek command mein (Issue #2)

Chain: scanner (run_all.py) -> mapper + estimator (generate_risk_report.py)
       -> tests. Phir check karta hai ki committed outputs badle ya nahi.
Usage (repo root se): python run_pipeline.py
Exit code: 0 = sab pass aur outputs unchanged, 1 = kuch fail ya badla
"""
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Pipeline ke generated outputs; inka hash pehle aur baad mein milate hain.
OUTPUTS = [ROOT / "outputs" / "findings.json",
           ROOT / "docs" / "risk_report.md"]

# Scan ke liye target repos yahan hone chahiye (git submodules).
TARGETS = [ROOT / "data" / "targets" / "steganography",
           ROOT / "data" / "targets" / "final-year-part1"]

STEPS = [
    ("1. Scan both targets (scanner + edge flags)", ["src/run_all.py"]),
    ("2. Mapper + estimator -> risk report", ["generate_risk_report.py"]),
    ("3. Test suite", ["run_tests.py"]),
]


def digest(path):
    """File ka short hash (Windows CRLF aur LF ka fark ignore)."""
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()[:12]


def main():
    # Khali target folder se scan 0 findings dega aur sab chupchap toot jayega.
    missing = [t for t in TARGETS if not t.is_dir() or not any(t.iterdir())]
    if missing:
        for t in missing:
            print(f"MISSING: {t} khali ya nahi hai. Chalao: git submodule update --init")
        return 1

    before = {p: digest(p) for p in OUTPUTS if p.exists()}

    for title, args in STEPS:
        print(f"\n=== {title}")
        result = subprocess.run([sys.executable] + args, cwd=ROOT)
        if result.returncode != 0:
            print(f"FAILED: {title} (exit code {result.returncode})")
            return 1

    print("\n=== Output check (pipeline se pehle vs baad)")
    changed = False
    for path in OUTPUTS:
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
