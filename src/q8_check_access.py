"""
q8_check_access.py - Week 4 Day 5: confirm IBM Quantum access and runtime limits for Q8.

WHAT THIS CHECKS (no circuits run here - just account/environment status)
---------------------------------------------------------------------------
  1. Is qiskit-ibm-runtime installed, and what version?
  2. Is there a saved IBM Quantum account/credential on this machine?
  3. If so, can we reach the service and list available backends?
  4. What does the account's plan report for runtime limits (e.g. minutes per month)?

This never submits a job and never runs a circuit - Q8's actual hardware runs (small circuits:
Q7, a 2-3 qubit Grover, a tiny Q1 case) are a SEPARATE step, to be done once this check passes
and the team has agreed to spend real runtime budget.

HONEST LIMITS
-------------
* IBM's published limits change over time; this script reports what YOUR account's service
  object says right now, not a number hard-coded from the plan's "last checked" figure.
* No real account configured is a NORMAL result if nobody has set one up yet - that is exactly
  the "confirm access" question Day 5 asks, and this script reports that plainly rather than
  erroring.

Usage (from the project root, venv active):
  python -m src.q8_check_access
  python -m src.q8_check_access --json outputs/q8_access.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check() -> dict:
    result = {"qiskit_ibm_runtime_installed": False, "qiskit_ibm_runtime_version": None,
             "saved_account_found": False, "service_reachable": False,
             "backends": [], "plan_info": None, "error": None}
    try:
        import qiskit_ibm_runtime
        result["qiskit_ibm_runtime_installed"] = True
        result["qiskit_ibm_runtime_version"] = qiskit_ibm_runtime.__version__
    except ImportError:
        result["error"] = ("qiskit-ibm-runtime is not installed. Install it with "
                           "`pip install qiskit-ibm-runtime` to go further (rule: use a "
                           "separate venv if it conflicts with the pinned qiskit version, "
                           "per the plan's Q13 fallback-venv note).")
        return result

    from qiskit_ibm_runtime import QiskitRuntimeService
    try:
        saved = QiskitRuntimeService.saved_accounts()
        result["saved_account_found"] = bool(saved)
        result["saved_account_names"] = list(saved.keys()) if saved else []
    except Exception as exc:
        result["error"] = f"Could not check for a saved account: {exc}"
        return result

    if not result["saved_account_found"]:
        result["error"] = ("No saved IBM Quantum account found on this machine. This is a "
                           "normal 'not yet confirmed' result for Day 5 - someone on the team "
                           "needs to run QiskitRuntimeService.save_account(token=...) once, "
                           "with a token from https://quantum.ibm.com, before Q8 can proceed.")
        return result

    try:
        service = QiskitRuntimeService()
        result["service_reachable"] = True
        backends = service.backends()
        result["backends"] = [{"name": b.name, "num_qubits": b.num_qubits,
                              "operational": b.status().operational} for b in backends]
    except Exception as exc:
        result["error"] = f"Found a saved account but could not reach the service: {exc}"
        return result

    try:
        # Not every qiskit-ibm-runtime version exposes the same usage/limits API; try the
        # common ones and report whatever is available rather than failing outright.
        if hasattr(service, "usage"):
            result["plan_info"] = service.usage()
        elif hasattr(service, "instances"):
            result["plan_info"] = {"instances": service.instances()}
    except Exception as exc:
        result["plan_info"] = f"could not read usage/limits info: {exc}"

    return result


def print_report(r: dict) -> None:
    print("=== Q8: IBM Quantum access check (Week 4 Day 5) ===")
    print(f"qiskit-ibm-runtime installed : {r['qiskit_ibm_runtime_installed']} "
         f"(version {r['qiskit_ibm_runtime_version']})" if r["qiskit_ibm_runtime_installed"]
         else "qiskit-ibm-runtime installed : False")
    print(f"saved account found           : {r['saved_account_found']}")
    if r.get("saved_account_names"):
        print(f"  account name(s)              : {r['saved_account_names']}")
    print(f"service reachable             : {r['service_reachable']}")
    if r["backends"]:
        print(f"backends available ({len(r['backends'])}):")
        for b in r["backends"][:10]:
            print(f"  - {b['name']}: {b['num_qubits']} qubits, operational={b['operational']}")
    if r["plan_info"] is not None:
        print(f"plan / usage info              : {r['plan_info']}")
    if r["error"]:
        print(f"\nNOTE: {r['error']}")
    print("\nThis checks access only; no circuit was run and no runtime budget was spent.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="also write the result to this JSON file")
    args = ap.parse_args()
    r = check()
    print_report(r)
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"\nwrote {out}")
    return 0 if r["service_reachable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
