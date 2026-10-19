"""
hybrid_review.py
----------------
Security-review helper for the hybrid ML-KEM-768 + AES-256-GCM module
(pqc_stego/hybrid.py, written by Uday). Week 2 Day 4.

  python src/hybrid_review.py                  # finds pqc_stego/hybrid.py
  python src/hybrid_review.py path/to/hybrid.py

Two parts:
  STATIC   a heuristic scan of the source (patterns that are usually mistakes).
           It finds obvious problems only; it does not prove the code is safe.
  DYNAMIC  runs the module: sizes, payload layout, fresh nonces, tamper
           detection, wrong key, truncated input, error messages.

Assumed payload layout (plan section 6): KEM ciphertext (1088 B) + nonce (12 B)
+ tag (16 B) + AES ciphertext. If Uday's layout differs, change LAYOUT below
and say so in the review.

Prints a Markdown table to paste into docs/hybrid_security_review.md.
Library caveat: kyber-py is educational and not hardened against timing attacks.
"""
import importlib
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ML-KEM-768 sizes (FIPS 203): verify against the standard's parameter table.
PK_LEN, SK_LEN, KEM_CT_LEN, SS_LEN = 1184, 2400, 1088, 32
NONCE_LEN, TAG_LEN = 12, 16
OVERHEAD = KEM_CT_LEN + NONCE_LEN + TAG_LEN
LAYOUT = {"kem_ct": (0, KEM_CT_LEN),
          "nonce": (KEM_CT_LEN, KEM_CT_LEN + NONCE_LEN),
          "tag": (KEM_CT_LEN + NONCE_LEN, OVERHEAD)}


# ---------------------------------------------------------------- static
STATIC_RULES = [
    # id, severity, regex, message
    ("S1", "FAIL", r"^\s*(import random\b|from random\b)|\brandom\.(random|randint|choice|randbytes|getrandbits)\(",
     "uses the `random` module; keys and nonces must come from os.urandom or get_random_bytes"),
    ("S2", "FAIL", r"MODE_(ECB|CBC|CFB|OFB|CTR)\b", "AES mode other than GCM"),
    ("S3", "FAIL", r"\b(nonce|iv|key)\s*=\s*b['\"]|\b(nonce|iv|key)\s*=\s*b['\"]\\x00['\"]\s*\*|\bbytes\(\s*(12|16|32)\s*\)",
     "hard-coded or all-zero key/nonce/IV"),
    ("S4", "FAIL", r"AES\.new\(\s*(ss|shared|shared_secret|secret|K)\b",
     "shared secret used directly as the AES key (plan: HKDF in between)"),
    ("S5", "WARN", r"^\s*assert\b", "assert used outside tests: removed when Python runs with -O, so never use it for security checks"),
    ("S6", "WARN", r"^\s*except\s*:|^\s*except\s+Exception\s*:", "broad except: check it cannot swallow a failed authentication"),
    ("S7", "FAIL", r"(print|logging\.\w+|logger\.\w+)\(.*\b(key|secret|ss|sk|shared|nonce|plaintext)\b",
     "prints or logs key material or plaintext"),
    ("S8", "WARN", r"\.decrypt\(", "uses .decrypt(): confirm the tag is verified (decrypt_and_verify or verify) before any plaintext is used"),
]


def static_findings(source: str) -> list:
    """Heuristic scan. Returns a list of {id, severity, line, text, message}."""
    out = []
    lines = source.splitlines()
    for rid, sev, pattern, msg in STATIC_RULES:
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("#"):
                continue
            if re.search(pattern, line):
                if rid == "S8" and re.search(r"verify", source):
                    continue
                out.append({"id": rid, "severity": sev, "line": i, "text": line.strip(), "message": msg})
    # whole-file checks
    if not re.search(r"HKDF|hkdf", source):
        out.append({"id": "S9", "severity": "FAIL", "line": 0, "text": "",
                    "message": "no HKDF found between the KEM shared secret and the AES key"})
    elif not re.search(r"info\s*=|HKDF\([^)]*,[^)]*,[^)]*b['\"]", source):
        out.append({"id": "S9", "severity": "WARN", "line": 0, "text": "",
                    "message": "HKDF found but no `info` string: add a fixed domain-separation string"})
    if not re.search(r"MODE_GCM", source):
        out.append({"id": "S10", "severity": "WARN", "line": 0, "text": "", "message": "MODE_GCM not found"})
    if not re.search(r"urandom|get_random_bytes", source):
        out.append({"id": "S11", "severity": "WARN", "line": 0, "text": "",
                    "message": "no explicit os.urandom / get_random_bytes: check where the nonce comes from"})
    if re.search(r"ML_KEM_(512|1024)\b|kyber(512|1024)", source, re.I):
        out.append({"id": "S12", "severity": "WARN", "line": 0, "text": "", "message": "a parameter set other than ML-KEM-768 is mentioned"})
    if not re.search(r"\.update\(", source):
        out.append({"id": "S13", "severity": "INFO", "line": 0, "text": "",
                    "message": "no AAD: binding the version and KEM ciphertext as associated data is recommended"})
    return out


# --------------------------------------------------------------- dynamic
@dataclass
class Adapter:
    keygen: callable      # () -> (public_key: bytes, secret_key: bytes)
    encrypt: callable     # (public_key, message: bytes) -> blob: bytes
    decrypt: callable     # (secret_key, blob: bytes) -> message: bytes


NAMES = {"keygen": ("generate_keypair", "keygen", "kem_keygen", "generate_keys", "keypair"),
         "encrypt": ("hybrid_encrypt", "encrypt"),
         "decrypt": ("hybrid_decrypt", "decrypt")}


def auto_adapter(module):
    """Find keygen/encrypt/decrypt by common names. Edit here if Uday's names differ."""
    found = {}
    for role, cands in NAMES.items():
        for n in cands:
            if callable(getattr(module, n, None)):
                found[role] = getattr(module, n)
                break
    return Adapter(**found) if len(found) == 3 else None


def _flip(blob: bytes, pos: int) -> bytes:
    b = bytearray(blob)
    b[pos] ^= 0x01
    return bytes(b)


def _fails(adapter, sk, blob):
    """(raised, exception_type_name, message)"""
    try:
        adapter.decrypt(sk, blob)
        return False, None, None
    except Exception as e:  # noqa: BLE001
        return True, type(e).__name__, str(e)


def dynamic_checks(adapter: Adapter, n_nonces: int = 100) -> list:
    res = []

    def add(rid, ok, text, severity="FAIL"):
        res.append({"id": rid, "status": "PASS" if ok else severity, "text": text})

    pk, sk = adapter.keygen()
    if isinstance(pk, (bytes, bytearray)) and isinstance(sk, (bytes, bytearray)):
        add("D1", len(pk) == PK_LEN and len(sk) == SK_LEN,
            f"key sizes: public {len(pk)} B (expect {PK_LEN}), secret {len(sk)} B (expect {SK_LEN})")
    else:
        add("D1", False, "keygen did not return (bytes, bytes): adapt the adapter", "WARN")

    ok = True
    for n in (0, 1, 16, 1000):
        m = os.urandom(n)
        try:
            ok &= adapter.decrypt(sk, adapter.encrypt(pk, m)) == m
        except Exception:  # noqa: BLE001
            ok = False
    add("D2", ok, "round trip for message lengths 0, 1, 16 and 1000")

    m = b"overhead check message"
    blob = adapter.encrypt(pk, m)
    add("D3", len(blob) == OVERHEAD + len(m),
        f"payload = {len(blob)} B for a {len(m)} B message (expect {OVERHEAD + len(m)} = {KEM_CT_LEN} + {NONCE_LEN} + {TAG_LEN} + message)")

    blobs = [adapter.encrypt(pk, m) for _ in range(n_nonces)]
    nonces = {b[LAYOUT["nonce"][0]:LAYOUT["nonce"][1]] for b in blobs}
    cts = {b[:KEM_CT_LEN] for b in blobs}
    add("D4", len(nonces) == n_nonces, f"{len(nonces)} distinct nonces in {n_nonces} encryptions (expect all distinct)")
    add("D5", len(cts) == n_nonces, f"{len(cts)} distinct KEM ciphertexts in {n_nonces} encryptions (fresh encapsulation each time)")
    add("D6", len({b for b in blobs}) == n_nonces, "every payload differs for the same message")

    msgs = {}
    base = adapter.encrypt(pk, b"A secret message that is long enough to flip bytes in")
    regions = {"KEM ciphertext (first byte)": 0, "KEM ciphertext (middle)": KEM_CT_LEN // 2,
               "KEM ciphertext (last byte)": KEM_CT_LEN - 1, "nonce": LAYOUT["nonce"][0] + 3,
               "tag": LAYOUT["tag"][0] + 5, "AES ciphertext": OVERHEAD + 2, "AES ciphertext (last)": len(base) - 1}
    bad = []
    for name, pos in regions.items():
        raised, etype, msg = _fails(adapter, sk, _flip(base, pos))
        msgs[name] = (etype, msg)
        if not raised:
            bad.append(name)
    add("D7", not bad, "a one-bit change is rejected in every region" + (f"; NOT rejected: {bad}" if bad else ""))

    uniform = len({v for v in msgs.values()}) == 1
    add("D8", uniform, "tamper errors look identical in every region (no hint about which part failed)"
        + ("" if uniform else f"; seen: {sorted({str(v) for v in msgs.values()})[:3]}"), "WARN")

    _, sk2 = adapter.keygen()
    raised, _, _ = _fails(adapter, sk2, base)
    add("D9", raised, "decrypting with a different secret key fails")

    bad_t, types = [], set()
    for n in (0, 10, KEM_CT_LEN, OVERHEAD - 1):
        raised, etype, _ = _fails(adapter, sk, base[:n])
        if not raised:
            bad_t.append(n)
        types.add(etype)
    add("D10", not bad_t, "truncated payloads (0, 10, 1088, 1115 bytes) are rejected"
        + (f"; NOT rejected at {bad_t}" if bad_t else ""))
    sloppy = types & {"IndexError", "KeyError", "TypeError", "AttributeError", "struct.error", "error"}
    add("D11", not sloppy, f"truncated payloads raise a clean error (seen: {sorted(t for t in types if t)})"
        + (f"; internal error types leak: {sorted(sloppy)}" if sloppy else ""), "WARN")
    return res


# ---------------------------------------------------------------- output
def markdown(static, dynamic) -> str:
    rows = ["| ID | Result | Detail |", "|---|---|---|"]
    for d in dynamic:
        rows.append(f"| {d['id']} | {d['status']} | {d['text']} |")
    if not static:
        rows.append("| S* | PASS | no static findings |")
    for f in static:
        where = f"line {f['line']}: `{f['text'][:60]}`" if f["line"] else "whole file"
        rows.append(f"| {f['id']} | {f['severity']} | {f['message']} ({where}) |")
    return "\n".join(rows)


def main(path=None):
    path = Path(path) if path else ROOT / "pqc_stego" / "hybrid.py"
    if not path.exists():
        sys.exit(f"{path} not found. Merge Uday's branch first (git fetch, git merge origin/main).")
    static = static_findings(path.read_text(encoding="utf-8"))
    dynamic = []
    sys.path.insert(0, str(ROOT))
    try:
        mod = importlib.import_module("pqc_stego." + path.stem)
        ad = auto_adapter(mod)
        if ad is None:
            print("Dynamic checks skipped: could not find keygen/encrypt/decrypt. Edit NAMES or auto_adapter().")
        else:
            dynamic = dynamic_checks(ad)
    except Exception as e:  # noqa: BLE001
        print(f"Dynamic checks skipped: could not import the module ({type(e).__name__}: {e})")
    print(markdown(static, dynamic))
    fails = [d for d in dynamic if d["status"] == "FAIL"] + [f for f in static if f["severity"] == "FAIL"]
    print(f"\n{len(fails)} FAIL item(s).")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))