"""Stage 6c: labelled estimate for real-size keys.  Owner: Yatharth (written in Week 6, please review).

2n+3 logical qubits (the F2 formula), the Gidney-Ekera abstract circuit, and the published figure when we
have one. Everything here is an ESTIMATE; it never carries a time to break (schema rule). Measured circuit
sizes exist only for toy sizes (outputs/q4_metrics.json).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
try:
    from src import physical_estimates as pe
except ImportError:
    sys.path.insert(0, str(ROOT))
    from src import physical_estimates as pe


def estimate(modulus_bits):
    """Return the estimate block of the report for an RSA modulus of this size."""
    bits = int(modulus_bits)
    published = pe.published_estimate(bits)
    if published:
        text = (f"Gidney and Ekera 2021: about {published['physical_qubits']:,} physical qubits for RSA-{bits} "
                "(ESTIMATE, not measured)")
    else:
        text = (f"no published figure for {bits} bits in data/published_estimates.json; the logical counts "
                "below are ESTIMATES, not measurements")
    return {"modulus_bits": bits,
            "logical_qubits_2n_plus_3": 2 * bits + 3,
            "gidney_ekera_logical_qubits": round(pe.gidney_ekera_logical(bits)),
            "published": text,
            "measured_circuits": "outputs/q4_metrics.json holds measured circuit sizes for n = 4 to 8 only "
                                 "(Aer simulator / transpiler, toy size)"}
