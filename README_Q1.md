# Q1 Shor phase estimation - files for Vaibhav

Copy into the team repo keeping the folder layout:

    src/shor_post.py
    src/q1_shor_pe.py
    src/q1_run.py
    tests/test_q1_shor_pe.py

Then, from the repo root with the venv active:

    python -m unittest tests.test_q1_shor_pe -v
    python -m src.quantum_guard
    python -m src.q1_run --N 15 --a 7
    python -m src.q1_run --suite --save
    python -m src.evidence_gate --strict

All quantum results: Aer simulator, toy size.
Qiskit calls were not executed when these files were written (qiskit was not installed
in the authoring sandbox); the circuit maths was checked with numpy only.
