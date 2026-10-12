"""
generate_risk_entries.py
------------------------
Reads findings.json (Stage 1 output) and produces one risk entry per
finding using qubit_estimator (Issue #8).

Usage:
    python generate_risk_entries.py [path/to/findings.json]
Output:
    output/risk_entries.json  (generated data, kept out of Git)
"""

import json
import sys
from pathlib import Path

from qubit_estimator import (
    grover_effective_security,
    grover_logical_qubits,
    grover_verdict,
    shor_logical_qubits,
)

# Adjust these if your findings.json uses different field names.
FIELD_CANDIDATES = {
    "project": ("project", "repo", "repository", "target"),
    "primitive": ("primitive", "algorithm", "type", "crypto"),
    "key_bits": ("modulus_bits", "key_size", "key_bits", "key_length", "bits"),
    "file": ("file", "path", "filename"),
    "line": ("line", "line_number", "lineno"),
    "padding": ("padding", "padding_status", "padding_flag"),
}


def pick(finding: dict, field: str):
    """Return the first non-null value for a logical field, or None."""
    for name in FIELD_CANDIDATES[field]:
        if finding.get(name) is not None:
            return finding[name]
    return None

def flatten(data) -> list:
    """Turn findings.json into a flat list of finding dicts."""
    if isinstance(data, list):
        return [f for f in data if isinstance(f, dict)]
    if isinstance(data, dict):
        if isinstance(data.get("findings"), list):
            return flatten(data["findings"])
        flat = []
        for key, value in data.items():     # shape: {project: [findings...]}
            if isinstance(value, list):
                for f in flatten(value):
                    flat.append({"project": key, **f})
        return flat
    return []


def to_int(value):
    """Convert '2048' or 2048 to int; return None if impossible."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_entry(finding: dict) -> dict:
    """Build one risk entry from one finding."""
    primitive = str(pick(finding, "primitive") or "UNKNOWN").upper().strip()
    bits = to_int(pick(finding, "key_bits"))

    entry = {
        "project": pick(finding, "project"),
        "primitive": primitive,
        "key_bits": bits,
        "file": pick(finding, "file"),
        "line": pick(finding, "line"),
        "padding": pick(finding, "padding"),
        "quantum_algorithm": None,
        "logical_qubits": None,
        "effective_security_bits": None,
        "verdict": None,
        "note": "",
    }

    if bits is None:
        entry["note"] = "Key size missing in findings; cannot estimate."
        entry["verdict"] = "UNKNOWN"
    elif primitive.startswith("RSA"):
        entry["quantum_algorithm"] = "Shor's"
        entry["logical_qubits"] = shor_logical_qubits(bits)
        entry["verdict"] = "VULNERABLE (Shor's gives a full break)"
        entry["note"] = "Logical qubits only; physical qubits are far higher."
    elif primitive.startswith("AES"):
        entry["quantum_algorithm"] = "Grover's"
        entry["logical_qubits"] = grover_logical_qubits(bits)
        entry["effective_security_bits"] = grover_effective_security(bits)
        entry["verdict"] = grover_verdict(bits)
    elif primitive.startswith("SHA"):
        entry["quantum_algorithm"] = "Grover's"
        entry["effective_security_bits"] = grover_effective_security(bits)
        entry["verdict"] = grover_verdict(bits)
        entry["note"] = "Preimage search only; no AES-style qubit table applies."
    else:
        entry["note"] = f"No estimator for primitive '{primitive}' yet."
        entry["verdict"] = "NOT ESTIMATED"
    return entry


def aggregate(entries: list):
    """Group sized findings into one row per (project, primitive, key_bits).

    Findings without a size (padding, modexp, phi, ...) are not separate
    keys; they are counted as supporting findings for their project.
    """
    rows, unsized = {}, {}
    for e in entries:
        if e["key_bits"] is None:
            k = (e["project"], e["primitive"])
            unsized[k] = unsized.get(k, 0) + 1
            continue
        k = (e["project"], e["primitive"], e["key_bits"])
        if k not in rows:
            row = dict(e)
            row.pop("file")
            row.pop("line")
            row["evidence"] = []
            row["size_confirmed"] = False
            rows[k] = row
        rows[k]["evidence"].append(f"{e['file']}:{e['line']}")
        if "assumed" not in str(e.get("size_basis") or ""):
            rows[k]["size_confirmed"] = True   # at least one non-assumed source
    result = list(rows.values())
    for r in result:
        r["unsized_findings_same_primitive"] = unsized.get((r["project"], r["primitive"]), 0)
    return result


def main(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    findings = flatten(data)
    if not findings:
        sys.exit(f"No findings found in {path}. Check its structure.")

    entries = [build_entry(f) for f in findings]
    rows = aggregate(entries)

    out_dir = Path("output")
    out_dir.mkdir(exist_ok=True)
    (out_dir / "risk_entries.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    (out_dir / "risk_entries_raw.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")

    print(f"{len(findings)} findings -> {len(rows)} risk entries\n")
    print(f"{'Project':<28}{'Prim':<6}{'Bits':>6}{'Qubits':>8}  {'Confirmed':<10}Verdict")
    print("-" * 100)
    for r in rows:
        print(f"{str(r['project']):<28}{r['primitive']:<6}{str(r['key_bits']):>6}"
              f"{str(r['logical_qubits']):>8}  {str(r['size_confirmed']):<10}{r['verdict']}")
    print("\nWrote output/risk_entries.json (grouped) and output/risk_entries_raw.json")

def find_findings_file() -> Path:
    """Locate findings.json without needing a command-line argument."""
    here = Path(__file__).resolve().parent      # .../notebook
    root = here.parent                          # repo root
    candidates = [
        root / "outputs" / "findings.json",
        root / "findings.json",
        here / "findings.json",
        Path.cwd() / "outputs" / "findings.json",
        Path.cwd() / "findings.json",
    ]
    for c in candidates:
        if c.exists():
            return c
    tried = "\n  ".join(str(c) for c in candidates)
    sys.exit(f"findings.json not found. Looked in:\n  {tried}\n"
             "Or pass the path: python generate_risk_entries.py <path>")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(find_findings_file())
    main(target)