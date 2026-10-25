"""Stage 6a: real Shor circuit for a toy-size modulus.  Owner: Yatharth (written in Week 6, please review).

Rules of the plan (Section 9, "Analyzer rule"):
  * The modulus comes from the public key given with the image. It goes to the Q2 gate-level circuit
    (src/q2_shor.py through src/shor_run.run_shor). It is NEVER factored with ordinary code first.
  * Classical code does only what the algorithm defines: choose a base a with gcd(a, N) = 1, post-process
    the measured outcomes (done inside run_shor), and then use the factors the CIRCUIT measured to rebuild
    the private exponent and decrypt.
  * Every run is saved as an evidence record (rule 4), whether or not it found factors.
  * The static guard (src/quantum_guard.py) scans this whole file.
Live runs write their records to an untracked session file; scripts/analyzer_testset_run.py --save-evidence
writes them to data/quantum_runs.json instead.
"""
import sys
from math import gcd
from pathlib import Path

from . import toyformat

ROOT = Path(__file__).resolve().parent.parent
SESSION_RUNS = ROOT / "outputs" / "tmp_quantum_runs_analyzer.json"
SESSION_DIAGRAMS = ROOT / "outputs" / "tmp_analyzer_diagrams"
LABEL = "Aer simulator, toy size"
SHOTS = 20
MAX_BASES = 6


def _shor_run():
    sys.path.insert(0, str(ROOT / "src"))
    import shor_run
    return shor_run


def _bases(n):
    """Bases a = 2, 3, ... that are coprime to n (the first step of Shor's algorithm)."""
    out = []
    for a in range(2, n):
        if gcd(a, n) == 1:
            out.append(a)
        if len(out) == MAX_BASES:
            break
    return out


def attack_toy(public_key, blob, record_path=None, diagram_dir=None, shor=None):
    """Factor the public modulus with the Q2 circuit, rebuild the private exponent and decrypt the blob.

    public_key: {"n": int, "e": int}. blob: the hex string hidden in the image, as ASCII bytes.
    shor: test hook, a function (a, N, shots) -> (record, circuit); defaults to the real Q2 run.
    Returns {"state": "broken_toy", "run_id", "label", "recovered_message", "factors", "evidence", ...}.
    Raises RuntimeError if no base gave factors (the pipeline then stops there and says so).
    """
    n, e = int(public_key["n"]), int(public_key["e"])
    blocks = toyformat.split_blocks(blob.decode("ascii"), n)
    if blocks is None:
        raise ValueError("the blob does not fit this modulus (wrong public key?)")
    sr = _shor_run()
    run = shor or sr.run_shor
    path = Path(record_path) if record_path else SESSION_RUNS
    diagrams = Path(diagram_dir) if diagram_dir else SESSION_DIAGRAMS
    tried = []
    for a in _bases(n):
        record, circuit = run(a, n, SHOTS)
        sr.save_record(record, circuit, path, diagrams,
                       notes="Stego Analyzer run; chi-square and a second-method cross-check are not done")
        tried.append({"a": a, "run_id": record["id"], "success_rate": record["success_rate"]})
        if not record["factors_found"]:
            continue
        top = max(record["factors_found"].items(), key=lambda kv: kv[1])[0]
        p, q = (int(x) for x in top.split("x"))
        d = pow(e, -1, (p - 1) * (q - 1))
        text = toyformat.decode([pow(c, d, n) for c in blocks], n)
        rel = path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        return {"state": "broken_toy", "run_id": record["id"], "label": LABEL, "recovered_message": text,
                "factors": [p, q], "base_a": a, "runs_tried": tried,
                "evidence": {"record_file": rel, "run_id": record["id"]}}
    raise RuntimeError(f"Shor did not find factors of {n} with {len(tried)} bases ({tried})")
