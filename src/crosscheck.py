"""
crosscheck.py - Week 2 Day 1: verify scanner output against the real source.

Two checks:
  A) LINE CHECK: for every finding in outputs/findings.json, open the real
     file, read line N, and confirm it is the same code the scanner reported.
  B) MISS HUNT: list lines that LOOK crypto-related (rsa, encrypt, pow(...))
     but have no finding. A human reads this list to spot scanner misses.

Usage (from the repo root):
    python src/crosscheck.py
Output: printed summary + docs/crosscheck_week2.md
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scanner                 # for SKIP_DIRS (same folders the scanner skips)
from run_all import TARGETS    # project name -> local folder

FINDINGS = "outputs/findings.json"
REPORT = "docs/crosscheck_week2.md"

# Words that suggest crypto code. Deliberately broad: it is better to show a
# human some noise than to silently hide a real miss.
HINT = re.compile(
    r"\b(rsa|encrypt\w*|decrypt\w*|cipher\w*|keypair|private_key|public_key|"
    r"modulus|totient|phi|gcd|isprime|hashlib|hmac|aes|sha\d*|md5)\b|\bpow\s*\(",
    re.IGNORECASE)


def read_lines(path):
    """Read a file the same way scanner.py does (utf-8, bad bytes ignored)."""
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return fh.read().splitlines()


def verify(findings):
    """Check A: return findings whose reported snippet != the real line."""
    cache, bad = {}, []
    for f in findings:
        path = os.path.join(TARGETS[f["project"]], f["file"])
        if path not in cache:
            cache[path] = read_lines(path)
        lines = cache[path]
        n = f["line"]
        # The scanner stores line.strip()[:200]; rebuild it the same way.
        actual = lines[n - 1].strip()[:200] if 0 < n <= len(lines) else None
        if actual != f["snippet"]:
            bad.append((f["project"], f["file"], n, f["snippet"], actual))
    return bad


def hunt(findings):
    """Check B: crypto-looking lines that have NO finding (possible misses)."""
    flagged = {(f["project"], f["file"], f["line"]) for f in findings}
    found = []
    for project, root in TARGETS.items():
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in scanner.SKIP_DIRS]
            for name in sorted(filenames):
                if not name.endswith(".py"):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                for i, line in enumerate(read_lines(full), 1):
                    if HINT.search(line) and (project, rel, i) not in flagged:
                        found.append((project, rel, i, line.strip()[:110]))
    return found


def clean(text):
    """Make text safe inside a markdown table cell."""
    return str(text).replace("|", "/").replace("`", "'")


def main():
    # Windows console (cp1252) cannot print emoji or em dashes found in the
    # target code. Show '?' on screen instead; the report file stays UTF-8.
    sys.stdout.reconfigure(errors="replace")

    with open(FINDINGS, encoding="utf-8") as fh:
        findings = json.load(fh)["findings"]

    bad = verify(findings)
    misses = hunt(findings)
    # Comments are usually prose, not code, so show real code lines first.
    code = [m for m in misses if not m[3].startswith("#")]

    print("Check A: %d of %d findings match the real source line"
          % (len(findings) - len(bad), len(findings)))
    for b in bad:
        print("  MISMATCH", b[1] + ":" + str(b[2]), "->", b[4])
    print("Check B: %d unflagged crypto-looking lines (%d are code, %d comments)"
          % (len(misses), len(code), len(misses) - len(code)))
    for m in code[:60]:
        print("  %-12s %s:%d  %s" % (m[0][:12], m[1], m[2], m[3]))
    if len(code) > 60:
        print("  ... %d more (see %s)" % (len(code) - 60, REPORT))

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as out:
        out.write("# Week 2 Day 1: scanner cross-check\n\n")
        out.write("**Check A** (finding matches real source line): %d of %d.\n\n"
                  % (len(findings) - len(bad), len(findings)))
        out.write("**Check B** (crypto-looking lines with no finding): %d, for manual review.\n\n"
                  % len(misses))
        out.write("| Project | File:line | Code | Review |\n|---|---|---|---|\n")
        for m in misses:
            out.write("| %s | %s:%d | `%s` | |\n" % (m[0][:14], m[1], m[2], clean(m[3])))
    print("Wrote", REPORT)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
