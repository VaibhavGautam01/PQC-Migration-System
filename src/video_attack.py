"""
video_attack.py - Key-free attack on the video stego (reduced RSA key).
The attacker never uses the secret frame-selection key: frames carrying
data are found by scanning for a plausible 16-bit length header.

Usage:
  python src/video_attack.py --project "<video project path>" --bits 96
"""
import argparse
import sys
import time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--project", required=True)
ap.add_argument("--bits", type=int, default=96)
args = ap.parse_args()

sys.path.insert(0, args.project)
import rsa_crypto as rc
from pipeline import embed_message
from xor_lsb import extract_bits_from_frame, bits_to_bytes
from sympy import factorint

SECRET_KEY = "Diu.2024"
MESSAGE = "HELLO"

# ---- Sender (simulated) ----
rng = np.random.default_rng()
frames = [rng.integers(0, 256, (90, 160, 3), dtype=np.uint8) for _ in range(300)]
_, pub_path = rc.generate_keypair(key_size=args.bits, out_dir="outputs/toykeys")
pub = rc.load_public_key(pub_path)
res = embed_message(frames, MESSAGE, SECRET_KEY, pub)
stego = res.stego_frames
print(f"[sender]   {pub['n'].bit_length()}-bit key, secret key '{SECRET_KEY}', "
      f"{len(res.selected_frames)} frames selected")

# ---- Attacker: stego frames + public key only ----
e, n = pub["e"], pub["n"]
n_bytes = (n.bit_length() + 7) // 8

cands = []
for i in range(min(256, len(stego))):
    hdr = extract_bits_from_frame(stego[i], 16)
    length = int("".join(map(str, hdr)), 2)
    if 1 <= length <= n_bytes:
        bits = extract_bits_from_frame(stego[i], length * 8, start=16)
        cands.append((i, bits_to_bytes(bits)[:length]))

chosen = cands
if sum(len(c[1]) for c in cands) != n_bytes:       # rare false-positive header
    for k in range(len(cands)):
        trial = cands[:k] + cands[k + 1:]
        if sum(len(c[1]) for c in trial) == n_bytes:
            chosen = trial
            break
total = sum(len(c[1]) for c in chosen)
if total != n_bytes:
    sys.exit(f"[attacker] could not assemble ciphertext ({total} of {n_bytes} bytes)")

print(f"[attacker] found data in frames {[c[0] for c in chosen]} without the key")
ciphertext = b"".join(c[1] for c in chosen)

t0 = time.time()
f = factorint(n)
p, q = sorted(f)
d = pow(e, -1, (p - 1) * (q - 1))
print(f"[attacker] factored n in {time.time() - t0:.2f}s")
print("[attacker] DECRYPTED:", rc.decrypt_message(ciphertext, {"d": d, "n": n}))