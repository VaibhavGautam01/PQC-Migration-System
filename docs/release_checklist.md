# Release checklist for v2.0.0 (Week 6 Day 4 and Day 5)

Run these in order. Do not tag until every line passes. Nothing here is automatic: each step needs a person.

## 1. Before the final merge

    git checkout main
    git pull
    git submodule update --init
    python run_tests.py
    python scripts/repo_check.py --release

repo_check --release must print "No problem found." It fails while any of these is true:

- a placeholder marker is still open in docs/ (the report chapters and the recordings list)
- a sir-confirmation marker is still open (docs/report/scope.md)
- the evidence gate fails in strict mode (the Q6 and Q7 records are not in the evidence format yet)
- a tracked file has uncommitted changes

## 2. The analyzer on the real pinned project

    python scripts/make_analyzer_testset.py
    python scripts/analyzer_testset_run.py --save-evidence
    python -m src.evidence_gate --strict

Every image must give its expected result. Commit data/quantum_runs.json and the new docs/circuits files. Quote the
accuracy table from this output only, and say it was measured on images from our own project.

## 3. Fresh clone

    powershell -ExecutionPolicy Bypass -File .\\scripts\\fresh_clone_check.ps1 -Branch main

All three exit codes must be 0. Then run the demo path of docs/rehearsal_script.md once more and add a line to
docs/REHEARSAL_LOG.md.

## 4. Numbers and claims

- README test count and weights version: python scripts/repo_check.py --count-tests
- Every number in docs/final_report.md and docs/report/scope.md against code output
- Every quantum result is labelled "Aer simulator, toy size"
- Nothing says RSA-1024 or RSA-2048 was broken

## 5. Merge and tag (Uday tags after Tarun's merge)

    git checkout main
    git pull
    git tag -a v2.0.0 -m "Phase 2: risk score, PQC advisor, Quantum Lab, Stego Analyzer"
    git push origin v2.0.0

## 6. After the tag

Delete the old branches that are merged, keep main, and write the date of the release in docs/REHEARSAL_LOG.md.
