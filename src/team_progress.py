"""team_progress.py - detects each member's Week 1 deliverables from repo files.

Nothing is hard-coded: when a member pushes a file, refresh the dashboard
and his tasks flip to Done. Score: 1 = done, 0.5 = partly, 0 = missing.
"""
import ast
import os

SKIP = {"venv", ".venv", "__pycache__", ".git"}


def find(root, name=None, pred=None):
    """Return the first file called `name` (or matching `pred`) under root."""
    for base, dirs, files in os.walk(root):
        rel = os.path.relpath(base, root).replace("\\", "/")
        dirs[:] = [d for d in dirs if d not in SKIP and not (rel == "data" and d == "targets")]
        for fn in files:
            if fn == name or (pred and pred(fn)):
                return os.path.join(base, fn)
    return None


def text(path):
    """Read a text file; empty string if missing."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except (OSError, TypeError):
        return ""


def names(path):
    """Top-level function and class names of a Python file."""
    try:
        tree = ast.parse(text(path))
    except SyntaxError:
        return set()
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


def doc_ratio(path):
    """Share of the module, functions and classes that have a docstring."""
    try:
        tree = ast.parse(text(path))
    except SyntaxError:
        return 0.0
    items = [tree] + [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    return sum(bool(ast.get_docstring(n)) for n in items) / len(items)


def evaluate(root, raw):
    """Return one dict per member: name, role, color, tasks, pct."""
    F = lambda n: find(root, n)
    d = lambda ok: 1.0 if ok else 0.0
    gi = os.path.join(root, ".gitignore")
    gi_ok = os.path.isfile(gi) and os.path.getsize(gi) > 0
    setup = all(os.path.exists(os.path.join(root, p))
                for p in ("README.md", "requirements.txt", "src", "tests", "outputs"))
    edge, est, mapper = F("edge_cases.py"), F("qubit_estimator.py"), F("quantum_mapper.py")
    mt = text(mapper)
    prims = sum(p in mt for p in ("RSA", "ECC", "DSA", "DH", "AES", "SHA"))
    merged = "edge_cases" in raw or any("edge_flag" in x for x in raw["findings"])
    mf = F("merge_flags.py")
    dr = doc_ratio(mapper) if mapper else 0.0
    ex = text(F("extra_patterns.py"))

    plan = [
        ("Tarun Saxena", "Detection Engine Lead", "#00B0FF", [
            ("Mon", "Repo, folders, README, requirements, .gitignore",
             1.0 if setup and gi_ok else 0.5 if setup else 0.0, "" if gi_ok else ".gitignore is empty"),
            ("Tue", "RSA detection patterns + first scan", d("RSA" in text(F("scanner.py"))), ""),
            ("Wed", "ECC / AES / SHA signatures", d(all(k in ex for k in ("ECC", "AES", "SHA"))), ""),
            ("Thu", "Key-size extraction", d(F("key_size.py")), ""),
            ("Fri", "findings.json v1", d(raw.get("total_findings", 0) > 0), "")]),
        ("Vaibhav Gautam", "Edge-Case Specialist", "#B388FF", [
            ("Mon", "edge_cases.py scaffold", d(edge), ""),
            ("Tue", "Padding-check logic", d("check_padding" in names(edge)), ""),
            ("Wed", "Indirect-usage detection", d("find_indirect_usage" in names(edge)), ""),
            ("Thu", "Manual validation of flags", d(F("edge_case_validation.md")), ""),
            ("Fri", "Merge flags into findings.json",
             1.0 if mf and merged else 0.5 if mf else 0.0,
             "" if merged else "merge script ready, flags not in findings.json yet")]),
        ("Uday Pratap Singh", "Migration Advisor", "#FFAB40", [
            ("Mon", "quantum_mapper.py with full table",
             1.0 if prims == 6 else 0.5 if mapper else 0.0, f"{prims}/6 primitives" if 0 < prims < 6 else ""),
            ("Tue", "Unit tests for the mapper",
             d(find(root, pred=lambda n: n.startswith("test") and "mapper" in n)), ""),
            ("Wed", "AES / SHA routed to Grover's", d("Grover" in mt and "AES" in mt and "SHA" in mt), ""),
            ("Thu", "mapping_report.md draft", d(F("mapping_report.md")), ""),
            ("Fri", "Docstrings and polish", 1.0 if dr >= 0.9 else 0.5 if dr > 0 else 0.0, "")]),
        ("Yatharth Raghuvanshi", "Risk Scoring & ML", "#1DE9B6", [
            ("Mon", "Shor's qubit estimator (2n + 3)", d("shor_logical_qubits" in names(est)), ""),
            ("Tue", "Qiskit install verified", d(F("verify_qiskit.py")), ""),
            ("Wed", "Grover's formula for symmetric keys", d("grover_effective_security" in names(est)), ""),
            ("Thu", "Shor's N = 15 circuit skeleton", d(F("shors_demo.py") or F("shor_demo.py")), ""),
            ("Fri", "Unit tests for the estimator", d(F("test_qubit_estimator.py")), "")]),
    ]
    return [dict(name=n, role=r, color=c, tasks=t, pct=sum(x[2] for x in t) / len(t))
            for n, r, c, t in plan]
