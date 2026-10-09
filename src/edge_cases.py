"""
edge_cases.py - Edge-case detection for the PQC Migration Advisor.

Detects:
  1. RSA used without secure padding (textbook RSA)
  2. Indirect crypto usage (imported in one file, used in another)
"""
import re
from pathlib import Path

# Patterns showing SECURE padding is present
SAFE_PADDING_PATTERNS = [r"OAEP", r"PKCS1_OAEP", r"PKCS1_v1_5", r"PSS"]

# Patterns showing raw (textbook) RSA
RAW_RSA_PATTERNS = [
    r"pow\s*\(\s*\w+\s*,\s*\w+\s*,\s*\w+\s*\)",   # pow(m, e, n)
    r"\*\*\s*\w+\s*%\s*\w+",                       # m**e % n
]

# Imports that signal crypto libraries
CRYPTO_IMPORT_PATTERNS = [
    r"from\s+Crypto", r"import\s+rsa", r"from\s+cryptography",
    r"import\s+hashlib", r"from\s+Cryptodome",
]

WINDOW = 15  # lines around an RSA hit to search for padding


def check_padding(file_path, rsa_line):
    """Return a flag dict if no secure padding appears near an RSA line."""
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
    """Map each file to the crypto libraries it imports."""
    results = {}
    for f in Path(repo_path).rglob("*.py"):
        text = f.read_text(errors="ignore")
        hits = [p for p in CRYPTO_IMPORT_PATTERNS if re.search(p, text)]
        if hits:
            results[str(f)] = hits
    return results


def find_indirect_usage(repo_path):
    """TODO (Day 3): detect crypto defined in one file and used in another."""
    raise NotImplementedError


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    print(find_crypto_imports(target))