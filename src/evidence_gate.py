"""
evidence_gate.py - the evidence gate for quantum runs (Week 2 Day 2).

Reads data/quantum_runs.json (rule 4) and every data/quantum_runs_*.json (for example the Q6 and
Q7 files) and checks that every quantum run has a complete record. Errors (always fail):
  * a record that fails quantum_runs.validate_run()
  * a duplicate run_id
  * a circuit diagram file that does not exist
Warnings (become errors with --strict, used at release):
  * a question_group that fails the change-the-question test (rule 6): it needs at least
    two runs with different inputs and different results.
A record in an extra file that is not in the evidence format yet is a warning (an error with
--strict, used at release), not an error, so a team member can migrate a file step by step.
No runs yet is not an error, so the gate gets stricter as runs arrive.
Run:  python -m src.evidence_gate [--strict]
Aer simulator, toy size.
"""
import argparse
import os
from pathlib import Path

from src import quantum_runs as QR

ROOT = Path(__file__).resolve().parent.parent


def check_runs(runs, root=ROOT, strict=False):
    """Return (errors, warnings), two lists of strings."""
    errors, warnings = [], []
    seen = set()
    for i, run in enumerate(runs):
        rid = run.get("run_id", f"#{i}")
        for problem in QR.validate_run(run):
            errors.append(f"run {rid}: {problem}")
        if rid in seen:
            errors.append(f"run {rid}: duplicate run_id")
        seen.add(rid)
        diagram = run.get("diagram_file")
        if isinstance(diagram, str) and not (Path(root) / diagram).is_file():
            errors.append(f"run {rid}: circuit diagram file not found: {diagram}")
    groups = sorted({r.get("question_group") for r in runs if r.get("question_group")})
    for g in groups:
        if not QR.check_change_the_question(runs, g):
            warnings.append(f"group {g}: fails change-the-question (needs 2 or more runs with "
                            f"different inputs and different results)")
    if strict:
        errors, warnings = errors + warnings, []
    return errors, warnings


def unconverted_warnings(extra_runs, file_problems):
    """One warning per extra file that still has records outside the evidence format."""
    bad = {}
    for run in extra_runs:
        problems = QR.validate_run({k: v for k, v in run.items() if k != "_source"})
        if problems:
            bad.setdefault(run["_source"], []).append(problems)
    warnings = [f"{name}: {len(items)} record(s) not in the evidence format yet "
                f"({'; '.join(items[0][:3])}; ...)" for name, items in sorted(bad.items())]
    return warnings + [f"{p}" for p in file_problems]


def run_gate(path=None, root=ROOT, strict=False, data_dir=None):
    """(n_runs_checked, errors, warnings). With path, only that file is checked (as before)."""
    if path is not None:
        runs = QR.load_runs(path)
        errors, warnings = check_runs(runs, root, strict)
        return len(runs), errors, warnings
    main_path = Path(data_dir) / "quantum_runs.json" if data_dir else None
    runs = QR.load_runs(main_path)
    extra, file_problems = QR.load_extra_runs(data_dir)
    runs = runs + [{k: v for k, v in r.items() if k != "_source"} for r in extra if not QR.validate_run(
        {k: v for k, v in r.items() if k != "_source"})]
    errors, warnings = check_runs(runs, root, strict=False)
    warnings = warnings + unconverted_warnings(extra, file_problems)
    if strict:
        errors, warnings = errors + warnings, []
    return len(runs), errors, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Evidence gate for quantum runs.")
    ap.add_argument("--strict", action="store_true",
                    help="treat change-the-question warnings as errors (release gate)")
    args = ap.parse_args(argv)
    strict = args.strict or os.environ.get("EVIDENCE_STRICT") == "1"
    n, errors, warnings = run_gate(strict=strict)
    for w in warnings:
        print("WARNING", w)
    for e in errors:
        print("ERROR  ", e)
    print(f"evidence gate: {n} runs, {len(errors)} errors, {len(warnings)} warnings "
          f"({'strict' if strict else 'normal'}) -> {'FAILED' if errors else 'OK'}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
