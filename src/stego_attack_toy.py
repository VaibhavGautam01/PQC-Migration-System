"""
stego_attack_toy.py - Toy-RSA version of the stego break (N = 15 or 21),
sized so Shor's algorithm can factor N on a simulator.

Each ASCII char is split into two base-N digits (each < N), each digit is
RSA-encrypted, and the results are hidden with the project's LSB routine.

Usage:
  python src/stego_attack_toy.py --project "<path>" --n 21
"""
import argparse
import os
import sys
from math import gcd
from pathlib import Path

from stego_attack_image import factor_n, hex_width  # swap factor_n for Shor later

TOY_PRIMES = {15: (3, 5), 21: (3, 7)}


def make_toy_keys(n):
    p, q = TOY_PRIMES[n]
    phi = (p - 1) * (q - 1)
    e = next(x for x in range(3, phi) if gcd(x, phi) == 1)
    d = pow(e, -1, phi)
    return (e, n), (d, n)


def encode(text, n):
    """char -> two base-n digits, all < n."""
    digits = []
    for ch in text:
        c = ord(ch)
        assert c < 128, "ASCII only"
        digits += [c // n, c % n]
    return digits


def decode(digits, n):
    return "".join(chr(digits[i] * n + digits[i + 1])
                   for i in range(0, len(digits), 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--n", type=int, default=21, choices=[15, 21])
    args = ap.parse_args()

    sys.path.insert(0, args.project)
    from lsb_stego import embed_lsb, extract_lsb
    from PIL import Image

    n = args.n
    out = Path("outputs")
    out.mkdir(exist_ok=True)
    cover, stego = str(out / "toy_cover.png"), str(out / "toy_stego.png")
    Image.frombytes("RGB", (200, 200), os.urandom(200 * 200 * 3)).save(cover)

    # Sender
    pub, priv = make_toy_keys(n)
    secret = "HELLO"
    w = hex_width(n)
    cipher = [pow(m, pub[0], n) for m in encode(secret, n)]
    embed_lsb(cover, "".join(format(c, f"0{w}x") for c in cipher), stego)
    print(f"[sender]   toy key e={pub[0]} N={n}; hid '{secret}' in {stego}")

    # Attacker: only the stego image and the public key
    hex_str = extract_lsb(stego)
    blocks = [int(hex_str[i:i + w], 16) for i in range(0, len(hex_str), w)]
    print(f"[attacker] extracted {len(blocks)} ciphertext blocks")
    p, q = factor_n(n)   # <-- Shor's circuit replaces this call
    d = pow(pub[0], -1, (p - 1) * (q - 1))
    text = decode([pow(c, d, n) for c in blocks], n)
    print(f"[attacker] factored N = {p} x {q}, recovered d = {d}")
    print(f"[attacker] DECRYPTED MESSAGE: {text}")
    print("BREAK SUCCESSFUL" if text == secret else "BREAK FAILED")


if __name__ == "__main__":
    main()