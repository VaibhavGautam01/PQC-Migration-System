"""
break_own_work.py - try to break our own work (Week 4 Day 3): nonce reuse, wrong keys,
tampering, and gaming the risk score by changing inputs instead of the real crypto.

Each check either:
  CONFIRMED SAFE     - the real code (hybrid.py, the attack scripts) already prevents this, and
                       this script demonstrates WHY by showing what would happen if it didn't.
  FOUND A GAP        - something the report must state as a limit, with a suggested fix.

Usage (from the project root, venv active):
  python extras/break_own_work.py
  python extras/break_own_work.py --json outputs/break_own_work.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Crypto.Cipher import AES                                # noqa: E402
from pqc_stego import hybrid                                 # noqa: E402
from src import risk_score as RS                             # noqa: E402


def record(findings, name, ok, detail):
    findings.append({"check": name, "status": "CONFIRMED SAFE" if ok else "FOUND A GAP",
                     "detail": detail})
    print(f"[{'SAFE' if ok else 'GAP '}] {name}\n        {detail}")


# ------------------------------------------------------------------ 1. nonce reuse
def check_nonce_reuse(findings):
    """Classic two-time-pad attack: IF the same (key, nonce) pair were ever reused for two
    different messages, XOR-ing the ciphertexts leaks the XOR of the two plaintexts, with no
    key needed at all. This checks (a) that this attack genuinely works when a nonce IS reused
    on purpose, and (b) that hybrid_encrypt() itself never reuses one in normal use."""
    key = hybrid.hkdf_sha256(b"fixed shared secret for this test", 32, info=hybrid.INFO)
    nonce = b"\x00" * 12                                      # deliberately reused, for the demo
    m1, m2 = b"ATTACK AT DAWN!!", b"RETREAT AT DUSK!"          # same length, for a clean XOR demo
    c1 = AES.new(key, AES.MODE_GCM, nonce=nonce).encrypt_and_digest(m1)[0]
    c2 = AES.new(key, AES.MODE_GCM, nonce=nonce).encrypt_and_digest(m2)[0]
    xor_cipher = bytes(a ^ b for a, b in zip(c1, c2))
    xor_plain = bytes(a ^ b for a, b in zip(m1, m2))
    leaked = xor_cipher == xor_plain                          # no key used anywhere above
    record(findings, "nonce reuse leaks the XOR of two plaintexts (no key needed)", not leaked,
          f"with a DELIBERATELY reused nonce, XOR(ciphertext1, ciphertext2) == XOR(plaintext1, "
          f"plaintext2): {leaked}. This is why GCM must never reuse a nonce under one key.")

    public_key, _ = hybrid.generate_keypair()
    nonces = set()
    for _ in range(2000):
        blob = hybrid.hybrid_encrypt(public_key, b"x")
        nonces.add(blob[hybrid.KEM_CT_LEN:hybrid.KEM_CT_LEN + hybrid.NONCE_LEN])
    record(findings, "hybrid_encrypt() itself never reuses a nonce (2000 calls, os.urandom)",
          len(nonces) == 2000,
          f"{len(nonces)} / 2000 nonces were distinct. hybrid_encrypt() draws a fresh "
          f"os.urandom(12) nonce every call, so this attack does not apply to the real code, "
          f"only to a hypothetical misuse (e.g. a fixed or counter-reset nonce).")


# ------------------------------------------------------------------ 2. gaming the risk score
def check_score_gaming(findings):
    """The risk engine trusts the CATEGORY and EXPOSURE labels it is given. Can a wrong or
    optimistic label make a genuinely weak layer score artificially low, without changing the
    actual crypto at all? This is a model-honesty check, not a crypto attack."""
    w = RS.load_weights()

    honest = RS.f1_quantum_exposure("shor_broken", weights=w)               # RSA, correctly labelled
    mislabelled = RS.f1_quantum_exposure("nist_pqc", weights=w)              # same RSA, WRONGLY labelled
    record(findings, "mislabelling an RSA layer as 'nist_pqc' changes F1",
          False, f"F1 = {honest} when correctly labelled 'shor_broken', but F1 = {mislabelled} "
          f"if someone (by mistake or on purpose) passes category='nist_pqc' for the same RSA "
          f"layer - a {honest - mislabelled:.0f}-point drop with NO change to the real algorithm. "
          f"The scanner/mapper decide the category from the detected algorithm name, never from "
          f"free text, so this requires either a scanner bug or someone hand-editing an "
          f"intermediate file. Limit to state in the report: the model assumes honest category "
          f"and exposure labels; it does not independently re-verify them from the raw code.")

    honest_f6 = RS.f6_exposure("keyless", w)
    claimed_f6 = RS.f6_exposure("keyed", w)
    record(findings, "claiming 'keyed' exposure for an actually-keyless layer changes F6",
          False, f"F6 = {honest_f6} for the real (keyless LSB) exposure, but F6 = {claimed_f6} if "
          f"'keyed' is claimed instead - a {honest_f6 - claimed_f6:.0f}-point drop. The exposure "
          f"label for each layer is set from the attack evidence (docs/attack_evidence*.md), not "
          f"computed automatically, so a stale or optimistic evidence doc could understate risk. "
          f"Recommendation: cross-check every exposure label against a current, dated attack run "
          f"before each score refresh.")

    import json as _json
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "weights.json"
        tampered = _json.loads(RS.DEFAULT_WEIGHTS.read_text())
        tampered["f1_quantum_exposure"]["shor_broken"] = 1          # zero out the worst factor
        bad.write_text(_json.dumps(tampered))
        zeroed = RS.f1_quantum_exposure("shor_broken", weights=RS.load_weights(bad))
        record(findings, "editing data/risk_weights.json directly can zero out F1",
              False, f"with the committed weights F1=100 for Shor-broken algorithms; with a "
              f"one-line edit to risk_weights.json, F1={zeroed} for the SAME layer. The weights "
              f"file has no integrity check (hash, signature, or CI diff gate). Recommendation: "
              f"freeze weights v1.0 in CI (fail the build if risk_weights.json changes without "
              f"a reviewed pull request), which the plan's Week 2 Day 5 step already intends.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="also write the results to this JSON file")
    args = ap.parse_args()
    findings = []
    print("=== 1. Nonce reuse ===")
    check_nonce_reuse(findings)
    print("\n=== 2. Gaming the risk score ===")
    check_score_gaming(findings)
    gaps = [f for f in findings if f["status"] == "FOUND A GAP"]
    print(f"\n{len(findings) - len(gaps)} confirmed safe, {len(gaps)} gap(s) to document in the report.")
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"findings": findings}, indent=2) + "\n", encoding="utf-8")
        print("wrote", out)


if __name__ == "__main__":
    main()
