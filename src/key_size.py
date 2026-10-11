"""
key_size.py - Day 4: key-size extraction for scanner.py.

Problems this module fixes (found on the two target repos):
  1. The look-ahead used to cross function boundaries, so randprime(low, high)
     picked up "bits=256" from the NEXT function's signature.
  2. Sizes held in variables (half, KEY_BITS, key_size=...) were never resolved.
  3. A per-prime size (getPrime(512)) was reported as if it were the RSA
     modulus size. The modulus is 2 x the prime size.

Fields added to every finding:
  key_size     : the number found in the code (may be a per-prime size)
  modulus_bits : estimated RSA/DSA/DH modulus size (None for ECC/AES/SHA)
  size_basis   : short note on how the number was found
"""
import re

MIN_BITS, MAX_BITS = 8, 16384   # anything outside this is not a key size (e.g. 65537)
MAX_CALL_LINES = 4              # how many lines a multi-line call may span
PER_PRIME_IDS = {"RSA-MANUAL-PRIME", "RSA-MANUAL-PRIME-LIB"}
MODULUS_PRIMITIVES = {"RSA", "DSA", "DH"}

# keyword argument with a literal number: key_size=2048, bits=128
KEYWORD_NUM = [
    (re.compile(r"\bkey_size\s*=\s*(\d+)"), "key_size"),
    (re.compile(r"\bbits\s*=\s*(\d+)"), "bits"),
    (re.compile(r"\binitialize\s*\(\s*(\d+)"), "key_size"),
]
# keyword argument with a variable: key_size=size
KEYWORD_NAME = re.compile(r"\b(key_size|bits|key_bits|nbits|modulus_bits)\s*=\s*([A-Za-z_]\w*)")
# first positional argument that is a variable: getPrime(half)
FIRST_ARG_NAME = re.compile(r"\(\s*([A-Za-z_]\w*)\s*[,)]")


def call_statement(lines, idx, start):
    """Return the text of the call that starts at lines[idx][start:].

    If the parentheses are still open at the end of the line, the next lines
    are appended (max MAX_CALL_LINES). This replaces the old fixed 3-line
    look-ahead, which wandered into unrelated code.
    """
    # Start at the match itself, so text before it on the line is ignored.
    text = lines[idx][start:]
    # depth = number of "(" still open; 0 means the call ends on this line.
    depth = text.count("(") - text.count(")")
    j = idx
    # Read on until the call closes. The two limits (end of file and
    # MAX_CALL_LINES) stop a missing ")" from swallowing the whole file.
    while depth > 0 and j + 1 < len(lines) and j - idx < MAX_CALL_LINES:
        j += 1
        # Join with a space so a split call reads like one line for the regexes.
        text += " " + lines[j]
        depth += lines[j].count("(") - lines[j].count(")")
    return text


def resolve_name(name, lines, depth=0):
    """Find the integer value of a variable inside the same file.

    Handles three styles:
      KEY_BITS = 3072                    (constant)
      def make(key_size: int = 2048)     (function default)
      half = key_size // 2               (derived value, resolved recursively)
    Returns None when the value cannot be determined.
    """
    # Depth limit: stops endless loops such as a = b // 2 and b = a // 2.
    if depth > 3:
        return None
    # re.escape: the variable name is placed inside a regex as plain text.
    esc = re.escape(name)
    pat_const = re.compile(rf"^\s*{esc}\s*(?::\s*\w+)?\s*=\s*(\d+)\s*(?:#.*)?$")
    pat_default = re.compile(rf"\bdef\s+\w+\s*\(.*\b{esc}\s*(?::\s*\w+)?\s*=\s*(\d+)")
    pat_div = re.compile(rf"^\s*{esc}\s*=\s*(\w+)\s*//\s*(\d+)\s*(?:#.*)?$")
    # Pass 1: a direct value, either a constant or a function default.
    for ln in lines:
        m = pat_const.match(ln) or pat_default.search(ln)
        if m:
            return int(m.group(1))
    # Pass 2: a derived value like half = key_size // 2. It runs only when
    # pass 1 found nothing, so a direct value always wins. The base value is
    # resolved recursively (depth + 1).
    for ln in lines:
        m = pat_div.match(ln)
        if m:
            base = resolve_name(m.group(1), lines, depth + 1)
            if base is not None:
                return base // int(m.group(2))
    # None means "unknown": the scanner then reports no size instead of guessing.
    return None


def _plausible(v):
    """A real key size is a sane number of bits, not e.g. the exponent 65537."""
    return v is not None and MIN_BITS <= v <= MAX_BITS


def extract_key_info(lines, idx, match, pat):
    """Return {"key_size", "modulus_bits", "size_basis"} for one finding.

    Search order (first hit wins):
      1. (?P<bits>..) group of the pattern itself   e.g. RSA.generate(2048)
      2. keyword argument with a number              e.g. key_size=4096
      3. a variable, resolved inside the same file   e.g. getPrime(half)
    Non-keygen patterns return all None.
    """
    info = {"key_size": None, "modulus_bits": None, "size_basis": None}
    if not pat["keygen"]:
        return info

    stmt = call_statement(lines, idx, match.start())
    size = basis = None
    kind = "size"

    group = match.groupdict().get("bits")
    if group:
        size, basis = int(group), "literal in call"

    if size is None:
        for rx, k in KEYWORD_NUM:
            m = rx.search(stmt)
            if m:
                size, basis, kind = int(m.group(1)), "keyword argument", k
                break

    if size is None:
        m = KEYWORD_NAME.search(stmt)
        if m:
            name, kind = m.group(2), m.group(1)
        else:
            m = FIRST_ARG_NAME.search(stmt)
            name = m.group(1) if m else None
        if name:
            value = resolve_name(name, lines)
            if _plausible(value):
                size, basis = value, "resolved from '" + name + "'"

    if not _plausible(size):
        return info

    info["key_size"] = size
    info["size_basis"] = basis

    if pat["primitive"] in MODULUS_PRIMITIVES:
        if pat["id"] in PER_PRIME_IDS:
            info["modulus_bits"] = size * 2
            info["size_basis"] += " (per-prime, modulus = 2 x)"
        elif pat["id"] == "RSA-WRAPPER-CALL" and kind == "bits":
            # In the target repo generate_keypair(bits=N) builds two N-bit
            # primes. This is an ASSUMPTION: verify it against the definition.
            info["modulus_bits"] = size * 2
            info["size_basis"] += " (per-prime assumed, modulus = 2 x)"
        else:
            info["modulus_bits"] = size
    return info
