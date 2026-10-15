"""
migration_demo.py - show that the migration the advisor recommends really works.

The advisor tells a project to replace RSA with ML-KEM-768. This module runs
both side by side, with real code:

  1. Textbook RSA (what the two target projects use: no padding, small key)
       - encrypt the same message twice -> identical ciphertext (deterministic)
       - an attacker who only has the public key factors n and reads the message
  2. RSA-OAEP 2048 (the safe classical version, for comparison)
  3. ML-KEM-768 + AES-256-GCM (the post-quantum hybrid the CBOM recommends)
       - key encapsulation, then AES-GCM encrypts the message
       - a wrong private key gives a different secret and decryption fails

Honest limits:
  * The textbook-RSA attack here is CLASSICAL (Pollard's rho on a tiny modulus).
    Against a large modulus the same job is what Shor's algorithm does.
  * ML-KEM comes from the pure-Python library `kyber-py`. It is correct but
    educational: not constant-time and not fast. Use a vetted library such as
    liboqs or OpenSSL 3.5+ in production.

Run:  python notebook/migration_demo.py
Needs: pip install kyber-py cryptography
"""
import argparse
import secrets
import sys
import time
from math import gcd

try:
    from kyber_py.ml_kem import ML_KEM_768
except ImportError:                      # reported later, never a crash on import
    ML_KEM_768 = None

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:
    AESGCM = None

E = 65537
_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)

QUANTUM_RSA = "Broken by Shor's algorithm"
QUANTUM_MLKEM = "No known quantum attack (NIST FIPS 203)"


# ---------------------------------------------------------------- textbook RSA
def is_probable_prime(n, rounds=24):
    """Miller-Rabin primality test. Returns True if n is (very probably) prime."""
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def random_prime(bits):
    """Random prime with exactly `bits` bits."""
    if bits < 2:
        raise ValueError("bits must be at least 2")
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if is_probable_prime(candidate):
            return candidate


def textbook_keygen(bits):
    """Textbook RSA key with an n of exactly `bits` bits (bits >= 32).

    Returns a dict with n, e, d, p, q. No padding scheme is involved anywhere.
    """
    if bits < 32:
        raise ValueError("bits must be at least 32")
    while True:
        p = random_prime(bits // 2)
        q = random_prime(bits - bits // 2)
        if p == q:
            continue
        n = p * q
        if n.bit_length() != bits:
            continue
        phi = (p - 1) * (q - 1)
        if gcd(E, phi) != 1:
            continue
        return {"n": n, "e": E, "d": pow(E, -1, phi), "p": p, "q": q}


def textbook_encrypt(message, n, e):
    """Raw RSA: c = m^e mod n. `message` is bytes and must be smaller than n."""
    m = int.from_bytes(message, "big")
    if m >= n:
        raise ValueError("message does not fit under the modulus")
    return pow(m, e, n)


def textbook_decrypt(ciphertext, n, d, length):
    """Raw RSA decryption back to `length` bytes."""
    return pow(ciphertext, d, n).to_bytes(length, "big")


def pollard_rho(n, max_steps=20_000_000):
    """Find a non-trivial factor of n (classical attack, fine for small n)."""
    if n % 2 == 0:
        return 2
    while True:
        x = y = secrets.randbelow(n - 2) + 2
        c = secrets.randbelow(n - 1) + 1
        d, steps = 1, 0
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = gcd(abs(x - y), n)
            steps += 1
            if steps > max_steps:
                raise RuntimeError("modulus too large for this classical attack")
        if d != n:
            return d


def attack_textbook(n, e, ciphertext, length):
    """Attacker view: only (n, e) and the ciphertext. Returns plaintext and seconds."""
    t0 = time.perf_counter()
    p = pollard_rho(n)
    q = n // p
    d = pow(e, -1, (p - 1) * (q - 1))
    plaintext = textbook_decrypt(ciphertext, n, d, length)
    return {"plaintext": plaintext, "seconds": time.perf_counter() - t0, "p": p, "q": q}


# ------------------------------------------------------------------ the 3 demos
def _mean_time(fn, reps=3):
    """Run fn() `reps` times. Returns (last result, mean seconds)."""
    result, total = None, 0.0
    for _ in range(reps):
        t0 = time.perf_counter()
        result = fn()
        total += time.perf_counter() - t0
    return result, total / reps


def run_textbook(bits=64, message=b"PQC!"):
    """Textbook RSA with a small key: encrypt, show it is deterministic, then break it."""
    key, keygen_s = _mean_time(lambda: textbook_keygen(bits), reps=1)
    n, e, d = key["n"], key["e"], key["d"]
    c1, enc_s = _mean_time(lambda: textbook_encrypt(message, n, e))
    c2 = textbook_encrypt(message, n, e)
    recovered, dec_s = _mean_time(lambda: textbook_decrypt(c1, n, d, len(message)))
    attack = attack_textbook(n, e, c1, len(message))
    size = (bits + 7) // 8
    return {
        "name": f"Textbook RSA-{bits} (no padding)",
        "public_key_bytes": size + 3,
        "ciphertext_bytes": size,
        "keygen_s": keygen_s, "encrypt_s": enc_s, "decrypt_s": dec_s,
        "randomised": c1 != c2,
        "roundtrip_ok": recovered == message,
        "attack_seconds": attack["seconds"],
        "attack_recovered": attack["plaintext"] == message,
        "factors": (attack["p"], attack["q"]),
        "quantum": QUANTUM_RSA,
    }


def run_rsa_oaep(bits=2048, message=b"PQC!"):
    """RSA-OAEP: the safe classical RSA, for a fair size and speed comparison."""
    if AESGCM is None:
        raise RuntimeError("missing dependency: pip install cryptography")
    oaep = padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
    key, keygen_s = _mean_time(lambda: rsa.generate_private_key(E, bits), reps=1)
    pub = key.public_key()
    pub_bytes = pub.public_bytes(serialization.Encoding.DER,
                                 serialization.PublicFormat.SubjectPublicKeyInfo)
    c1, enc_s = _mean_time(lambda: pub.encrypt(message, oaep))
    c2 = pub.encrypt(message, oaep)
    recovered, dec_s = _mean_time(lambda: key.decrypt(c1, oaep))
    return {
        "name": f"RSA-OAEP-{bits}",
        "public_key_bytes": len(pub_bytes),
        "ciphertext_bytes": len(c1),
        "keygen_s": keygen_s, "encrypt_s": enc_s, "decrypt_s": dec_s,
        "randomised": c1 != c2,
        "roundtrip_ok": recovered == message,
        "quantum": QUANTUM_RSA,
    }


def run_ml_kem_hybrid(message=b"PQC!"):
    """ML-KEM-768 key encapsulation + AES-256-GCM, the hybrid the CBOM recommends."""
    if ML_KEM_768 is None:
        raise RuntimeError("missing dependency: pip install kyber-py")
    if AESGCM is None:
        raise RuntimeError("missing dependency: pip install cryptography")
    (ek, dk), keygen_s = _mean_time(ML_KEM_768.keygen)
    (secret, kem_ct), enc_s = _mean_time(lambda: ML_KEM_768.encaps(ek))
    nonce = secrets.token_bytes(12)
    blob = AESGCM(secret).encrypt(nonce, message, None)
    secret2, dec_s = _mean_time(lambda: ML_KEM_768.decaps(dk, kem_ct))
    recovered = AESGCM(secret2).decrypt(nonce, blob, None)
    # Wrong private key: ML-KEM rejects implicitly and returns an unrelated secret.
    _, wrong_dk = ML_KEM_768.keygen()
    wrong_secret = ML_KEM_768.decaps(wrong_dk, kem_ct)
    return {
        "name": "ML-KEM-768 + AES-256-GCM",
        "public_key_bytes": len(ek),
        "private_key_bytes": len(dk),
        "ciphertext_bytes": len(kem_ct) + len(nonce) + len(blob),
        "kem_ciphertext_bytes": len(kem_ct),
        "shared_secret_bytes": len(secret),
        "keygen_s": keygen_s, "encrypt_s": enc_s, "decrypt_s": dec_s,
        "randomised": True,
        "roundtrip_ok": recovered == message and secret == secret2,
        "wrong_key_secret_differs": wrong_secret != secret,
        "quantum": QUANTUM_MLKEM,
    }


def compare(message=b"PQC!", textbook_bits=64, rsa_bits=2048):
    """Run all three demos. A demo that cannot run reports {'error': reason}."""
    jobs = {"textbook": lambda: run_textbook(textbook_bits, message),
            "oaep": lambda: run_rsa_oaep(rsa_bits, message),
            "mlkem": lambda: run_ml_kem_hybrid(message)}
    out = {}
    for key, job in jobs.items():
        try:
            out[key] = job()
        except (RuntimeError, ValueError) as exc:
            out[key] = {"error": str(exc)}
    return out


# --------------------------------------------------------------------------- CLI
def _ms(seconds):
    """Seconds as a short millisecond string."""
    return f"{seconds * 1000:,.1f} ms"


def main(argv=None):
    """Print the comparison. Exit code 0 if every demo worked, 1 otherwise."""
    parser = argparse.ArgumentParser(description="RSA vs ML-KEM-768 migration demo")
    parser.add_argument("--message", default="PQC!", help="short ASCII message")
    parser.add_argument("--textbook-bits", type=int, default=64)
    parser.add_argument("--rsa-bits", type=int, default=2048)
    args = parser.parse_args(argv)

    res = compare(args.message.encode(), args.textbook_bits, args.rsa_bits)
    ok = True
    print(f"{'scheme':32} {'public key':>11} {'ciphertext':>11} {'keygen':>10} {'encrypt':>10} {'decrypt':>10}")
    for r in res.values():
        if "error" in r:
            ok = False
            print(f"  skipped: {r['error']}")
            continue
        ok = ok and r["roundtrip_ok"]
        print(f"{r['name']:32} {r['public_key_bytes']:>9} B {r['ciphertext_bytes']:>9} B "
              f"{_ms(r['keygen_s']):>10} {_ms(r['encrypt_s']):>10} {_ms(r['decrypt_s']):>10}")
    t = res.get("textbook", {})
    if "factors" in t:
        print(f"\nAttack on {t['name']}: attacker had only the public key.")
        print(f"  factored n in {_ms(t['attack_seconds'])}, read the message: {t['attack_recovered']}")
        print("  (classical attack on a tiny key; large keys fall to Shor's algorithm)")
    m = res.get("mlkem", {})
    if "wrong_key_secret_differs" in m:
        print("\nML-KEM-768: a wrong private key gives a different secret:",
              m["wrong_key_secret_differs"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
