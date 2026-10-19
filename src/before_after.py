"""
before_after.py
---------------
Before and after table for the image project, scored by the SAME engine
(risk_score.score_layer, weights v0.1).

  before: textbook RSA, no padding, deterministic, keyless embedding
  after : ML-KEM-768 + AES-256-GCM (HKDF between them), keyless embedding unchanged

  python src/before_after.py                       # sizes 256 and 512
  python src/before_after.py --bits 256            # one size
  python src/before_after.py --draws 200 --out outputs/before_after_image.json

Scored layer: L1 (message encryption). The integrity layer is covered by the
AES-GCM tag in the "after" setup, and the optional ML-DSA signature (L5) is
scored in Week 3. Layers with no cryptography are not scored (open team
decision, see docs/risk_review_week1.md). The hiding layer is measured by
steganalysis, not here.

The score is a weighted score, not a probability. Formulas only; no simulator.
"""
import argparse
import copy
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from risk_score import load_weights, project_score, score_layer  # noqa: E402
from sensitivity import SEED, narrow_draw, wide_draw  # noqa: E402
from weights_lock import fingerprint  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BITS = (256, 512)
AFTER = dict(category="nist_pqc", construction="aead", exposure="keyless")


def before_config(bits: int) -> dict:
    """Textbook RSA of the given modulus size, keyless embedding."""
    return dict(category="shor_broken", construction="no_padding_deterministic",
                exposure="keyless", modulus_bits=bits)


def compare(bits: int, weights=None, x_years=None, z_years=None) -> dict:
    kw = dict(weights=weights, x_years=x_years, z_years=z_years)
    b = score_layer(**before_config(bits), **kw)
    a = score_layer(**AFTER, **kw)
    return {"modulus_bits": bits, "before": b, "after": a,
            "drop": b["overall"] - a["overall"],
            "project_before": project_score([b["overall"]], weights),
            "project_after": project_score([a["overall"]], weights)}


def remaining_floor(after: dict) -> list:
    """The factors that keep the 'after' score above zero, with their values."""
    rows = [("F1 quantum exposure (NIST PQC level)", after["f1"]),
            ("F4 construction (AES-GCM, not zero by design)", after["f4"]),
            ("F5_eff data lifetime, gated by F1", after["f5_eff"]),
            ("F6_eff exposure, gated by F4", after["f6_eff"])]
    return [{"factor": n, "value": round(v, 2)} for n, v in rows]


def sensitivity(bits: int, n_draws: int, seed: int = SEED) -> dict:
    base = load_weights()
    out = {}
    for name, maker, s in (("narrow_random", narrow_draw, seed), ("wide_random", wide_draw, seed + 1)):
        rng = random.Random(s)
        befores, afters, drops = [], [], []
        for _ in range(n_draws):
            r = compare(bits, weights=maker(copy.deepcopy(base), rng))
            befores.append(r["before"]["overall"])
            afters.append(r["after"]["overall"])
            drops.append(r["drop"])
        out[name] = {"after_below_before_fraction": sum(d > 0 for d in drops) / n_draws,
                     "before_min": min(befores), "before_max": max(befores),
                     "after_min": min(afters), "after_max": max(afters),
                     "smallest_drop": min(drops)}
    return out


def run(bits_list=DEFAULT_BITS, n_draws=1000) -> dict:
    base = load_weights()
    zs = base["f5_data_lifetime"]["z_scenarios"]
    rows = []
    for bits in bits_list:
        r = compare(bits)
        r["z_scenarios"] = {z: {"before": compare(bits, z_years=z)["before"]["overall"],
                                "after": compare(bits, z_years=z)["after"]["overall"]} for z in zs}
        r["sensitivity"] = sensitivity(bits, n_draws)
        rows.append(r)
    return {"weights_version": base["version"], "weights_sha256": fingerprint(),
            "project": "image", "layer": "L1 message encryption", "seed": SEED, "n_draws": n_draws,
            "label": "formulas and weights only; no simulator result; weighted score, not a probability",
            "after_floor": remaining_floor(rows[0]["after"]), "rows": rows}


def print_report(res):
    print(f"Image project, L1 message encryption. Weights {res['weights_version']}.\n")
    print(f"{'RSA bits':<10}{'':<8}{'Quantum':>9}{'Classical':>11}{'Overall':>9}  Band")
    for r in res["rows"]:
        for tag in ("before", "after"):
            s = r[tag]
            label = f"{r['modulus_bits']}" if tag == "before" else ""
            what = "RSA, no padding" if tag == "before" else "ML-KEM-768 + AES-256-GCM"
            print(f"{label:<10}{tag:<8}{s['quantum']:>9.1f}{s['classical']:>11.1f}{s['overall']:>9.1f}  {s['band']:<9}{what}")
        print(f"{'':<10}drop {r['drop']:.1f} points; Z scenarios (before -> after): "
              + ", ".join(f"Z={z}: {v['before']:.1f} -> {v['after']:.1f}" for z, v in r["z_scenarios"].items()))
        for k, v in r["sensitivity"].items():
            print(f"{'':<10}{k}: after < before in {v['after_below_before_fraction']:.1%} of draws; "
                  f"after {v['after_min']:.1f} to {v['after_max']:.1f}, before {v['before_min']:.1f} to {v['before_max']:.1f}")
    print("\nWhy the 'after' score is not zero:")
    for f in res["after_floor"]:
        print(f"  {f['factor']}: {f['value']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bits", type=int, nargs="+", default=list(DEFAULT_BITS))
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--out", default=str(ROOT / "outputs" / "before_after_image.json"))
    a = ap.parse_args()
    res = run(a.bits, a.draws)
    Path(a.out).parent.mkdir(exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print_report(res)
    print(f"\nWrote {a.out}")