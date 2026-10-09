"""
steganalysis_hex.py - Detector tailored to the project's hex-encoded LSB payload.
Test 1: fraction of ones in the LSB plane (random/natural ~ 0.5).
Test 2: does extract_lsb() return a clean hex string?

Usage:
  python src/steganalysis_hex.py --project "<stego project>" --image a.png [b.png ...]
"""
import argparse
import re
import sys

import numpy as np
from PIL import Image


def lsb_ones_fraction(path):
    arr = np.array(Image.open(path).convert("RGB")).reshape(-1)
    return float((arr & 1).mean())


def looks_like_hex(extract_lsb, path):
    try:
        s = extract_lsb(path)
    except Exception as e:
        return False, f"extract failed ({type(e).__name__})"
    if not s:
        return False, "empty"
    ok = re.fullmatch(r"[0-9a-f]+", s) is not None
    return ok, f"{len(s)} chars"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--image", nargs="+", required=True)
    args = ap.parse_args()

    sys.path.insert(0, args.project)
    from lsb_stego import extract_lsb

    for path in args.image:
        frac = lsb_ones_fraction(path)
        ok, info = looks_like_hex(extract_lsb, path)
        print(f"{path}\n  LSB ones fraction = {frac:.4f}\n"
              f"  extracts as clean hex: {ok} ({info})")


if __name__ == "__main__":
    main()