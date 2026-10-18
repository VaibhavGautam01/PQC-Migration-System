"""
physical_estimates.py
---------------------
Physical-qubit figures for the risk report. EVERYTHING returned here is an
estimate and says so. Nothing is measured.

  * published_estimate(bits): the figure published by Gidney and Ekera (2021)
    for RSA-2048 under their stated assumptions. No figure is returned for other
    sizes, because the paper's number is for 2048 bits only.
  * gidney_ekera_logical(n): their abstract-circuit logical-qubit formula
    3n + 0.002 n lg n. This is a DIFFERENT circuit from the 2n+3 formula used by
    risk_score.py, so the two are shown side by side and never mixed.
  * illustrative_physical(logical, ratio): logical x ratio. The ratio is an
    assumption chosen for illustration, not a measured value.

The numbers in data/published_estimates.json were copied by hand and are marked
verified = false until checked against the paper.
"""
import json
import math
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "published_estimates.json"
ILLUSTRATIVE_RATIO = 1000


def _load(path=None) -> dict:
    return json.loads(Path(path or DATA).read_text(encoding="utf-8"))


def _need_bits(value, name="bits"):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")


def gidney_ekera_logical(n_bits: int) -> float:
    """Abstract-circuit logical qubits of Gidney and Ekera (2021): 3n + 0.002 n lg n."""
    _need_bits(n_bits)
    return 3 * n_bits + 0.002 * n_bits * math.log2(n_bits)


def published_estimate(rsa_bits: int, path=None):
    """Published physical-qubit estimate for this RSA size, or None if none is listed."""
    _need_bits(rsa_bits)
    src = _load(path)["sources"]["gidney_ekera_2021"]
    for e in src["estimates"]:
        if e["rsa_bits"] == rsa_bits:
            return {
                "kind": "published ESTIMATE (not measured)",
                "rsa_bits": rsa_bits,
                "physical_qubits": e["physical_qubits"],
                "runtime_hours": e["runtime_hours"],
                "assumptions": src["assumptions"],
                "citation": src["citation"],
                "verified_against_paper": src["verified"],
            }
    return None


def illustrative_physical(logical_qubits: int, ratio: int = ILLUSTRATIVE_RATIO) -> dict:
    """logical x ratio, labelled as an illustration."""
    _need_bits(logical_qubits)
    _need_bits(ratio, "ratio")
    return {"kind": "ILLUSTRATIVE ESTIMATE (assumed ratio, not measured)",
            "logical_qubits": logical_qubits, "ratio": ratio,
            "physical_qubits": logical_qubits * ratio}


def comparison_row(rsa_bits: int) -> dict:
    """One row for the report: our 2n+3 count, an illustration, and the published figure."""
    _need_bits(rsa_bits)
    q = 2 * rsa_bits + 3
    return {"rsa_bits": rsa_bits,
            "logical_2n_plus_3": q,
            "illustrative": illustrative_physical(q),
            "gidney_ekera_logical_abstract": round(gidney_ekera_logical(rsa_bits)),
            "published": published_estimate(rsa_bits)}