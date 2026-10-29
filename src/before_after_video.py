"""
before_after_video.py
---------------------
Before and after table for the VIDEO project, scored by the SAME engine as the image
project (risk_score.score_layer; same weights file).

  before (as found in Secure-Video-Steganography):
    L1  textbook RSA, no padding, deterministic, header scan finds the frames
    L2  SHA-256 of a passphrase picks the frames (frames 0 to 255 only)
    L3  CRC32 integrity (not cryptographic)
  after (the migration recommended by the advisor):
    L1  ML-KEM-768 + HKDF + AES-256-GCM
    L2  256-bit random key with HKDF or HMAC-SHA256 picking frames across the whole video
    L3  the AES-GCM tag replaces CRC32

  python src/before_after_video.py                       # RSA sizes 1024, 2048, 3072
  python src/before_after_video.py --bits 2048           # one size
  python src/before_after_video.py --draws 200 --out outputs/before_after_video.json

Open model question (not guessed here): the engine has no factor for how strong or how widely
used a frame-selection key is. The L2 fix (random 256-bit key, all frames) therefore cannot be
credited. L2 keeps its "before" value in the "after" project score, so the drop shown is a
lower bound. The header scan can still find the frames, so exposure stays "bypassable" in
every layer: migration fixes the encryption and integrity layers, not the hiding layer.

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
DEFAULT_BITS = (1024, 2048, 3072)   # function default 1024; the UI offers 1024, 2048, 3072

L2_BEFORE = dict(category="symmetric", effective_bits=128,
                 construction="deterministic_or_oracle", exposure="bypassable")
L3_BEFORE = dict(category="none", construction="deterministic_or_oracle", exposure="bypassable")
L1_AFTER = dict(category="nist_pqc", construction="aead", exposure="bypassable")
L3_AFTER = dict(category="symmetric", effective_bits=128, construction="aead", exposure="bypassable")

WHAT = {"L1": ("RSA, no padding", "ML-KEM-768 + AES-256-GCM"),
        "L2": ("SHA-256 of a passphrase", "256-bit random key (not credited, see docstring)"),
        "L3": ("CRC32", "AES-GCM tag")}


def l1_before(bits: int) -> dict:
    return dict(category="shor_broken", construction="no_padding_deterministic",
                exposure="bypassable", modulus_bits=bits)


def compare(bits: int, weights=None, x_years=None, z_years=None) -> dict:
    kw = dict(weights=weights, x_years=x_years, z_years=z_years)
    b1, a1 = score_layer(**l1_before(bits), **kw), score_layer(**L1_AFTER, **kw)
    b2 = score_layer(**L2_BEFORE, **kw)
    b3, a3 = score_layer(**L3_BEFORE, **kw), score_layer(**L3_AFTER, **kw)
    pb = project_score([b1["overall"], b2["overall"], b3["overall"]], weights)
    pa = project_score([a1["overall"], b2["overall"], a3["overall"]], weights)   # L2 not credited
    return {"modulus_bits": bits,
            "layers": {"L1": {"before": b1, "after": a1},
                       "L2": {"before": b2, "after": None},
                       "L3": {"before": b3, "after": a3}},
            "project_before": pb, "project_after": pa, "project_drop": pb - pa}


def sensitivity(bits: int, n_draws: int, seed: int = SEED) -> dict:
    base = load_weights()
    out = {}
    for name, maker, s in (("narrow_random", narrow_draw, seed), ("wide_random", wide_draw, seed + 1)):
        rng = random.Random(s)
        pbs, pas, drops = [], [], []
        for _ in range(n_draws):
            r = compare(bits, weights=maker(copy.deepcopy(base), rng))
            pbs.append(r["project_before"])
            pas.append(r["project_after"])
            drops.append(r["project_drop"])
        out[name] = {"after_below_before_fraction": sum(d > 0 for d in drops) / n_draws,
                     "before_min": min(pbs), "before_max": max(pbs),
                     "after_min": min(pas), "after_max": max(pas), "smallest_drop": min(drops)}
    return out


def run(bits_list=DEFAULT_BITS, n_draws=1000) -> dict:
    base = load_weights()
    zs = base["f5_data_lifetime"]["z_scenarios"]
    rows = []
    for bits in bits_list:
        r = compare(bits)
        r["z_scenarios"] = {z: {"before": compare(bits, z_years=z)["project_before"],
                                "after": compare(bits, z_years=z)["project_after"]} for z in zs}
        r["sensitivity"] = sensitivity(bits, n_draws)
        rows.append(r)
    return {"weights_version": base["version"], "weights_sha256": fingerprint(),
            "project": "video", "layers": ["L1", "L2", "L3"], "seed": SEED, "n_draws": n_draws,
            "label": "formulas and weights only; no simulator result; weighted score, not a probability",
            "not_credited": "L2 frame-selection fix: the engine has no factor for key entropy or frame coverage",
            "exposure_note": "header scan still finds the frames, so exposure stays bypassable in every layer",
            "rows": rows}


def print_report(res):
    print(f"Video project, layers L1 to L3. Weights {res['weights_version']}.\n")
    print(f"{'RSA bits':<10}{'Layer':<7}{'':<8}{'Quantum':>9}{'Classical':>11}{'Overall':>9}  Band")
    for r in res["rows"]:
        for layer, v in r["layers"].items():
            for tag in ("before", "after"):
                s = v[tag]
                if s is None:
                    print(f"{'':<10}{layer:<7}{tag:<8}{'not credited':>29}  {WHAT[layer][1]}")
                    continue
                what = WHAT[layer][0] if tag == "before" else WHAT[layer][1]
                print(f"{r['modulus_bits'] if (layer == 'L1' and tag == 'before') else '':<10}{layer:<7}{tag:<8}"
                      f"{s['quantum']:>9.1f}{s['classical']:>11.1f}{s['overall']:>9.1f}  {s['band']:<9}{what}")
        print(f"{'':<10}project score {r['project_before']:.1f} -> {r['project_after']:.1f} "
              f"(drop {r['project_drop']:.1f}); Z scenarios (before -> after): "
              + ", ".join(f"Z={z}: {v['before']:.1f} -> {v['after']:.1f}" for z, v in r["z_scenarios"].items()))
        for k, v in r["sensitivity"].items():
            print(f"{'':<10}{k}: after < before in {v['after_below_before_fraction']:.1%} of draws; "
                  f"after {v['after_min']:.1f} to {v['after_max']:.1f}, before {v['before_min']:.1f} to {v['before_max']:.1f}")
    print("\nNot credited: " + res["not_credited"])
    print("Note: " + res["exposure_note"])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bits", type=int, nargs="+", default=list(DEFAULT_BITS))
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--out", default=str(ROOT / "outputs" / "before_after_video.json"))
    a = ap.parse_args()
    res = run(a.bits, a.draws)
    Path(a.out).parent.mkdir(exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print_report(res)
    print(f"\nWrote {a.out}")
