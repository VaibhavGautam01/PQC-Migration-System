"""
stego_attack_toy.py - Toy-RSA version of the stego break (N = 15 or 21),
sized so Shor's algorithm can factor N on a simulator.

Each ASCII char is split into two base-N digits (each < N), each digit is
RSA-encrypted, and the results are hidden with the project's LSB routine.

Usage (from the project root, venv active):
  python extras/stego_attack_toy.py --project "data/targets/final-year-part1" --n 21
  python extras/stego_attack_toy.py --project "data/targets/final-year-part1" --n 15 --shor
  python extras/stego_attack_toy.py --project "data/targets/final-year-part1" --n 35 --shor --save-evidence

--shor           the attacker factors N with the Q1 quantum circuit (Aer simulator, toy size)
                 instead of classical code. Only the public N is given to the circuit.
--save-evidence  append the circuit run records to data/quantum_runs.json (rule 4)
"""
import argparse
import os
import sys
from math import gcd
from pathlib import Path

# make "from src import ..." work when this script is started from any folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from stego_attack_image import factor_n, hex_width  # classical factoring, kept as the default

TOY_PRIMES = {15: (3, 5), 21: (3, 7), 35: (5, 7)}


def make_toy_keys(n):
    """Return (public, private) toy RSA keys for N = 15 or 21."""
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
    """Rebuild text from base-N digit pairs."""
    return "".join(chr(digits[i] * n + digits[i + 1])
                   for i in range(0, len(digits), 2))


def main():
    """Run the toy-RSA stego attack for N = 15 or 21."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--n", type=int, default=21, choices=[15, 21, 35])
    ap.add_argument("--shor", action="store_true",
                    help="factor N with the Q1 quantum circuit (Aer simulator, toy size)")
    ap.add_argument("--save-evidence", action="store_true",
                    help="with --shor: append the circuit run records to data/quantum_runs.json")
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
    if args.shor:
        # The attacker gives ONLY the public modulus n to the quantum circuit.
        from src.q1_factor import quantum_factor
        result = quantum_factor(n)
        if result["factors"] is None:
            print("[attacker] Shor circuit did not find factors; attempts:", result["attempts"])
            print("BREAK FAILED")
            return
        p, q = result["factors"]
        print(f"[attacker] Aer simulator, toy size: {result['method']}, base a={result['a']}, "
              f"measured period r={result['period']}, attempts={len(result['attempts'])}")
        if args.save_evidence:
            from src import quantum_runs as QR
            for rec in result["records"]:
                QR.append_run(rec)
            print(f"[attacker] saved {len(result['records'])} evidence record(s) to {QR.RUNS_PATH}")
    else:
        p, q = factor_n(n)   # classical factoring (default); use --shor for the quantum circuit
    d = pow(pub[0], -1, (p - 1) * (q - 1))
    text = decode([pow(c, d, n) for c in blocks], n)
    print(f"[attacker] factored N = {p} x {q}, recovered d = {d}")
    print(f"[attacker] DECRYPTED MESSAGE: {text}")
    print("BREAK SUCCESSFUL" if text == secret else "BREAK FAILED")


if __name__ == "__main__":
    main()