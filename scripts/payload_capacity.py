"""RSA ciphertext vs ML-KEM hybrid blob, and the smallest image that fits.

Usage: python scripts\payload_capacity.py --bits-per-pixel 3 [--overhead-bytes 4]
bits-per-pixel depends on the pinned project's embedding (check its code:
1 LSB on all of R, G, B = 3; R channel only = 1).
"""
import argparse
import math

p = argparse.ArgumentParser()
p.add_argument("--bits-per-pixel", type=int, required=True)
p.add_argument("--overhead-bytes", type=int, default=0, help="length header the project adds")
a = p.parse_args()

HYBRID_FIXED = 1088 + 12 + 16
print(f"{'message':>8} {'RSA-1024':>9} {'RSA-2048':>9} {'ML-KEM blob':>12} {'min image (blob)':>18}")
for msg in (16, 64, 256, 1024):
    rsa1024 = math.ceil((msg + 1) / 117) * 128 if msg else 128   # textbook chunks, rough
    rsa2048 = math.ceil((msg + 1) / 245) * 256 if msg else 256
    blob = HYBRID_FIXED + msg
    px = math.ceil((blob + a.overhead_bytes) * 8 / a.bits_per_pixel)
    side = math.ceil(math.sqrt(px))
    print(f"{msg:>8} {rsa1024:>9} {rsa2048:>9} {blob:>12} {side:>7}x{side:<10}")
print("Note: the RSA columns are estimates from block size; verify against the pinned code's real ciphertext length.")
