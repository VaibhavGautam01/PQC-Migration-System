"""
evidence_check_weeks1to4.py - Week 5 Day 3: final evidence check for Weeks 1 to 4.

"Every quantum run has its record; every number names its version" (the plan's own words for
this task). This script checks TWO things the existing evidence_gate.py does not:

  1. ORPHANED CLAIMS: every specific quantum result mentioned in the attack-evidence docs
     (an N, a p, a key, a period, a factor pair) should be backed by an actual record in
     data/quantum_runs.json. A number quoted in prose with no matching run is a claim without
     evidence - this is exactly the kind of mismatch a reviewer (or sir, or a viva examiner)
     would probe.
  2. VERSION MENTIONS: every doc that discusses quantum results should name qiskit/qiskit-aer
     versions and a commit somewhere, not just once at the very top of one file.

This does NOT replace `python -m src.evidence_gate --strict`, which checks the INTERNAL
consistency of data/quantum_runs.json (schema, change-the-question, diagram files existing).
Run both; they check different things.

Usage (from the project root, venv active):
  python extras/evidence_check_weeks1to4.py
  python extras/evidence_check_weeks1to4.py --docs docs/attack_evidence.md docs/attack_evidence_master.md
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DOCS = ["docs/attack_evidence.md", "docs/attack_evidence_week2.md",
                "docs/attack_evidence_week3.md", "docs/attack_evidence_master.md"]

# Patterns that look like a specific, checkable quantum claim in prose.
N_PATTERN = re.compile(r"\bN\s*=\s*(\d+)\b")
P_PATTERN = re.compile(r"\bp\s*=\s*(\d+)\b")
PERIOD_PATTERN = re.compile(r"\bperiod\s*(?:found\s*)?(?:r\s*=\s*|is\s*|was\s*)?(\d+)\b", re.I)
VERSION_WORDS = ("qiskit", "qiskit-aer", "kyber-py", "dilithium-py", "pycryptodome", "commit")


def load_runs(runs_path: Path) -> list:
    if not runs_path.exists():
        return []
    data = json.loads(runs_path.read_text(encoding="utf-8"))
    return data.get("runs", data) if isinstance(data, dict) else data


def claimed_values(doc_text: str) -> dict:
    """Every N=, p= and period mentioned in a doc's prose (not inside a code block)."""
    # strip fenced code blocks so we don't flag example commands as claims
    text = re.sub(r"```.*?```", "", doc_text, flags=re.S)
    return {
        "N": sorted({int(m) for m in N_PATTERN.findall(text)}),
        "p": sorted({int(m) for m in P_PATTERN.findall(text)}),
        "period": sorted({int(m) for m in PERIOD_PATTERN.findall(text)}),
    }


def backed_values(runs: list) -> dict:
    """Every N, p and period that actually has a real run record behind it."""
    out = {"N": set(), "p": set(), "period": set()}
    for run in runs:
        inputs = run.get("inputs", {})
        result = run.get("result", {})
        if "N" in inputs:
            out["N"].add(inputs["N"])
        if "p" in inputs:
            out["p"].add(inputs["p"])
        for key in ("period", "order_r"):
            if result.get(key) is not None:
                out["period"].add(result[key])
            if inputs.get(key) is not None:
                out["period"].add(inputs[key])
    return {k: sorted(v) for k, v in out.items()}


def check_doc(path: Path, backed: dict) -> dict:
    text = path.read_text(encoding="utf-8")
    claimed = claimed_values(text)
    orphans = {kind: [v for v in claimed[kind] if v not in backed[kind]] for kind in claimed}
    orphans = {k: v for k, v in orphans.items() if v}
    version_mentions = sum(1 for w in VERSION_WORDS if w.lower() in text.lower())
    try:
        shown = str(path.relative_to(ROOT))
    except ValueError:
        shown = str(path)
    return {"file": shown, "claimed": claimed, "orphaned_claims": orphans,
           "version_word_mentions": version_mentions,
           "has_fill_markers_remaining": "[FILL" in text}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--docs", nargs="+", default=DEFAULT_DOCS)
    ap.add_argument("--runs", default="data/quantum_runs.json")
    ap.add_argument("--json", help="also write the full result to this JSON file")
    args = ap.parse_args()

    runs_path = Path(args.runs) if Path(args.runs).is_absolute() else ROOT / args.runs
    runs = load_runs(runs_path)
    backed = backed_values(runs)
    try:
        shown_path = runs_path.relative_to(ROOT)
    except ValueError:
        shown_path = runs_path
    print(f"Loaded {len(runs)} run records from {shown_path}")
    print(f"Backed values -> N: {backed['N']}  p: {backed['p']}  period/order: {backed['period']}\n")

    results = []
    any_problem = False
    for doc in args.docs:
        path = Path(doc) if Path(doc).is_absolute() else ROOT / doc
        if not path.exists():
            print(f"[skip] {doc} does not exist")
            continue
        r = check_doc(path, backed)
        results.append(r)
        status = "OK" if not r["orphaned_claims"] and not r["has_fill_markers_remaining"] else "CHECK"
        print(f"[{status}] {r['file']}")
        if r["orphaned_claims"]:
            any_problem = True
            print(f"    orphaned claims (mentioned in prose, no matching run record): "
                 f"{r['orphaned_claims']}")
        if r["has_fill_markers_remaining"]:
            any_problem = True
            print(f"    still has [FILL] markers - not finished")
        if r["version_word_mentions"] == 0:
            print(f"    WARNING: no version words (qiskit, commit, ...) found anywhere in this file")
        print()

    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"backed_values": backed, "docs": results}, indent=2) + "\n",
                       encoding="utf-8")
        print(f"wrote {out}")

    print("Also run: python -m src.evidence_gate --strict  (checks the JSON file's own internal "
         "consistency - this script only checks the DOCS against it)")
    return 1 if any_problem else 0


if __name__ == "__main__":
    raise SystemExit(main())
