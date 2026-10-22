"""Compare sizes in data/pqc_recommendations.json with what the libraries and our modules produce.
Exit code 1 on any mismatch. Usage: python scripts/check_sizes.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from dilithium_py.ml_dsa import ML_DSA_65
from kyber_py.ml_kem import ML_KEM_768

import pqc_advisor
from pqc_stego import hybrid, signing


def check():
    recs = pqc_advisor.load_recommendations()
    ek, dk = ML_KEM_768.keygen()
    _, ct = ML_KEM_768.encaps(ek)
    pk, sk = ML_DSA_65.keygen()
    sig = ML_DSA_65.sign(sk, b"size check")
    rows = [
        ("L1 public_key", recs["L1"]["sizes_bytes"]["public_key"], len(ek)),
        ("L1 ciphertext", recs["L1"]["sizes_bytes"]["ciphertext"], len(ct)),
        ("L3 nonce", recs["L3"]["sizes_bytes"]["nonce"], hybrid.NONCE_LEN),
        ("L3 tag", recs["L3"]["sizes_bytes"]["tag"], hybrid.TAG_LEN),
        ("L5 public_key", recs["L5"]["sizes_bytes"]["public_key"], len(pk)),
        ("L5 signature", recs["L5"]["sizes_bytes"]["signature"], len(sig)),
        ("hybrid overhead", 1116, hybrid.OVERHEAD),
        ("hybrid overhead from parts", len(ct) + hybrid.NONCE_LEN + hybrid.TAG_LEN, hybrid.OVERHEAD),
        ("signing.SIG_LEN", len(sig), signing.SIG_LEN),
        ("signing.PUBLIC_KEY_LEN", len(pk), signing.PUBLIC_KEY_LEN),
    ]
    return [(name, doc, code, doc == code) for name, doc, code in rows]


if __name__ == "__main__":
    results = check()
    print("| Item | Documented | From code | Match |")
    print("|---|---|---|---|")
    for name, doc, code, ok in results:
        print(f"| {name} | {doc} | {code} | {'yes' if ok else 'NO'} |")
    sys.exit(0 if all(r[3] for r in results) else 1)