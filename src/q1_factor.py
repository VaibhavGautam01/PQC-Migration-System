"""
q1_factor.py - factor N with the Q1 quantum circuit (used by the toy stego attack).

WHAT IT DOES
------------
quantum_factor(N) is the function that REPLACES the classical factor_n(N) in
extras/stego_attack_toy.py. It follows Shor's algorithm exactly:

  1. pick a base a with 1 < a < N
  2. if gcd(a, N) > 1 you were lucky and already have a factor (part of Shor's algorithm)
  3. otherwise run the Q1 phase-estimation circuit (Aer simulator) for that a
  4. post-process ONLY the measured counts: continued fractions -> period r -> gcd -> factors
  5. if this a fails (odd period, or a**(r/2) = -1 mod N), try the next a

The attacker's only input is the PUBLIC modulus N. The factors come from the
measured circuit output, never from sympy or a classical order search (rules 2 and 3).

Aer simulator, toy size. The circuit uses dense unitaries (see q1_shor_pe.py), so
this does not scale to real key sizes - it shows that the break pipeline works
end to end when the factoring step is a real quantum circuit.
"""
from math import gcd

from src import shor_post as SP

STEGO_GROUP = "shor_toy_stego_attack"       # evidence group for rule 6 (change the question)


def candidate_bases(N: int):
    """Bases to try, in a fixed order, so a run is reproducible: 2, 3, 4, ... below N."""
    return range(2, N)


def quantum_factor(N: int, shots: int = 2048, max_tries: int = 6, runner=None) -> dict:
    """Factor N using the Q1 circuit. Returns a dict:

        {"factors": (p, q) or None, "a": base used, "period": measured period,
         "method": "lucky gcd" | "quantum circuit", "attempts": [...], "records": [...]}

    runner: function (a, N, shots) -> (evidence_record, circuit). Default is
            q1_run.run_q1 (real circuit on Aer). Tests inject a fake runner.
    records: the evidence record of every circuit run, ready for --save-evidence.
    """
    if runner is None:
        from src.q1_run import run_q1                       # imported late: needs qiskit
        runner = lambda a, n, s: run_q1(a, n, s, cross_check=False)  # noqa: E731

    attempts, records = [], []
    for a in candidate_bases(N):
        if len(attempts) >= max_tries:
            break
        g = gcd(a, N)
        if g != 1:                                          # lucky: a shares a factor with N
            attempts.append({"a": a, "outcome": f"gcd(a, N) = {g}"})
            return {"factors": tuple(sorted((g, N // g))), "a": a, "period": None,
                    "method": "lucky gcd", "attempts": attempts, "records": records}
        record, _ = runner(a, N, shots)
        record["question_group"] = STEGO_GROUP
        records.append(record)
        found = SP.analyse_counts(record["counts"], record["inputs"]["counting_qubits"], a, N)
        attempts.append({"a": a, "period": found["period"], "factors": found["factors"]})
        if found["factors"]:
            return {"factors": tuple(found["factors"]), "a": a, "period": found["period"],
                    "method": "quantum circuit", "attempts": attempts, "records": records}
    return {"factors": None, "a": None, "period": None, "method": "failed",
            "attempts": attempts, "records": records}
