"""
attack_pqc_image.py - attack the PQC image variant (Week 2 Day 3).

THE SETUP
---------
The image project used to hide an RSA-encrypted message with LSB embedding. The PQC variant
(pqc_stego/image_pqc.py) hides a hybrid blob instead:
        ML-KEM-768 ciphertext (1088 B) | nonce (12 B) | GCM tag (16 B) | AES-256-GCM ciphertext
The attacker has what a real attacker would have: the stego image and the receiver's PUBLIC
key. No secret.

WHAT THIS SCRIPT SHOWS (each line is a check that must come out as expected)
-----------------------------------------------------------------------------
EXTRACTION STILL WORKS      LSB embedding is keyless, so anyone can pull the blob out. The
                            hiding layer did not get stronger; only the encryption did.
NOTHING TO FACTOR           The old break needed an integer modulus N = p * q. An ML-KEM public
                            key is 1184 bytes of lattice data, so Shor-style factoring has no
                            input here (by construction, not a measured attack).
NOTHING READABLE            The plaintext does not appear in the blob.
WRONG KEY FAILS             Decrypting with another receiver's secret key raises an error.
TAMPERING FAILS LOUDLY      Flipping one payload bit (KEM ciphertext, nonce, tag, AES part)
                            or the length header makes decryption fail; it never returns
                            a wrong message silently. This is the AES-GCM tag at work, and it
                            also removes the old CRC "key-check oracle" idea.
OUTSIDE BITS ARE HARMLESS   Flipping an LSB the payload does not use leaves the message intact.

Usage (from the project root, venv active):
  python extras/attack_pqc_image.py                       # reference LSB embedder (test stand-in)
  python extras/attack_pqc_image.py --project data/targets/final-year-part1
                                                          # use the pinned project's embed_lsb / extract_lsb
  python extras/attack_pqc_image.py --cover stego_images/lena_stego.png   # use a real image as the cover
  python extras/attack_pqc_image.py --json outputs/attack_pqc_image.json

HONEST LIMITS
-------------
* kyber-py is an educational library, not hardened. This is a prototype demonstration.
* A failed attack here is evidence for THIS construction only; ML-KEM's security rests on
  lattice problems and published analysis, not on this script.
* Without --project the embedder is the reference stand-in (image_pqc.REFERENCE_BACKEND), NOT
  the pinned project's code. The output says which one ran. Say so in the evidence document.
"""
import argparse
import json
import struct
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pqc_stego import hybrid, image_pqc                     # noqa: E402


# ------------------------------------------------------------------ carriers (how bits are hidden)
class ReferenceCarrier:
    """Reference embedder: 4-byte length header + blob, one bit per pixel byte, from byte 0."""
    name = "reference-lsb (test stand-in, not pinned code)"

    def hide(self, public_key, message, cover_png, out_png):
        cover = np.array(Image.open(cover_png).convert("RGB"))
        stego = image_pqc.hide_message(public_key, message, cover.tobytes())
        Image.fromarray(np.frombuffer(stego, dtype=np.uint8).reshape(cover.shape)).save(out_png)

    def reveal_blob(self, stego_png):
        flat = np.array(Image.open(stego_png).convert("RGB")).tobytes()
        return image_pqc.reveal_blob(flat)

    def region_bytes(self, blob_len):
        """Number of pixel bytes the payload occupies (1 bit per byte, header included)."""
        return 8 * (image_pqc.HEADER_BYTES + blob_len)

    def pixel_byte_of(self, blob_offset):
        """Pixel byte that stores the first bit of blob byte `blob_offset` (after the header)."""
        return 8 * (image_pqc.HEADER_BYTES + blob_offset)

    header_pixel_byte = 3          # a bit of the 4-byte length header (header has no pinned equivalent)


class PinnedCarrier:
    """Uses the pinned image project's own embed_lsb / extract_lsb on a hex string of the blob."""

    def __init__(self, project_dir):
        sys.path.insert(0, str(project_dir))
        from lsb_stego import embed_lsb, extract_lsb          # the pinned project's functions
        self._embed, self._extract = embed_lsb, extract_lsb
        self.name = f"pinned:{Path(project_dir).name}/lsb_stego.py"

    def hide(self, public_key, message, cover_png, out_png):
        blob = hybrid.hybrid_encrypt(public_key, message)
        self._embed(str(cover_png), blob.hex(), str(out_png))  # hex string, like the RSA flow

    def reveal_blob(self, stego_png):
        return bytes.fromhex(self._extract(str(stego_png)))

    def region_bytes(self, blob_len):
        return 8 * 2 * blob_len                                 # 2 hex chars per byte, 8 bits per char

    def pixel_byte_of(self, blob_offset):
        return 8 * 2 * blob_offset                              # first bit of the blob byte's hex chars

    header_pixel_byte = None       # the pinned project's own format is not parsed here


# ------------------------------------------------------------------ small helpers
def make_cover(path, size=200, seed=1):
    """A random RGB cover image (a stand-in; any PNG photo can be used instead)."""
    rng = np.random.default_rng(seed)
    Image.fromarray(rng.integers(0, 256, (size, size, 3), dtype=np.uint8)).save(path)


def flip_lsb(stego_png, byte_index, out_png):
    """Copy the image with the LSB of pixel-byte `byte_index` flipped (a 1-bit tamper)."""
    arr = np.array(Image.open(stego_png).convert("RGB"))
    flat = arr.reshape(-1).copy()
    flat[byte_index] ^= 1
    Image.fromarray(flat.reshape(arr.shape)).save(out_png)


def try_decrypt(carrier, secret_key, stego_png):
    """Return ('ok', message) or ('error', ExceptionName) without raising."""
    try:
        blob = carrier.reveal_blob(stego_png)
        return "ok", hybrid.hybrid_decrypt(secret_key, blob)
    except Exception as exc:                                    # any loud failure is a detection
        return "error", type(exc).__name__


# ------------------------------------------------------------------ the attack
def run_attack(carrier, message=b"HELLO", size=200, cover_path=None):
    """Run every check. Returns a list of check dicts (check, kind, expected, observed, ok).

    cover_path: optional real image to use as the cover (converted to RGB). If omitted, a random
    size x size image is generated.
    """
    checks = []

    def record(name, kind, expected, observed, ok):
        checks.append({"check": name, "kind": kind, "expected": expected,
                       "observed": observed, "ok": bool(ok)})

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cover, stego = tmp / "cover.png", tmp / "stego.png"
        if cover_path:
            Image.open(cover_path).convert("RGB").save(cover)      # a real cover image
        else:
            make_cover(cover, size)
        total = int(np.array(Image.open(cover)).size)               # number of pixel bytes in the cover

        # ---- sender (the attacker does not see any of this) ----
        public_key, secret_key = hybrid.generate_keypair()
        _, other_secret_key = hybrid.generate_keypair()
        carrier.hide(public_key, message, cover, stego)

        # ---- attacker: has ONLY the stego image and the public key ----
        # 1. extraction needs no secret (the LSB layer is keyless)
        blob = carrier.reveal_blob(stego)
        record("extract the blob without any secret", "measured",
               f"works, {hybrid.OVERHEAD + len(message)} bytes", f"{len(blob)} bytes",
               len(blob) == hybrid.OVERHEAD + len(message))

        # 2. nothing to factor: the old break needs an integer modulus N
        record("RSA break (factor N) applicable", "by construction",
               "no: no modulus", f"ML-KEM-768 public key is {len(public_key)} raw bytes",
               len(public_key) == 1184)

        # 3. nothing readable in the blob
        record("plaintext visible in the blob", "measured", "no", "no" if message not in blob else "YES",
               message not in blob)

        # 4. wrong secret key
        try:
            hybrid.hybrid_decrypt(other_secret_key, blob)
            wrong = "decrypted (BAD)"
        except hybrid.HybridDecryptError:
            wrong = "HybridDecryptError"
        record("decrypt with the wrong secret key", "measured", "fails", wrong,
               wrong == "HybridDecryptError")

        # 5. sanity: the real receiver can still read it
        status, plain = try_decrypt(carrier, secret_key, stego)
        record("receiver decrypts with the right secret key", "measured",
               message.decode(), plain.decode() if status == "ok" else plain,
               status == "ok" and plain == message)

        # 6. tamper with ONE payload bit in each part of the blob (offsets are inside the blob):
        #    KEM ciphertext = bytes 0..1087, nonce = 1088..1099, tag = 1100..1115, AES part = rest
        parts = [("KEM ciphertext, first byte", 0), ("KEM ciphertext, middle", 544),
                 ("nonce", hybrid.KEM_CT_LEN + 3), ("GCM tag", hybrid.KEM_CT_LEN + hybrid.NONCE_LEN + 5)]
        if len(blob) > hybrid.OVERHEAD:
            parts.append(("AES ciphertext (the message bytes)", hybrid.OVERHEAD))
        targets = [(f"{label} (blob byte {off})", carrier.pixel_byte_of(off) + 7) for label, off in parts]
        if carrier.header_pixel_byte is not None:
            targets.insert(0, ("length header", carrier.header_pixel_byte))
        for label, index in targets:
            bad = tmp / f"tamper_{index}.png"
            flip_lsb(stego, index, bad)
            status, info = try_decrypt(carrier, secret_key, bad)
            record(f"flip 1 payload bit in the {label}, pixel byte {index}", "measured",
                   "decryption fails loudly", f"{status}: {info}", status == "error")

        region = carrier.region_bytes(len(blob))
        # 7. an LSB the payload does not use: harmless
        if region < total:
            bad = tmp / "tamper_outside.png"
            flip_lsb(stego, total - 1, bad)
            status, plain = try_decrypt(carrier, secret_key, bad)
            record("flip 1 bit OUTSIDE the payload (last pixel byte)", "measured",
                   "message still correct", "message intact" if status == "ok" and plain == message
                   else f"{status}", status == "ok" and plain == message)
    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", help="pinned image project folder (uses its embed_lsb/extract_lsb)")
    ap.add_argument("--message", default="HELLO")
    ap.add_argument("--size", type=int, default=200, help="side of the random cover (ignored with --cover)")
    ap.add_argument("--cover", help="use this image as the cover instead of a random one")
    ap.add_argument("--json", help="also write the results to this JSON file")
    args = ap.parse_args()

    carrier = PinnedCarrier(args.project) if args.project else ReferenceCarrier()
    print(f"Attack on the PQC image variant | embedder: {carrier.name}")
    print("Attacker knows: the stego image and the public key. Nothing else.\n")
    checks = run_attack(carrier, args.message.encode(), args.size, args.cover)
    for c in checks:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] ({c['kind']}) {c['check']}\n"
              f"        expected: {c['expected']}  |  observed: {c['observed']}")
    ok = all(c["ok"] for c in checks)
    print("\nRESULT:", "the attack FAILS against the PQC variant, as designed; extraction still works "
          "(the hiding layer is unchanged)" if ok else "UNEXPECTED RESULT - see the FAIL lines")
    print("Remaining weakness: the LSB layer is keyless and detectable (see steganalysis_pqc.py), "
          "which is not a quantum weakness.")
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"embedder": carrier.name, "message_bytes": len(args.message),
                                   "checks": checks, "all_ok": ok}, indent=2) + "\n", encoding="utf-8")
        print("wrote", out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
