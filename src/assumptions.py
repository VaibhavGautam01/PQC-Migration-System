"""
assumptions.py - validating loader for the Section 5 assumptions (Week 1 Day 3).

Reads the "assumptions" block of data/manual_facts.json:
  X secret_years, Y migration_years, Z quantum_years (central value + scenarios),
  exposure, attacker, and whether sir agreed (with the date).
Until agreed_with_sir is true, the dashboard must show the score as a range over
the Z scenarios. Per-project overrides go under "project_overrides".
Stdlib only.
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS_PATH = ROOT / "data" / "manual_facts.json"
PROJECTS = ("image", "video")
EXPOSURES = ("public", "restricted")
NUMERIC = ("secret_years", "migration_years", "quantum_years")


class AssumptionError(ValueError):
    pass


def _check_numeric(name, block):
    if not isinstance(block, dict) or "value" not in block:
        raise AssumptionError(f"{name}: needs a 'value'")
    v = block["value"]
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
        raise AssumptionError(f"{name}: value must be a positive number")
    sc = block.get("scenarios", [v])
    if not sc or any(isinstance(s, bool) or not isinstance(s, (int, float)) or s <= 0 for s in sc):
        raise AssumptionError(f"{name}: scenarios must be positive numbers")
    if v not in sc:
        raise AssumptionError(f"{name}: central value {v} must be one of the scenarios {sc}")


def validate(a):
    """Raise AssumptionError on the first problem; return a unchanged otherwise."""
    if not isinstance(a, dict):
        raise AssumptionError("assumptions block must be an object")
    for name in NUMERIC:
        if name not in a:
            raise AssumptionError(f"missing: {name}")
        _check_numeric(name, a[name])
    if a.get("exposure") not in EXPOSURES:
        raise AssumptionError(f"exposure must be one of {EXPOSURES}")
    if not isinstance(a.get("attacker"), str) or not a["attacker"]:
        raise AssumptionError("attacker must be a non-empty string")
    agreed = a.get("agreed_with_sir")
    if not isinstance(agreed, bool):
        raise AssumptionError("agreed_with_sir must be true or false")
    d = a.get("agreed_date")
    if agreed:
        try:
            date.fromisoformat(d)
        except (TypeError, ValueError):
            raise AssumptionError("agreed_with_sir is true, so agreed_date must be YYYY-MM-DD")
    elif d is not None:
        raise AssumptionError("agreed_date must be null until sir agrees")
    for proj, ov in a.get("project_overrides", {}).items():
        if proj not in PROJECTS:
            raise AssumptionError(f"unknown project in overrides: {proj}")
        for name in ov:
            if name not in NUMERIC and name not in ("exposure", "attacker"):
                raise AssumptionError(f"{proj}: cannot override {name}")
    return a


def load_assumptions(project=None, path=None):
    """Return the validated assumptions, with a project's overrides applied.

    Result keys: secret_years, migration_years, quantum_years (each {value, scenarios}),
    exposure, attacker, agreed_with_sir, agreed_date.
    """
    path = Path(path) if path else FACTS_PATH
    with open(path, encoding="utf-8-sig") as fh:
        raw = json.load(fh)
    if "assumptions" not in raw:
        raise AssumptionError("manual_facts.json has no 'assumptions' block")
    a = validate(raw["assumptions"])
    out = {k: a[k] for k in (*NUMERIC, "exposure", "attacker", "agreed_with_sir", "agreed_date")}
    if project is not None:
        if project not in PROJECTS:
            raise AssumptionError(f"unknown project: {project}")
        for name, val in a.get("project_overrides", {}).get(project, {}).items():
            out[name] = val
        for name in NUMERIC:
            _check_numeric(name, out[name])
    return out


def z_scenarios(a):
    """The Z values the dashboard must show (central value first)."""
    z = a["quantum_years"]
    return [z["value"]] + [s for s in z.get("scenarios", []) if s != z["value"]]
