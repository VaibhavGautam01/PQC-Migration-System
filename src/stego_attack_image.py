"""
stego_attack_image.py - Break the RSA + LSB image stego:
extract ciphertext -> factor n -> recover d -> decrypt.
factor_n() is classical for now; Shor's replaces it later (Issue #9).

Usage:
  python src/stego_attack_image.py --project "<path to stego project>" --demo
"""
import argparse
import os
import sys
import time
from pathlib import Path


def factor_n(n):
    """Classical factoring (placeholder for Shor's)."""
    from sympy import factorint
    f = factorint(n)
    primes = sorted(f)
    if len(primes) != 2 or any(v != 1 for v in f.values()):
        raise ValueError("n is not a product of two distinct primes")
    return primes[0], primes[1]


def hex_width(n):
    return ((n.bit_length() + 7) // 8) * 2


def extract_ciphertext(stego_path, n, extract_lsb):
    """Pull the hex string out of the image and split it into cipher ints."""
    hex_str = extract_lsb(stego_path)
    w = hex_width(n)
    if len(hex_str) % w != 0:
        raise ValueError("Extracted data is not a whole number of blocks")
    return [int(hex_str[i:i + w], 16) for i in range(0, len(hex_str), w)]


def break_rsa(pub, cipher_ints):
    """Factor n, rebuild d, decrypt. Uses only PUBLIC information."""
    e, n = pub
    t0 = time.time()
    p, q = factor_n(n)
    elapsed = time.time() - t0
    phi = (p - 1) * (q - 1)
    d = pow(e, -1, phi)
    text = "".join(chr(pow(c, d, n)) for c in cipher_ints)
    return text, p, q, d, elapsed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="path to stego project")
    ap.add_argument("--demo", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, args.project)
    from rsa_utils import generate_keypair
    from rsa_lsb_stego import rsa_lsb_embed
    from lsb_stego import extract_lsb
    from PIL import Image

    out = Path("outputs")
    out.mkdir(exist_ok=True)
    cover = str(out / "demo_cover.png")
    stego = str(out / "demo_stego.png")

    # 1. Sender side (simulated)
    Image.frombytes("RGB", (200, 200), os.urandom(200 * 200 * 3)).save(cover)
    pub, priv = generate_keypair()
    secret = "HELLO QUANTUM"
    rsa_lsb_embed(cover, secret, stego, pub)
    print(f"[sender]   public key  e={pub[0]}  n={pub[1]} ({pub[1].bit_length()} bits)")
    print(f"[sender]   hid secret in {stego}")

    # 2. Attacker side: uses ONLY the stego image and the public key
    cipher_ints = extract_ciphertext(stego, pub[1], extract_lsb)
    print(f"[attacker] extracted {len(cipher_ints)} ciphertext blocks")
    text, p, q, d, elapsed = break_rsa(pub, cipher_ints)
    print(f"[attacker] factored n = {p} x {q} in {elapsed:.4f}s")
    print(f"[attacker] recovered d = {d}")
    print(f"[attacker] DECRYPTED MESSAGE: {text}")
    print("BREAK SUCCESSFUL" if text == secret else "BREAK FAILED")


if __name__ == "__main__":
    main()