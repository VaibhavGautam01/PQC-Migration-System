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