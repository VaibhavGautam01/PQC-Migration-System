"""
quantum_guard.py - static guard for rule 8 (Q12, Week 2 Day 1).

Scans the circuit-builder code and reports obvious classical shortcuts:
  * imports of sympy, or of order-finding / factoring / discrete-log helpers
  * calls to such helpers (n_order, factorint, classical_period, ...)
  * a loop that searches for a period, for example `for r in range(1, N): if pow(a, r, N) == 1`.
    A loop over a short constant list or range (at most 16 values) is allowed: that is the
    post-processing check of a candidate period taken from a measurement, not a search

Allowed: pow(a, x, N) outside such a loop. Building the unitary from it is the oracle
the algorithm is given (rule 8, Q1). gcd and Fraction are post-processing and are
not flagged.
A static test only catches obvious shortcuts: a second person still reviews every
circuit builder (plan, rule 8).
Aer simulator, toy size.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FORBIDDEN_NAMES = {
    "n_order", "multiplicative_order", "factorint", "primefactors", "divisors",
    "totient", "discrete_log", "sqrt_mod", "isprime", "classical_period",
    "factors_from_period", "find_period", "order_finding",
}
FORBIDDEN_MODULE_ROOTS = {"sympy"}
BUILDER_PREFIXES = ("build_", "c_amod", "controlled_", "qft", "phi_", "modular_",
                    "oracle", "grover", "diffusion")

# path -> "all" (every function is a builder) or "builders" (only builder-named functions)
GUARDED = {
    "src/q2_arith.py": "all",
    "notebook/shors_demo.py": "builders",
    "stego_analyzer/quantum_stage.py": "all",     # the analyzer's Shor stage (plan Section 9, Analyzer rule)
}


def discover_guarded():
    """GUARDED plus every src/q<number>_*.py, so a new Q module is scanned automatically."""
    found = dict(GUARDED)
    for p in sorted((ROOT / "src").glob("q[0-9]*.py")):
        found.setdefault(p.relative_to(ROOT).as_posix(), "all")
    return found


def is_builder(name):
    return name.startswith(BUILDER_PREFIXES)


def _call_name(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _is_three_arg_pow(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "pow" and len(node.args) == 3)


MAX_BOUNDED_LOOP = 16


def _is_small_constant_iter(loop):
    """True for `for k in (1, 2, 3, 4)` or `for k in range(1, 5)`: a bounded, constant loop."""
    if not isinstance(loop, ast.For):
        return False
    it = loop.iter
    if isinstance(it, (ast.Tuple, ast.List)):
        return len(it.elts) <= MAX_BOUNDED_LOOP and all(isinstance(e, ast.Constant) for e in it.elts)
    if (isinstance(it, ast.Call) and isinstance(it.func, ast.Name) and it.func.id == "range"
            and it.args and all(isinstance(a, ast.Constant) and isinstance(a.value, int) for a in it.args)):
        vals = [a.value for a in it.args]
        stop = vals[0] if len(vals) == 1 else vals[1]
        return stop <= MAX_BOUNDED_LOOP
    return False


def _period_search_loops(tree):
    """Yield loops whose body compares pow(a, x, N) with 1 (the order-finding signature)."""
    for loop in ast.walk(tree):
        if not isinstance(loop, (ast.For, ast.While)) or _is_small_constant_iter(loop):
            continue
        for sub in ast.walk(loop):
            if not isinstance(sub, ast.Compare):
                continue
            operands = [sub.left] + list(sub.comparators)
            has_pow = any(_is_three_arg_pow(n) for o in operands for n in ast.walk(o))
            has_one = any(isinstance(o, ast.Constant) and o.value == 1 for o in operands)
            if has_pow and has_one:
                yield loop
                break


def scan_source(source, mode="all", filename="<source>"):
    """Return a list of 'file:line: reason' strings (empty list = clean)."""
    tree = ast.parse(source, filename=filename)
    problems = []

    # imports (module level and inside functions)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in FORBIDDEN_MODULE_ROOTS:
                    problems.append(f"{filename}:{node.lineno}: imports {a.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in FORBIDDEN_MODULE_ROOTS:
                problems.append(f"{filename}:{node.lineno}: imports from {node.module}")
            for a in node.names:
                if a.name in FORBIDDEN_NAMES:
                    problems.append(f"{filename}:{node.lineno}: imports {a.name}")

    # the code to check: every function, or only builder-named ones
    funcs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if mode == "all":
        scopes = [tree]            # the whole module: every function and module-level code
    else:
        scopes = [f for f in funcs if is_builder(f.name)]
    for scope in scopes:
        name = getattr(scope, "name", "<module>")
        for node in ast.walk(scope):
            if isinstance(node, ast.Call) and _call_name(node) in FORBIDDEN_NAMES:
                problems.append(f"{filename}:{node.lineno}: {name} calls {_call_name(node)}()")
        for loop in _period_search_loops(scope):
            problems.append(f"{filename}:{loop.lineno}: {name} has a loop that searches for a "
                            f"period (pow(..) == 1)")
    return sorted(set(problems))


def builder_functions(source):
    """Names of the builder-named functions in a source string."""
    tree = ast.parse(source)
    return sorted(n.name for n in ast.walk(tree)
                  if isinstance(n, ast.FunctionDef) and is_builder(n.name))


def scan_file(relpath, mode):
    p = ROOT / relpath
    return scan_source(p.read_text(encoding="utf-8-sig"), mode, relpath)


def scan_all():
    out = []
    for rel, mode in discover_guarded().items():
        out += scan_file(rel, mode)
    return out


if __name__ == "__main__":
    problems = scan_all()
    for p in problems:
        print(p)
    print("static guard:", "FAILED" if problems else "OK")
    raise SystemExit(1 if problems else 0)
