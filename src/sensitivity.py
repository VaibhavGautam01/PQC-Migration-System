"""
sensitivity.py
--------------
Sensitivity study of the risk weights (plan: docs/sensitivity_plan.md).

  python src/sensitivity.py                 # writes data/sensitivity_results.json
  python src/sensitivity.py --draws 200     # quicker run

Four parts, all with a fixed seed:
  1. one at a time: every weight x0.8 and x1.2, its group re-scaled to sum to 1
  2. narrow random: every weight x U(0.8, 1.2), groups re-scaled   (decision rule)
  3. wide random:   every group a uniform Dirichlet draw           (stress test)
  4. assumption grid: X = 2, 5, 10 years and Z = 5, 10, 20 years with v0.1 weights

Cases scored: the four reference cases (plan section 4). The image and video
project scores need the layer map and are added later.
The score is a weighted score, not a probability.
"""
import argparse
import copy
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from risk_score import load_weights, score_layer  # noqa: E402
from weights_lock import fingerprint  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GROUPS = ("quantum_weights", "classical_weights", "overall_weights", "project_weights")
SEED = 42
DEFAULT_DRAWS = 1000
STABLE_FRACTION = 0.95

# Ordered from riskiest to safest: this is the reference order that must hold.
CASES = {
    "RSA-512 no padding": dict(category="shor_broken", construction="no_padding_deterministic",
                               exposure="keyless", modulus_bits=512),
    "RSA-1024 no padding": dict(category="shor_broken", construction="no_padding_deterministic",
                                exposure="keyless", modulus_bits=1024),
    "RSA-2048 OAEP": dict(category="shor_broken", construction="oaep",
                          exposure="keyless", modulus_bits=2048),
    "ML-KEM-768 + AES-256-GCM": dict(category="nist_pqc", construction="aead",
                                     exposure="keyless"),
}


def normalise(weights: dict) -> dict:
    """Re-scale every weight group so it sums to 1 (in place); returns weights."""
    for g in GROUPS:
        total = sum(weights[g].values())
        for k in weights[g]:
            weights[g][k] /= total
    return weights


def one_at_a_time(base, group, key, factor):
    w = copy.deepcopy(base)
    w[group][key] *= factor
    return normalise(w)


def narrow_draw(base, rng):
    w = copy.deepcopy(base)
    for g in GROUPS:
        for k in w[g]:
            w[g][k] *= rng.uniform(0.8, 1.2)
    return normalise(w)


def wide_draw(base, rng):
    w = copy.deepcopy(base)
    for g in GROUPS:
        draws = {k: rng.expovariate(1.0) for k in w[g]}   # normalised exponentials = Dirichlet(1,...,1)
        w[g] = draws
    return normalise(w)


def score_cases(weights, x_years=None, z_years=None) -> dict:
    return {n: score_layer(**kw, weights=weights, x_years=x_years, z_years=z_years)
            for n, kw in CASES.items()}


def overall(results: dict) -> dict:
    return {n: r["overall"] for n, r in results.items()}


def order_holds(scores: dict) -> bool:
    vals = [scores[n] for n in CASES]
    return all(a > b for a, b in zip(vals, vals[1:]))


def percentile(sorted_vals, p):
    if not sorted_vals:
        raise ValueError("no values")
    i = (len(sorted_vals) - 1) * p
    lo, hi = int(i), min(int(i) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (i - lo)


def summarise(draws: list) -> dict:
    """draws: list of {"overall": {case: value}, "bands": {case: band}}."""
    names = list(CASES)
    out = {"n": len(draws), "cases": {}}
    for n in names:
        vals = sorted(d["overall"][n] for d in draws)
        bands = {}
        for d in draws:
            bands[d["bands"][n]] = bands.get(d["bands"][n], 0) + 1
        out["cases"][n] = {"min": vals[0], "max": vals[-1], "mean": sum(vals) / len(vals),
                           "p05": percentile(vals, 0.05), "p95": percentile(vals, 0.95),
                           "bands": bands}
    out["order_fraction"] = sum(order_holds(d["overall"]) for d in draws) / len(draws)
    out["pair_fractions"] = {
        f"{a} > {b}": sum(d["overall"][a] > d["overall"][b] for d in draws) / len(draws)
        for a, b in zip(names, names[1:])}
    return out


def run(n_draws=DEFAULT_DRAWS, seed=SEED, weights=None) -> dict:
    base = copy.deepcopy(weights or load_weights())
    baseline = score_cases(base)

    oat = []
    for g in GROUPS:
        for k in base[g]:
            for f in (0.8, 1.2):
                res = score_cases(one_at_a_time(base, g, k, f))
                s = overall(res)
                oat.append({"group": g, "weight": k, "factor": f, "overall": s,
                            "order_holds": order_holds(s),
                            "max_change": max(abs(s[n] - overall(baseline)[n]) for n in CASES)})

    def draws_from(maker, rng):
        out = []
        for _ in range(n_draws):
            res = score_cases(maker(base, rng))
            out.append({"overall": overall(res), "bands": {n: r["band"] for n, r in res.items()}})
        return out

    narrow = summarise(draws_from(narrow_draw, random.Random(seed)))
    wide = summarise(draws_from(wide_draw, random.Random(seed + 1)))

    zs = base["f5_data_lifetime"]["z_scenarios"]
    grid = []
    for x in (2, 5, 10):
        for z in zs:
            res = score_cases(base, x_years=x, z_years=z)
            grid.append({"x_years": x, "z_years": z, "overall": overall(res),
                         "bands": {n: r["band"] for n, r in res.items()}})

    oat_all_hold = all(e["order_holds"] for e in oat)
    stable = narrow["order_fraction"] >= STABLE_FRACTION and oat_all_hold
    top = sorted(oat, key=lambda e: -e["max_change"])[:3]
    return {
        "weights_version": base["version"], "weights_sha256": fingerprint(),
        "seed": seed, "n_draws": n_draws, "stable_fraction_required": STABLE_FRACTION,
        "note": "Weighted score, not a probability. Reference cases only; formulas and published values, no simulator result.",
        "baseline": overall(baseline),
        "one_at_a_time": oat, "narrow_random": narrow, "wide_random": wide,
        "assumption_grid": grid,
        "decision": {"one_at_a_time_all_hold": oat_all_hold,
                     "narrow_order_fraction": narrow["order_fraction"],
                     "reference_order_stable": stable,
                     "largest_single_weight_effects": [
                         {k: e[k] for k in ("group", "weight", "factor", "max_change")} for e in top]},
    }


def print_report(r):
    print(f"Weights {r['weights_version']} (sha256 {r['weights_sha256'][:12]}...), seed {r['seed']}, "
          f"{r['n_draws']} draws per random run\n")
    print("Baseline:", {k: round(v, 1) for k, v in r["baseline"].items()})
    for title, key in (("Narrow random (x0.8..1.2)", "narrow_random"), ("Wide random (Dirichlet)", "wide_random")):
        s = r[key]
        print(f"\n{title}: reference order holds in {s['order_fraction']:.1%} of draws")
        print(f"  {'case':<28}{'min':>7}{'p05':>7}{'mean':>7}{'p95':>7}{'max':>7}  bands")
        for n, c in s["cases"].items():
            print(f"  {n:<28}{c['min']:>7.1f}{c['p05']:>7.1f}{c['mean']:>7.1f}{c['p95']:>7.1f}{c['max']:>7.1f}  {c['bands']}")
        for pair, f in s["pair_fractions"].items():
            print(f"  {pair}: {f:.1%}")
    d = r["decision"]
    print("\nOne at a time (x0.8 and x1.2): order holds in all cases:", d["one_at_a_time_all_hold"])
    print("Largest single-weight effects (max change in any case, points):")
    for e in d["largest_single_weight_effects"]:
        print(f"  {e['group']}.{e['weight']} x{e['factor']}: {e['max_change']:.1f}")
    print(f"\nDecision rule: stable if narrow order fraction >= {r['stable_fraction_required']:.0%} "
          f"and one-at-a-time all hold -> reference order stable: {d['reference_order_stable']}")
    print("\nAssumption grid (overall %):")
    print(f"  {'X':<4}{'Z':<4}" + "".join(f"{n[:14]:<16}" for n in CASES))
    for g in r["assumption_grid"]:
        print(f"  {g['x_years']:<4}{g['z_years']:<4}" + "".join(f"{g['overall'][n]:<7.1f}{g['bands'][n]:<9}" for n in CASES))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    ap.add_argument("--out", default=str(ROOT / "data" / "sensitivity_results.json"))
    a = ap.parse_args()
    res = run(a.draws)
    Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    print_report(res)
    print(f"\nWrote {a.out}")