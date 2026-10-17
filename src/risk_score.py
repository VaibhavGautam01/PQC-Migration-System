"""
risk_score.py
-------------
Factors F1 to F6 of the risk model (docs/risk_model.md, weights v0.1).

Every function is pure: same inputs, same output, no file or network access
except load_weights(). All numbers come from data/risk_weights.json.
A factor that does not apply to a layer returns None; the caller leaves it
out and re-scales the other weights (done in the formulas, Week 1 Day 3).

The score is a transparent weighted score, NOT a probability.
"""

import json
import math
from pathlib import Path

DEFAULT_WEIGHTS = Path(__file__).resolve().parent.parent / "data" / "risk_weights.json"


def load_weights(path=None) -> dict:
    """Load the weights file (default: data/risk_weights.json)."""
    p = Path(path) if path else DEFAULT_WEIGHTS
    return json.loads(p.read_text(encoding="utf-8"))


def _need_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")


def f1_quantum_exposure(category: str, effective_bits=None, weights=None) -> float:
    """F1: how exposed the algorithm is to quantum attack.

    category: 'shor_broken' (RSA, ECC, DSA, DH), 'nist_pqc' (ML-KEM, ML-DSA,
    SLH-DSA with AES-256) or 'symmetric' (AES, SHA; needs effective_bits,
    which is the strength AFTER Grover's halving, e.g. 128 for AES-256).
    """
    w = (weights or load_weights())["f1_quantum_exposure"]
    if category == "shor_broken":
        return float(w["shor_broken"])
    if category == "nist_pqc":
        return float(w["nist_pqc"])
    if category == "symmetric":
        if isinstance(effective_bits, bool) or not isinstance(effective_bits, (int, float)) or effective_bits < 0:
            raise ValueError("symmetric needs effective_bits >= 0")
        for band in w["grover_effective_bits"]:
            if effective_bits >= band["min_bits"]:
                return float(band["score"])
    raise ValueError(f"unknown F1 category {category!r}")


def f2_qubit_cost(modulus_bits, weights=None):
    """F2: 100 x (1 - (log10(q) - 2) / 3) with q = 2n + 3, limited to 20..100.

    Returns None when the layer is not Shor-broken (modulus_bits is None).
    """
    if modulus_bits is None:
        return None
    _need_int(modulus_bits, "modulus_bits")
    w = (weights or load_weights())["f2_qubit_cost"]
    q = 2 * modulus_bits + 3
    raw = 100.0 * (1.0 - (math.log10(q) - 2.0) / 3.0)
    return max(float(w["min"]), min(float(w["max"]), raw))


def f3_classical_key_weakness(modulus_bits, weights=None):
    """F3: weakness of the key size against ordinary computers.

    Up to 512 bits = 100, 513-1023 = 80, 1024-2047 = 50, 2048+ = 10.
    Returns None when the layer has no modulus (for example ML-KEM).
    """
    if modulus_bits is None:
        return None
    _need_int(modulus_bits, "modulus_bits")
    for band in (weights or load_weights())["f3_classical_key_weakness"]:
        if band["max_bits"] is None or modulus_bits <= band["max_bits"]:
            return float(band["score"])


def f4_construction_weakness(construction: str, weights=None) -> float:
    """F4: weakness of how the primitive is used (padding, AEAD, oracle)."""
    table = (weights or load_weights())["f4_construction_weakness"]
    if construction not in table:
        raise ValueError(f"unknown construction {construction!r}; use one of {sorted(table)}")
    return float(table[construction])


def f5_data_lifetime(x_years, y_years, z_years) -> float:
    """F5 (Mosca test): 100 x (X + Y) / Z, limited to 100.

    X = years the data must stay secret, Y = years to migrate,
    Z = years until a large quantum computer exists.
    """
    for name, v in (("x_years", x_years), ("y_years", y_years)):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
            raise ValueError(f"{name} must be >= 0")
    if isinstance(z_years, bool) or not isinstance(z_years, (int, float)) or z_years <= 0:
        raise ValueError("z_years must be > 0")
    return min(100.0, 100.0 * (x_years + y_years) / z_years)


def f5_effective(f5: float, f1: float) -> float:
    """Gated F5: F5_eff = F5 x F1 / 100 (only matters if the algorithm is quantum-vulnerable)."""
    return f5 * f1 / 100.0


def f6_exposure(kind: str, weights=None) -> float:
    """F6: can the ciphertext be extracted without a secret?

    kind: 'keyless' = 100, 'bypassable' (keyed, e.g. video header scan) = 90,
    'keyed' (keyed and not bypassable) = 30.
    """
    table = (weights or load_weights())["f6_exposure"]
    if kind not in table:
        raise ValueError(f"unknown exposure {kind!r}; use one of {sorted(table)}")
    return float(table[kind])


def f6_effective(f6: float, f3, f4: float) -> float:
    """Gated F6: F6_eff = F6 x max(F3, F4) / 100; if F3 does not apply, F4 alone."""
    weakness = f4 if f3 is None else max(f3, f4)
    return f6 * weakness / 100.0


# ---------------------------------------------------------------------
# Formulas (Week 1 Day 3)
# ---------------------------------------------------------------------
def _weighted(parts: dict, weights: dict) -> float:
    """Weighted mean of the factors that apply (None = left out, rest re-scaled)."""
    used = {k: v for k, v in parts.items() if v is not None}
    if not used:
        raise ValueError("no factor applies to this layer")
    total = sum(weights[k] for k in used)
    return sum(weights[k] * v for k, v in used.items()) / total


def quantum_risk(f1, f2, f5_eff, weights=None) -> float:
    """Quantum Risk % = 0.50 x F1 + 0.25 x F2 + 0.25 x F5_eff (F2 may be None)."""
    w = (weights or load_weights())["quantum_weights"]
    return _weighted({"f1": f1, "f2": f2, "f5": f5_eff}, w)


def classical_weakness(f3, f4, f6_eff, weights=None) -> float:
    """Classical Weakness % = 0.40 x F3 + 0.30 x F4 + 0.30 x F6_eff (F3 may be None)."""
    w = (weights or load_weights())["classical_weights"]
    return _weighted({"f3": f3, "f4": f4, "f6": f6_eff}, w)


def overall_risk(quantum: float, classical: float, weights=None) -> float:
    """Overall Risk % = 0.60 x Quantum + 0.40 x Classical."""
    w = (weights or load_weights())["overall_weights"]
    return w["quantum"] * quantum + w["classical"] * classical


def project_score(layer_scores, weights=None) -> float:
    """Weakest-link rule: 0.7 x (worst layer) + 0.3 x (average of layers)."""
    scores = list(layer_scores)
    if not scores:
        raise ValueError("need at least one layer score")
    w = (weights or load_weights())["project_weights"]
    return w["worst_layer"] * max(scores) + w["average"] * (sum(scores) / len(scores))


def band(score: float, weights=None) -> str:
    """Low (<25), Moderate (25-49), High (50-74), Critical (75+)."""
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 100:
        raise ValueError(f"score must be between 0 and 100, got {score!r}")
    for b in (weights or load_weights())["bands"]:
        if b["below"] is None or score < b["below"]:
            return b["name"]


def score_layer(category, construction, exposure, modulus_bits=None,
                effective_bits=None, x_years=None, y_years=None, z_years=None,
                weights=None) -> dict:
    """Score one layer and return every factor, the three percentages and the band.

    category: F1 category ('shor_broken', 'nist_pqc', 'symmetric').
    construction: F4 key (for example 'oaep'). exposure: F6 key.
    modulus_bits: RSA modulus size, or None when F2 and F3 do not apply
    (ML-KEM, SHA-256). x/y/z default to the values in the weights file.
    """
    w = weights or load_weights()
    d = w["f5_data_lifetime"]
    x = d["x_years"] if x_years is None else x_years
    y = d["y_years"] if y_years is None else y_years
    z = d["z_years"] if z_years is None else z_years

    f1 = f1_quantum_exposure(category, effective_bits, w)
    f2 = f2_qubit_cost(modulus_bits, w) if category == "shor_broken" else None
    f3 = f3_classical_key_weakness(modulus_bits, w)
    f4 = f4_construction_weakness(construction, w)
    f5_eff = f5_effective(f5_data_lifetime(x, y, z), f1)
    f6_eff = f6_effective(f6_exposure(exposure, w), f3, f4)

    q = quantum_risk(f1, f2, f5_eff, w)
    c = classical_weakness(f3, f4, f6_eff, w)
    o = overall_risk(q, c, w)
    return {"f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5_eff": f5_eff, "f6_eff": f6_eff,
            "quantum": q, "classical": c, "overall": o, "band": band(o, w)}