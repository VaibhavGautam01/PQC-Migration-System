"""
steganalysis_chi2.py - Chi-square test for LSB embedding.
Compares three images from the same photo:
  clean            : untouched photo
  random-bit stego : LSBs replaced with random bits (sanity check for the test)
  project stego    : the project's own embed_lsb with a hex payload
p near 1 -> pairs (2k, 2k+1) equalised -> likely embedded; p near 0 -> clean.

Usage:
  python src/steganalysis_chi2.py --project "<stego project>" --cover photo.png
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.stats import chi2


def chi_square_p(values):
    hist = np.bincount(values, minlength=256).astype(float)
    obs = hist[0::2]
    exp = (hist[0::2] + hist[1::2]) / 2
    keep = exp >= 5
    stat = np.sum((obs[keep] - exp[keep]) ** 2 / exp[keep])
    return float(chi2.sf(stat, keep.sum() - 1))


def p_of(path, limit=None):
    arr = np.array(Image.open(path).convert("RGB")).reshape(-1)
    if limit:
        arr = arr[:limit]
    return chi_square_p(arr)


def verdict(p):
    return "EMBEDDED" if p > 0.5 else "clean"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--cover", required=True)
    args = ap.parse_args()

    sys.path.insert(0, args.project)
    from lsb_stego import embed_lsb

    out = Path("outputs")
    out.mkdir(exist_ok=True)
    clean = str(out / "chi_cover.png")
    rand = str(out / "chi_random.png")
    stego = str(out / "chi_stego.png")

    img = Image.open(args.cover).convert("RGB")
    img.save(clean)
    arr = np.array(img)

    # Sanity check: replace every LSB with a random bit
    bits = np.random.randint(0, 2, arr.shape, dtype=np.uint8)
    Image.fromarray((arr & 0xFE) | bits).save(rand)

    # Project's own embedding with a hex payload, ~80% of capacity
    n_chars = (img.width * img.height * 3 // 8) * 8 // 10
    hex_str = "".join(np.random.choice(list("0123456789abcdef"), n_chars))
    embed_lsb(clean, hex_str, stego)

    print(f"clean image          p = {p_of(clean):.4f}  -> {verdict(p_of(clean))}")
    print(f"random-bit stego     p = {p_of(rand):.4f}  -> {verdict(p_of(rand))}")
    print(f"project stego (hex)  p = {p_of(stego):.4f}  -> {verdict(p_of(stego))}")
    # Only the part of the image the payload actually covers (row-major assumed)
    region = len(hex_str) * 8
    print(f"project stego, embedded region only p = {p_of(stego, region):.4f}")


if __name__ == "__main__":
    main()