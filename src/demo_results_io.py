"""
demo_results_io.py - write Q1 batch results into data/demo_results.json WITHOUT breaking the dashboard.

WHY THIS FILE EXISTS
--------------------
data/demo_results.json already has a fixed format that the dashboard reads
(src/build_dashboard.py load_demo, src/live_dashboard.py save_demo):

    {"_readme": "...", "environment": "...",
     "cases": [{"N": 15, "expected_factors": [3, 5], "runs": 1024, "successes": 509,
                "backend": "simulator", "notes": "..."}],
     "recordings": []}

`runs` and `successes` MUST be whole numbers (successes <= runs); anything else makes the
dashboard raise ValueError. So the Q1 batch script keeps its detailed results (per-repeat seeds,
chi-square, top outcomes) in data/q1_batch_results.json and only merges ONE summary line per N
into demo_results.json, in exactly this format. Existing keys, the other cases and the
recordings list are preserved, and a case with the same N is replaced (like save_demo does).

No qiskit is needed here, so these functions are tested on any machine.
"""
import json
from pathlib import Path

README = ("Real simulator runs. Copy of the format in data/demo_results.template.json. "
          "Do not invent numbers.")


def pick_dashboard_cases(cases: list) -> list:
    """One case per N: the first one given. (The dashboard table has one row per N.)"""
    seen, picked = set(), []
    for case in cases:
        if case["N"] not in seen:
            seen.add(case["N"])
            picked.append(case)
    return picked


def build_entry(case: dict, seed_start: int, versions: str) -> dict:
    """One dashboard row from one batch case.

    runs      = total shots over all repeats
    successes = shots whose single measured outcome already gave the factors
    expected_factors = the factors the measurements produced most often (not computed classically)
    """
    top = max(case["factors_found_in_repeats"].items(), key=lambda kv: kv[1])[0]
    expected = [] if top == "none" else [int(x) for x in top.split("x")]
    runs = int(case["repeats"]) * int(case["shots_per_repeat"])
    successes = int(sum(r["shots_with_factors"] for r in case["runs"]))
    return {"N": case["N"], "expected_factors": expected, "runs": runs, "successes": successes,
            "backend": "simulator",
            "notes": (f"saved by src/q1_demo_batch.py: a={case['a']}, {case['repeats']} repeats x "
                      f"{case['shots_per_repeat']} shots, seeds {seed_start}..{seed_start + case['repeats'] - 1}, "
                      f"{versions}; Aer simulator, toy size")}


def merge_into_demo_results(path, cases: list, seed_start: int, versions: str) -> dict:
    """Merge one summary row per N into the demo results file and write it. Returns the document."""
    path = Path(path)
    if path.exists():
        doc = json.loads(path.read_text(encoding="utf-8"))
    else:
        doc = {"_readme": README, "environment": versions, "cases": [], "recordings": []}
    entries = [build_entry(c, seed_start, versions) for c in pick_dashboard_cases(cases)]
    replaced = {e["N"] for e in entries}
    doc["environment"] = versions
    doc["cases"] = [c for c in doc.get("cases", []) if c.get("N") not in replaced] + entries
    doc["cases"].sort(key=lambda c: c["N"])
    doc.setdefault("recordings", [])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc
