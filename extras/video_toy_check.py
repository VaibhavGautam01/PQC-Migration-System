"""
video_toy_check.py - Reduced-size RSA test on the video project's rsa_crypto.
Encrypts with a small key, then breaks it using only the public key.

Usage:
  python src/video_toy_check.py --project "<video project path>" --bits 96
"""
import argparse
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--bits", type=int, default=96)
ap.add_argument("--msg", default="HELLO")
args = ap.parse_args()

sys.path.insert(0, args.project)
import rsa_crypto as rc
from sympy import factorint

_, pub_path = rc.generate_keypair(key_size=args.bits, out_dir="outputs/toykeys")
pub = rc.load_public_key(pub_path)
print(f"capacity at {args.bits} bits: {rc.rsa_key_capacity_bytes(pub)} bytes")

cipher = rc.encrypt_message(args.msg, pub)
e, n = pub["e"], pub["n"]

t0 = time.time()
f = factorint(n)
p, q = sorted(f)
d = pow(e, -1, (p - 1) * (q - 1))
print(f"factored n ({n.bit_length()} bits) in {time.time() - t0:.2f}s")
print("DECRYPTED:", rc.decrypt_message(cipher, {"d": d, "n": n}))