"""
edge_cases.py - Edge-case detection for the PQC Migration Advisor.

Finds crypto problems that a plain signature scan reports only as
"RSA is used":

  1. check_padding        - RSA used without OAEP/PKCS1 padding (textbook RSA)
  2. find_crypto_imports  - files that import known crypto libraries
  3. find_indirect_usage  - files that use crypto defined in another file

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
    return [f for f in Path(repo_path).rglob("*.py")
            if not SKIP_DIRS.intersection(f.parts)]


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


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print("Crypto imports:", find_crypto_imports(target))
    for fl in find_indirect_usage(target):
        print(fl)