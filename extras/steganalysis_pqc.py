"""
steganalysis_pqc.py - is the PQC payload easier to detect than the RSA payload? (Week 2 Day 4)

THE QUESTION
------------
Replacing textbook RSA by ML-KEM-768 + AES-256-GCM changes the size of what is hidden:
  * textbook RSA hides ONE ciphertext block per message character: with a 1024-bit modulus
    that is 128 bytes (256 hex characters) per character, so the payload grows with the message
  * the hybrid blob has a FIXED overhead of 1116 bytes (KEM ciphertext 1088 + nonce 12 + tag 16)
    plus one byte per message character
So for short messages the PQC payload is larger, for long messages it can be SMALLER. This script
MEASURES it instead of assuming either way (risk table in the plan: report the result honestly).

WHAT IT MEASURES for a clean cover, an RSA payload and a PQC payload in the same cover
--------------------------------------------------------------------------------------
  payload size            bytes, bits, and share of the cover's capacity
  LSB ones fraction       share of 1s in the least-significant-bit plane (random data ~ 0.5)
                          for the whole image and for the embedded region only
  chi-square pair test    p near 1 means pixel-value pairs (2k, 2k+1) are equalised, which is what
                          LSB replacement does. The repo's rule (steganalysis_chi2.py) flags
                          p > 0.5. Reported for the whole image and the embedded region only
  header scan             can a detector see a recognisable structure at the fixed start of
                          the LSB stream? (a clean hex string, or a plausible length header)

PAYLOADS COMPARED (same cover, same message)
  RSA hex       textbook RSA ciphertext blocks as a hex string, as the image project hides them
  PQC hex       the hybrid blob as a hex string, hidden the same way
  PQC raw       the hybrid blob as raw bytes behind a 4-byte length header (pqc_stego format)

Usage (from the project root, venv active):
  python extras/steganalysis_pqc.py                          # synthetic cover, reference embedder
  python extras/steganalysis_pqc.py --cover photo.png        # RECOMMENDED: a real photo
  python extras/steganalysis_pqc.py --project data/targets/final-year-part1 --cover photo.png
                                                             # RSA/PQC hex use the pinned embed_lsb
  python extras/steganalysis_pqc.py --lengths 5 40 200 --rsa-bits 1024

HONEST LIMITS
-------------
* The default synthetic cover is NOT a photograph, so its chi-square numbers are only a
  demonstration. Use a real photo for the numbers you put in the report.
* The reference embedder is not the pinned project's code unless --project is given; the
  output says which one ran.
* These are simple detectors, not state-of-the-art steganalysis. A "not flagged" result does
  not mean the payload is undetectable.
"""
import argparse
import json
import re
import secrets
import struct
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pqc_stego import hybrid                                # noqa: E402
from src import shor_post as SP                             # noqa: E402  (chi-square p-value)

HEX_RE = re.compile(rb"[0-9a-f]+")
RULE_P = 0.5                                                # the repo's "EMBEDDED" threshold


# ------------------------------------------------------------------ textbook RSA payload
def _is_probable_prime(n, rounds=24):
    """Miller-Rabin primality test (enough for generating a demo key)."""
    if n < 4:
        return n in (2, 3)
    if n % 2 == 0:
        return False
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for _ in range(rounds):
        x = pow(secrets.randbelow(n - 3) + 2, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _random_prime(bits):
    while True:
        candidate = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(candidate):
            return candidate


def make_textbook_rsa(bits):
    """Return (n, e, d) for a demo RSA key of `bits` bits. DEMO ONLY, not for real use."""
    e = 65537
    while True:
        p, q = _random_prime(bits // 2), _random_prime(bits // 2)
        phi = (p - 1) * (q - 1)
        if p != q and phi % e != 0:
            return p * q, e, pow(e, -1, phi)


def rsa_hex_payload(message: bytes, n: int, e: int) -> str:
    """One textbook-RSA block per character, written as fixed-width hex (the project's style)."""
    width = (n.bit_length() + 3) // 4
    return "".join(format(pow(c, e, n), f"0{width}x") for c in message)


# ------------------------------------------------------------------ embedding (reference)
def embed_bytes(cover_flat: np.ndarray, data: bytes) -> np.ndarray:
    """Reference LSB embedding: bit i of `data` (MSB first) replaces the LSB of pixel byte i."""
    bits = np.unpackbits(np.frombuffer(data, dtype=np.uint8))
    if bits.size > cover_flat.size:
        raise ValueError("payload does not fit in the cover")
    out = cover_flat.copy()
    out[:bits.size] = (out[:bits.size] & 0xFE) | bits
    return out


def lsb_stream_bytes(flat: np.ndarray, nbytes: int) -> bytes:
    """Read `nbytes` bytes back from the start of the LSB plane (1 bit per pixel byte, MSB first)."""
    return np.packbits(flat[:nbytes * 8] & 1).tobytes()


# ------------------------------------------------------------------ the detectors
def ones_fraction(values: np.ndarray) -> float:
    """Share of 1s in the least significant bit of the given pixel bytes."""
    return float((values & 1).mean())


def chi_square_pair_p(values: np.ndarray) -> float:
    """Chi-square p-value that pixel-value pairs (2k, 2k+1) are equalised (same idea as
    steganalysis_chi2.py). Near 1 = looks like LSB replacement; near 0 = looks untouched."""
    hist = np.bincount(values, minlength=256).astype(float)
    obs = hist[0::2]
    exp = (hist[0::2] + hist[1::2]) / 2
    keep = exp >= 5
    if keep.sum() < 2:
        return float("nan")
    stat = float(np.sum((obs[keep] - exp[keep]) ** 2 / exp[keep]))
    return SP.chi2_sf(stat, int(keep.sum()) - 1)


def hex_header_found(flat: np.ndarray, nchars: int = 64) -> bool:
    """Does the start of the LSB stream read as a clean hex string? (a tell-tale of hex payloads)"""
    return HEX_RE.fullmatch(lsb_stream_bytes(flat, nchars)) is not None


def length_header_plausible(flat: np.ndarray) -> bool:
    """Does the start of the LSB stream look like the pqc_stego length header (1116 <= n <= capacity)?"""
    (length,) = struct.unpack(">I", lsb_stream_bytes(flat, 4))
    return hybrid.OVERHEAD <= length <= flat.size // 8 - 4


def analyse(flat: np.ndarray, region_bytes: int, capacity_bytes: int, payload_bytes: int = 0) -> dict:
    """All detector numbers for one image. `region_bytes` = pixel bytes the payload covers."""
    region = flat[:region_bytes] if region_bytes else flat
    p_all, p_region = chi_square_pair_p(flat), chi_square_pair_p(region)
    return {
        "payload_bytes": payload_bytes,
        "capacity_used": round(payload_bytes * 8 / flat.size, 4) if payload_bytes else 0.0,
        "ones_whole": round(ones_fraction(flat), 4),
        "ones_region": round(ones_fraction(region), 4),
        "chi_p_whole": None if np.isnan(p_all) else round(p_all, 4),
        "chi_p_region": None if np.isnan(p_region) else round(p_region, 4),
        "flagged_region": bool(p_region > RULE_P) if not np.isnan(p_region) else False,
        "hex_header_found": hex_header_found(flat),
        "length_header_found": length_header_plausible(flat),
    }


# ------------------------------------------------------------------ cover images
def synthetic_cover(size, seed=5):
    """A smooth, photo-LIKE image (gradients, waves, mild noise). Not a real photograph."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size]
    base = np.stack([
        110 + 90 * np.sin(x / 61.0) * np.cos(y / 83.0),
        120 + 80 * np.sin((x + y) / 97.0),
        100 + 100 * np.cos(x / 71.0 + y / 59.0)], axis=-1)
    return np.clip(base + rng.normal(0, 3.0, base.shape), 0, 255).astype(np.uint8)


def load_cover(path, size):
    if path:
        img = Image.open(path).convert("RGB")
        if min(img.size) < size:
            img = img.resize((size, size))
        img = img.crop((0, 0, size, size))
        return np.array(img)
    return synthetic_cover(size)


# ------------------------------------------------------------------ pinned embedder (optional)
def pinned_embed(project_dir, cover_png, hex_str, out_png):
    sys.path.insert(0, str(project_dir))
    from lsb_stego import embed_lsb                         # the pinned project's function
    embed_lsb(str(cover_png), hex_str, str(out_png))


# ------------------------------------------------------------------ the experiment
def run_experiment(cover, lengths, rsa_bits, project=None):
    flat_cover = cover.reshape(-1)
    capacity = flat_cover.size // 8
    n, e, _ = make_textbook_rsa(rsa_bits)
    public_key, _ = hybrid.generate_keypair()
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        cover_png = Path(tmp) / "cover.png"
        Image.fromarray(cover).save(cover_png)
        largest = 0
        payloads = []
        for length in lengths:
            msg = (b"The quick brown fox jumps over the lazy dog. " * 10)[:length]
            hex_rsa = rsa_hex_payload(msg, n, e)
            blob = hybrid.hybrid_encrypt(public_key, msg)
            payloads.append((length, "RSA hex", hex_rsa.encode()))
            payloads.append((length, "PQC hex", blob.hex().encode()))
            payloads.append((length, "PQC raw", struct.pack(">I", len(blob)) + blob))
            largest = max(largest, len(hex_rsa), 2 * len(blob), len(blob) + 4)
        # baseline: the untouched cover, region = the largest payload's region
        rows.append({"message_chars": 0, "payload": "clean cover",
                     **analyse(flat_cover, 8 * largest, capacity)})
        for length, kind, data in payloads:
            region = 8 * len(data)
            if len(data) > capacity:
                rows.append({"message_chars": length, "payload": kind, "payload_bytes": len(data),
                             "note": "does not fit in this cover"})
                continue
            if project and kind != "PQC raw":
                out_png = Path(tmp) / "pinned_stego.png"
                pinned_embed(project, cover_png, data.decode(), out_png)
                stego = np.array(Image.open(out_png).convert("RGB")).reshape(-1)
            else:
                stego = embed_bytes(flat_cover, data)
            rows.append({"message_chars": length, "payload": kind,
                         **analyse(stego, region, capacity, len(data))})
    return rows, {"rsa_bits": rsa_bits, "cover_bytes": int(flat_cover.size),
                  "capacity_bytes": capacity}


def crossover_length(rsa_bits):
    """Message length (chars) above which the PQC raw payload is smaller than textbook RSA's."""
    rsa_block = (rsa_bits + 7) // 8                         # bytes of RSA ciphertext per character
    # RSA: rsa_block * L bytes; PQC raw: 4 + OVERHEAD + L bytes
    return (4 + hybrid.OVERHEAD) / (rsa_block - 1)


def to_markdown(rows, meta, embedder, cover_name):
    lines = [f"Steganalysis: RSA payload vs PQC payload | embedder: {embedder} | cover: {cover_name} "
             f"| rsa bits: {meta['rsa_bits']} | capacity {meta['capacity_bytes']} B", "",
             "| msg chars | payload | bytes | cap used | ones whole | ones region | chi p whole | "
             "chi p region | flagged (p>0.5) | hex header | length header |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if "note" in r:
            lines.append(f"| {r['message_chars']} | {r['payload']} | {r['payload_bytes']} | "
                         f"{r['note']} |||||||")
            continue
        lines.append(f"| {r['message_chars'] or '-'} | {r['payload']} | {r['payload_bytes'] or '-'} | "
                     f"{r['capacity_used']:.1%} | {r['ones_whole']} | {r['ones_region']} | "
                     f"{r['chi_p_whole']} | {r['chi_p_region']} | {r['flagged_region']} | "
                     f"{r['hex_header_found']} | {r['length_header_found']} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cover", help="cover photo (recommended); default is a synthetic image")
    ap.add_argument("--size", type=int, default=512, help="cover side in pixels")
    ap.add_argument("--lengths", type=int, nargs="+", default=[5, 40, 200], help="message lengths")
    ap.add_argument("--rsa-bits", type=int, default=1024)
    ap.add_argument("--project", help="pinned image project folder: RSA/PQC hex use its embed_lsb")
    ap.add_argument("--out", default="outputs/steganalysis_pqc_image", help="output path prefix")
    args = ap.parse_args()

    cover = load_cover(args.cover, args.size)
    embedder = (f"pinned:{Path(args.project).name}/lsb_stego.py (hex rows), reference (PQC raw)"
                if args.project else "reference LSB, ASCII-hex or raw bytes, 1 bit per pixel byte")
    cover_name = args.cover or "SYNTHETIC (not a real photo: use --cover for report numbers)"
    rows, meta = run_experiment(cover, args.lengths, args.rsa_bits, args.project)

    text = to_markdown(rows, meta, embedder, cover_name)
    print(text)
    cross = crossover_length(args.rsa_bits)
    print(f"Size note: textbook RSA-{args.rsa_bits} hides {(args.rsa_bits + 7) // 8} bytes per message "
          f"character; the PQC blob adds a fixed {hybrid.OVERHEAD + 4} bytes. The PQC raw payload is "
          f"smaller than the RSA payload for messages longer than about {cross:.0f} characters.")
    print("Reading the table: compare 'clean cover' with the payload rows. A row is only "
          "'detectable' if the numbers move away from the clean row.")
    if not args.cover:
        print("WARNING: synthetic cover. Re-run with --cover <photo.png> before quoting numbers.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".md").write_text(text, encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(
        {"embedder": embedder, "cover": cover_name, "meta": meta, "rows": rows}, indent=2) + "\n",
        encoding="utf-8")
    print(f"wrote {out.with_suffix('.md')} and {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
