"""triage_checkb.py - sorts the 166 "Check B" lines from docs/crosscheck_week2.md.

Check B lists crypto-looking lines the scanner did NOT flag. Most are harmless
(comments, docstrings, UI text). A few may be real misses = scanner bugs to fix.
This script splits them so you only review the likely-real ones by hand.

It is READ-ONLY: it never edits the doc or the scanner.
Run:  python src/triage_checkb.py [path/to/crosscheck_week2.md]
"""
import re
import sys

DOC = sys.argv[1] if len(sys.argv) > 1 else "docs/crosscheck_week2.md"

# One markdown table row looks like:  | Project | file.py:12 | `code here` | |
ROW = re.compile(r"^\|\s*(?P<proj>[^|]+?)\s*\|\s*(?P<loc>[^|]+?)\s*\|\s*`(?P<code>.*)`\s*\|")

# Real crypto code: calls/defs of encrypt/decrypt, phi math, prime or GCD helpers,
# modular pow, hashing, sympy/hashlib imports. These are what a scanner SHOULD catch.
LIKELY_REAL = re.compile(
    r"\b(encrypt|decrypt)\w*\s*\("      # encrypt_int(...), decrypt_message(...)
    r"|def\s+(encrypt|decrypt)"          # def encrypt_text(...)
    r"|\bphi\b"                          # phi(n) math used for key generation
    r"|isprime|getPrime|\bGCD\b|\bgcd\b" # prime / coprime helpers used for key generation
    r"|\bpow\s*\("                       # modular exponentiation c = pow(m, e, n)
    r"|hashlib|sha256|SHA256"            # hashing (SHA family)
    r"|import\s+sympy|from\s+sympy"      # library imports
)


def is_noise(code: str) -> bool:
    """True for lines that only *mention* crypto: comments, docstrings, UI text."""
    c = code.strip()
    if c.startswith(("#", '"""', "'''", '"', "'", "f\"", "f'", "<")):
        return True                          # comment, docstring or string / HTML fragment
    if re.match(r"^\d+\.\s", c):
        return True                          # numbered docstring step like "3. phi(n) = ..."
    if c.startswith(("st.", "with st.", "print(")):
        return True                          # Streamlit / print output text
    if "(" not in c and "=" not in c and not c.startswith(("import", "from", "def", "class")):
        return True                          # plain English sentence, no code shape
    return False


real, other, noise = [], [], []
with open(DOC, encoding="utf-8", errors="replace") as fh:
    for line in fh:
        m = ROW.match(line)
        if not m:
            continue                         # skip headers and damaged rows
        item = (m["proj"], m["loc"], m["code"].strip())
        if is_noise(m["code"]):
            noise.append(item)
        elif LIKELY_REAL.search(m["code"]):
            real.append(item)
        else:
            other.append(item)

print(f"Total rows read: {len(real) + len(other) + len(noise)}")
print(f"  likely false alarms (comments/docstrings/UI text): {len(noise)}")
print(f"  other code lines (probably fine, glance quickly):  {len(other)}")
print(f"  LIKELY REAL MISSES (review these by hand):         {len(real)}\n")

print("=== LIKELY REAL MISSES ===")
for proj, loc, code in real:
    print(f"{proj[:14]:14} {loc:28} {code[:90]}")

print("\n=== OTHER CODE LINES ===")
for proj, loc, code in other:
    print(f"{proj[:14]:14} {loc:28} {code[:90]}")
