"""
weights_lock.py
---------------
Freezes the risk-model weights. data/risk_weights.lock.json stores the version
and a SHA-256 fingerprint of data/risk_weights.json (computed on the JSON
content, so spacing and line endings do not matter).

  python src/weights_lock.py check    # exit 0 if the weights match the lock
  python src/weights_lock.py write    # (re)create the lock - only for a documented change

A weight change must come with: a new version number in risk_weights.json, an
entry in the change log of docs/risk_model.md, and a new lock. The unit test
tests/test_weights_frozen.py fails until all three agree.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEIGHTS = ROOT / "data" / "risk_weights.json"
LOCK = ROOT / "data" / "risk_weights.lock.json"


def fingerprint(path=WEIGHTS) -> str:
    """SHA-256 of the canonical JSON content (sorted keys, no spacing)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_lock(weights=WEIGHTS, lock=LOCK) -> dict:
    version = json.loads(Path(weights).read_text(encoding="utf-8"))["version"]
    record = {"version": version, "sha256": fingerprint(weights)}
    Path(lock).write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def check_lock(weights=WEIGHTS, lock=LOCK):
    """Return (ok, message)."""
    if not Path(lock).exists():
        return False, "lock file missing: run 'python src/weights_lock.py write'"
    rec = json.loads(Path(lock).read_text(encoding="utf-8"))
    version = json.loads(Path(weights).read_text(encoding="utf-8"))["version"]
    if rec.get("version") != version:
        return False, f"version in lock ({rec.get('version')}) differs from weights ({version})"
    if rec.get("sha256") != fingerprint(weights):
        return False, ("weights changed since they were frozen. Bump the version, add a "
                       "change-log entry in docs/risk_model.md, then run 'write'.")
    return True, f"weights {version} match the lock"


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "write":
        print("wrote lock:", write_lock())
    elif cmd == "check":
        ok, msg = check_lock()
        print(("OK: " if ok else "FAIL: ") + msg)
        sys.exit(0 if ok else 1)
    else:
        sys.exit("usage: python src/weights_lock.py [check|write]")