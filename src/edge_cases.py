"""
edge_cases.py - Edge-case detection for the PQC Migration Advisor.

Finds crypto problems that a plain signature scan reports only as
"RSA is used":

  1. check_padding        - RSA used without OAEP/PKCS1 padding (textbook RSA)
  2. find_crypto_imports  - files that import known crypto libraries
  3. find_indirect_usage  - files that use crypto defined in another file
  4. find_insecure_rng    - key material drawn from a non-cryptographic RNG

Used by run_padding_check.py and merge_flags.py.
"""
import ast
import re
from pathlib import Path

# Patterns showing a secure padding scheme is present
SAFE_PADDING_PATTERNS = [r"OAEP", r"PKCS1_OAEP", r"PKCS1_v1_5", r"PSS"]

# Patterns showing raw (textbook) RSA arithmetic
RAW_RSA_PATTERNS = [
    r"pow\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*\)",   # pow(m, e, n)
    r"\*\*\s*\w+\s*%\s*\w+",                       # m**e % n
]

# Imports that signal a crypto library
CRYPTO_IMPORT_PATTERNS = [
    r"from\s+Crypto",
    r"import\s+rsa\b",          # \b avoids matching 'import rsa_utils'
    r"from\s+cryptography",
    r"import\s+hashlib",
    r"from\s+Cryptodome",
]

# Lines searched on each side of an RSA hit when looking for padding
WINDOW = 15

# Folders skipped when walking a repository
SKIP_DIRS = {"venv", "__pycache__", ".git"}


def _python_files(repo_path):
    """All .py files under repo_path, skipping virtualenvs and caches."""
    return sorted(f for f in Path(repo_path).rglob("*.py")
              if not SKIP_DIRS.intersection(f.parts))


def check_padding(file_path, rsa_line):
    """Flag RSA usage with no secure padding near the given line.

    Looks WINDOW lines either side of rsa_line. Returns a flag dict if raw
    RSA arithmetic is present or no padding pattern is found, else None.
    This is a heuristic: confirm each flag by reading the code.
    """
    lines = Path(file_path).read_text(errors="ignore").splitlines()
    start = max(0, rsa_line - WINDOW)
    end = min(len(lines), rsa_line + WINDOW)
    context = "\n".join(lines[start:end])

    has_safe = any(re.search(p, context) for p in SAFE_PADDING_PATTERNS)
    has_raw = any(re.search(p, context) for p in RAW_RSA_PATTERNS)

    if has_raw or not has_safe:
        return {
            "flag": "NO_PADDING",
            "file": str(file_path),
            "line": rsa_line,
            "detail": "RSA used without OAEP/PKCS1 padding (textbook RSA)",
        }
    return None


def find_crypto_imports(repo_path):
    """Map each file to the crypto-import patterns it matches."""
    results = {}
    for f in _python_files(repo_path):
        text = f.read_text(errors="ignore")
        hits = [p for p in CRYPTO_IMPORT_PATTERNS if re.search(p, text)]
        if hits:
            results[str(f)] = hits
    return results


def find_indirect_usage(repo_path, provider_files=None):
    """Flag files that import a crypto module defined in another file.

    provider_files: file names known to contain crypto (for example from
    findings.json). If None, providers are auto-detected by pattern.
    Returns a list of INDIRECT_USAGE flag dicts.
    """
    py_files = _python_files(repo_path)

    if provider_files is None:
        providers = set()
        for f in py_files:
            text = f.read_text(errors="ignore")
            if any(re.search(p, text)
                   for p in CRYPTO_IMPORT_PATTERNS + RAW_RSA_PATTERNS):
                providers.add(f.stem)
    else:
        providers = {Path(p).stem for p in provider_files}

    flags = []
    for f in py_files:
        try:
            tree = ast.parse(f.read_text(errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in providers:
                module, names = node.module, [a.name for a in node.names]
            elif isinstance(node, ast.Import):
                hits = [a.name for a in node.names if a.name in providers]
                if not hits:
                    continue
                module, names = hits[0], hits
            else:
                continue
            if module == f.stem:
                continue
            flags.append({
                "flag": "INDIRECT_USAGE",
                "file": f.name,
                "line": node.lineno,
                "detail": f"imports crypto module '{module}' ({', '.join(names)})",
            })
    return flags


# Functions of the stdlib `random` module (Mersenne Twister, not a CSPRNG)
INSECURE_RANDOM_FUNCS = {
    "choice", "choices", "randint", "randrange", "getrandbits", "sample",
    "shuffle", "random", "uniform", "randbytes",
}

# sympy helpers that draw from the same Mersenne Twister
INSECURE_SYMPY_FUNCS = {"randprime", "randint"}


def _insecure_rng_calls(tree):
    """Yield (line, description) for non-cryptographic RNG calls in an AST.

    Matches random.<fn>(...) (also under an alias), names imported with
    `from random import <fn>`, and sympy's randprime/randint. Calls on
    random.SystemRandom() or the secrets module are not flagged.
    """
    random_aliases, random_names, sympy_names, sympy_aliases = set(), {}, {}, set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "random":
                    random_aliases.add(a.asname or "random")
                elif a.name == "sympy":
                    sympy_aliases.add(a.asname or "sympy")
        elif isinstance(node, ast.ImportFrom):
            if node.module == "random":
                for a in node.names:
                    if a.name in INSECURE_RANDOM_FUNCS:
                        random_names[a.asname or a.name] = a.name
            elif node.module and node.module.split(".")[0] == "sympy":
                for a in node.names:
                    if a.name in INSECURE_SYMPY_FUNCS:
                        sympy_names[a.asname or a.name] = a.name
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id in random_aliases and func.attr in INSECURE_RANDOM_FUNCS:
                yield node.lineno, f"random.{func.attr}() (Mersenne Twister)"
            elif func.value.id in sympy_aliases and func.attr in INSECURE_SYMPY_FUNCS:
                yield node.lineno, f"sympy.{func.attr}() (Mersenne Twister)"
        elif isinstance(func, ast.Name):
            if func.id in random_names:
                yield node.lineno, f"{random_names[func.id]}() from random (Mersenne Twister)"
            elif func.id in sympy_names:
                yield node.lineno, f"{sympy_names[func.id]}() from sympy (Mersenne Twister)"


def find_insecure_rng(repo_path, provider_files=None):
    """Flag non-cryptographic random number generators in crypto code.

    provider_files: file names that contain crypto findings. Only these files
    are checked, so a random.choice() in unrelated code is not reported. If
    None, every Python file is checked. Returns INSECURE_RNG flag dicts.
    This is a heuristic: it cannot tell whether the value feeds a key.
    """
    wanted = None if provider_files is None else {Path(p).name for p in provider_files}
    flags = []
    for f in _python_files(repo_path):
        if wanted is not None and f.name not in wanted:
            continue
        try:
            tree = ast.parse(f.read_text(errors="ignore"))
        except SyntaxError:
            continue
        for line, what in _insecure_rng_calls(tree):
            flags.append({
                "flag": "INSECURE_RNG",
                "file": f.name,
                "line": line,
                "detail": f"{what} used in a file with crypto code; "
                          "key material needs a CSPRNG (secrets / os.urandom)",
            })
    return sorted(flags, key=lambda x: (x["file"], x["line"]))


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print("Crypto imports:", find_crypto_imports(target))
    for fl in find_indirect_usage(target):
        print(fl)
