"""
risk_review.py
--------------
Week 1 Day 4 review helper for the risk model (docs/risk_model.md, v0.1).

  python src/risk_review.py
      Re-checks the worked values, the reference order, monotonic behaviour and
      the F5 / F6 gating, and prints the scores for Z = 5, 10, 20.

  python src/risk_review.py --category shor_broken --construction no_padding_deterministic \
         --exposure bypassable --bits 1024
      Prints the expected factors and percentages for ONE layer, so you can
      compare them with a row of outputs/risk_scores.json.

Exit code is 1 if any check fails. Does not change any file.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from risk_score import (f5_data_lifetime, f5_effective, f6_effective,  # noqa: E402
                        f6_exposure, load_weights, score_layer)

WORKED = [
    ("RSA-512 no padding", dict(category="shor_broken", construction="no_padding_deterministic",
                                exposure="keyless", modulus_bits=512), (84.1, 100.0, 90.4)),
    ("RSA-1024 no padding", dict(category="shor_broken", construction="no_padding_deterministic",
                                 exposure="keyless", modulus_bits=1024), (81.6, 80.0, 80.9)),
    ("RSA-2048 OAEP", dict(category="shor_broken", construction="oaep",
                           exposure="keyless", modulus_bits=2048), (79.1, 8.5, 50.8)),
    ("ML-KEM-768 + AES-256-GCM", dict(category="nist_pqc", construction="aead",
                                      exposure="keyless"), (4.5, 5.0, 4.7)),
]

failures = []


def check(ok, text):
    print(("  [PASS] " if ok else "  [FAIL] ") + text)
    if not ok:
        failures.append(text)


def run_review():
    print("1. Worked values (plan section 4)")
    results = []
    for name, kw, (q, c, o) in WORKED:
        r = score_layer(**kw)
        results.append(r["overall"])
        check(round(r["quantum"], 1) == q and round(r["classical"], 1) == c and round(r["overall"], 1) == o,
              f"{name}: got {r['quantum']:.1f} / {r['classical']:.1f} / {r['overall']:.1f}, expected {q} / {c} / {o}")
    check(results == sorted(results, reverse=True), "reference order is strictly decreasing")

    print("\n2. F5 gating: F5_eff = F5 x F1 / 100")
    f5 = f5_data_lifetime(5, 2, 10)
    for label, f1 in (("Shor-broken (F1=100)", 100), ("Grover 128 bits (F1=10)", 10), ("NIST PQC (F1=5)", 5)):
        eff = f5_effective(f5, f1)
        print(f"     {label}: F5 = {f5:.0f}, F5_eff = {eff:.1f}")
    check(abs(f5_effective(f5, 5) - 0.05 * f5) < 1e-9, "at the NIST PQC level F5_eff is 5 percent of F5")
    check(f5_effective(f5, 0) == 0, "F5_eff is 0 when F1 is 0")

    print("\n3. F6 gating: F6_eff = F6 x max(F3, F4) / 100")
    f6 = f6_exposure("keyless")
    check(f6_effective(f6, 100, 100) == 100, "weak key and no padding: full exposure counts")
    check(f6_effective(f6, 10, 5) == 10, "RSA-2048 + OAEP: exposure follows the layer's weakness (10)")
    check(f6_effective(f6, None, 5) == 5, "no F3 (ML-KEM): F4 alone (5)")
    check(f6_effective(f6_exposure("keyless"), None, 5) <= f6_effective(f6_exposure("keyless"), None, 80),
          "a stronger construction never gets more exposure weight")

    print("\n4. Monotonic behaviour")
    bits = (256, 512, 768, 1024, 2048, 3072, 4096)
    s = [score_layer("shor_broken", "no_padding_deterministic", "keyless", b)["overall"] for b in bits]
    check(s == sorted(s, reverse=True), "bigger key never raises the score")
    order = ["no_padding_deterministic", "deterministic_or_oracle", "padding_without_aead", "oaep"]
    s = [score_layer("shor_broken", c, "keyless", 2048)["overall"] for c in order]
    check(s == sorted(s, reverse=True), "added padding never raises the score")
    s = [score_layer("shor_broken", "oaep", "keyless", 2048, z_years=z)["quantum"] for z in (5, 10, 20)]
    check(s == sorted(s, reverse=True), "a later quantum computer (bigger Z) never raises the quantum risk")

    print("\n5. Z scenarios (X=5, Y=2), overall % per case")
    zs = load_weights()["f5_data_lifetime"]["z_scenarios"]
    print("     " + f"{'case':<28}" + "".join(f"Z={z:<8}" for z in zs))
    for name, kw, _ in WORKED:
        row = [score_layer(**kw, z_years=z)["overall"] for z in zs]
        print("     " + f"{name:<28}" + "".join(f"{v:<10.1f}" for v in row))
    return not failures


def one_layer(a):
    r = score_layer(a.category, a.construction, a.exposure, a.bits, a.effective_bits,
                    a.x, a.y, a.z)
    for k, v in r.items():
        print(f"  {k:<10} {v if isinstance(v, str) or v is None else round(v, 2)}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--category")
    p.add_argument("--construction")
    p.add_argument("--exposure")
    p.add_argument("--bits", type=int)
    p.add_argument("--effective-bits", type=int, dest="effective_bits")
    p.add_argument("--x", type=float)
    p.add_argument("--y", type=float)
    p.add_argument("--z", type=float)
    args = p.parse_args()
    if args.category:
        one_layer(args)
    else:
        ok = run_review()
        print("\nAll checks passed." if ok else f"\n{len(failures)} check(s) FAILED.")
        sys.exit(0 if ok else 1)