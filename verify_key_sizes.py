"""
verify_key_sizes.py - findings.json key sizes ki sanity check (Issue #2)

Kaam: key sizes validate karna aur har project ka summary dena.
Usage: python verify_key_sizes.py [outputs/findings.json]
Exit code: 0 = sab sahi, 1 = INVALID size ya project ka size nahi mila
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

# Standard RSA/DSA/DH sizes. Inke bahar ka size NONSTANDARD flag hoga.
VALID_SIZES = {512, 1024, 2048, 3072, 4096}

# 2048 se kam size classical attack se bhi tootta hai -> WEAK.
MIN_SAFE_BITS = 2048

# Sirf in primitives mein key size = modulus/prime bits hota hai.
# ECC mein size curve ka hota hai, isliye use yahan nahi jaanchte.
SIZE_CHECKED = {"RSA", "DSA", "DH"}


def load_findings(path):
    """findings.json ki 'findings' list nikalo (list form bhi chalega)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("findings", [])


def get_size(f):
    """modulus_bits ko key_size par priority (mapper ka same rule)."""
    return f.get("modulus_bits") or f.get("key_size")


def check(f):
    """Ek finding ka status: SKIP/UNRESOLVED/INVALID/WEAK/NONSTANDARD/OK."""
    prim = str(f.get("primitive", "")).upper()
    size = get_size(f)
    if prim not in SIZE_CHECKED:
        return "SKIP"
    # null size wrapper-call jaisi lines pe normal hai, error nahi.
    if size is None:
        return "UNRESOLVED"
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        return "INVALID"
    if size < MIN_SAFE_BITS:
        return "WEAK"
    if size not in VALID_SIZES:
        return "NONSTANDARD"
    return "OK"


def in_snippet(f, size):
    """Code snippet mein wo number likha hai? NO = variable se aaya ho sakta hai."""
    if not isinstance(size, int):
        return "-"
    return "YES" if str(size) in str(f.get("snippet", "")) else "NO"


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "outputs/findings.json"
    findings = load_findings(path)
    counts = defaultdict(int)
    projects = defaultdict(lambda: {"n": 0, "sizes": set()})

    print(f"{'STATUS':<12}{'PRIM':<6}{'BITS':<7}{'BASIS':<16}{'SNIP':<6}WHERE")
    for f in findings:
        status = check(f)
        counts[status] += 1
        if status == "SKIP":
            continue
        size = get_size(f)
        where = "{}/{}:{}".format(
            f.get("project", "?"), f.get("file"), f.get("line"))
        print(f"{status:<12}{str(f.get('primitive')):<6}{str(size):<7}"
              f"{str(f.get('size_basis')):<16}{in_snippet(f, size):<6}{where}")
        p = projects[f.get("project", "?")]
        p["n"] += 1
        if status in {"OK", "WEAK", "NONSTANDARD"}:
            p["sizes"].add(size)

    print("\n=== PROJECT SUMMARY (CBOM ke liye) ===")
    bad_project = False
    for name, p in sorted(projects.items()):
        sizes = sorted(p["sizes"]) if p["sizes"] else "NONE RESOLVED"
        if not p["sizes"]:
            bad_project = True
        print(f"{name}: {p['n']} findings, sizes = {sizes}")

    print("\nStatus counts:", dict(counts), "| total:", len(findings))
    # INVALID ya project ka koi size nahi -> CBOM mein galat number jayega.
    return 1 if counts.get("INVALID") or bad_project else 0


if __name__ == "__main__":
    sys.exit(main())
