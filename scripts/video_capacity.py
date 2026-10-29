"""Capacity of N frames vs the hybrid payload, with and without an ML-DSA-65 signature.

Usage: python scripts\video_capacity.py --width 640 --height 480 --bits-per-pixel 1 --frames 60
Take bits-per-pixel and header bytes from pqc_stego/video_pqc.py, not from guesswork.
"""
import argparse

from pqc_stego import hybrid

OVERHEAD = hybrid.OVERHEAD      # KEM ciphertext + nonce + tag, from the real module
SIG = 3309                      # ML-DSA-65 signature

p = argparse.ArgumentParser()
p.add_argument("--width", type=int, required=True)
p.add_argument("--height", type=int, required=True)
p.add_argument("--bits-per-pixel", type=int, required=True)
p.add_argument("--frames", type=int, default=60)
p.add_argument("--header-bytes", type=int, default=0, help="length header the embedder adds")
a = p.parse_args()

per_frame = a.width * a.height * a.bits_per_pixel // 8
total = per_frame * a.frames - a.header_bytes
print(f"per frame {per_frame} B, {a.frames} frames {total} B usable (hybrid overhead {OVERHEAD} B, signature {SIG} B)")
for msg in (16, 256, 1024, 4096):
    for label, size in (("hybrid", OVERHEAD + msg), ("hybrid+ML-DSA-65", OVERHEAD + msg + SIG)):
        frames_needed = -(-(size + a.header_bytes) // per_frame)
        print(f"msg {msg:>5} B  {label:<18} blob {size:>6} B  frames {frames_needed:>3}  fits: {size <= total}")
