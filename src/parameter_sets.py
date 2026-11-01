"""
parameter_sets.py
-----------------
Comparison of the ML-KEM and ML-DSA parameter sets for the hybrid steganography
payload (Week 3 Day 4): sizes, payload overhead, cover capacity, embedding rate.

  python src/parameter_sets.py
  python src/parameter_sets.py --message-bytes 100 --frame 128 128
  python src/parameter_sets.py --measure        # compare with the installed libraries

SIZES are copied from the plan's table (FIPS 203 and FIPS 204) and are marked
unverified until a team member has checked them against the standards. The
decapsulation / secret key sizes are from memory and need the same check.

Payload layout (plan section 6): KEM ciphertext + 12-byte nonce + 16-byte tag +
AES ciphertext, plus the signature when signing is used. Any extra header in the
real format (version or length bytes) adds to these numbers.

Capacity assumption: 1 bit per colour channel, 3 channels, per frame. Check this
against the embedding of the pinned projects. Pure arithmetic; no simulator.
"""
import argparse
import math

VERIFIED_AGAINST_STANDARDS = False

KEM = {   # bytes
    "ML-KEM-512": dict(category=1, ek=800, dk=1632, ct=768, ss=32),
    "ML-KEM-768": dict(category=3, ek=1184, dk=2400, ct=1088, ss=32),
    "ML-KEM-1024": dict(category=5, ek=1568, dk=3168, ct=1568, ss=32),
}
DSA = {   # bytes
    "ML-DSA-44": dict(category=2, pk=1312, sk=2560, sig=2420),
    "ML-DSA-65": dict(category=3, pk=1952, sk=4032, sig=3309),
    "ML-DSA-87": dict(category=5, pk=2592, sk=4896, sig=4627),
}
PAIRINGS = [("ML-KEM-512", "ML-DSA-44"), ("ML-KEM-768", "ML-DSA-65"), ("ML-KEM-1024", "ML-DSA-87")]
NONCE_LEN, TAG_LEN = 12, 16
HEADER_BITS_PER_FRAME = 16          # per-frame length header of the video project (Tarun's review)
RSA_CIPHERTEXT_BYTES = {256: 32, 512: 64, 1024: 128, 2048: 256}


def _need_nonneg_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer, got {value!r}")


def payload_overhead(kem: str, dsa: str = None) -> int:
    """Bytes added to the message: KEM ciphertext + nonce + tag (+ signature)."""
    if kem not in KEM:
        raise ValueError(f"unknown KEM {kem!r}")
    total = KEM[kem]["ct"] + NONCE_LEN + TAG_LEN
    if dsa is not None:
        if dsa not in DSA:
            raise ValueError(f"unknown signature scheme {dsa!r}")
        total += DSA[dsa]["sig"]
    return total


def payload_size(kem: str, message_bytes: int, dsa: str = None) -> int:
    _need_nonneg_int(message_bytes, "message_bytes")
    return message_bytes + payload_overhead(kem, dsa)


def capacity_bits(width: int, height: int, channels: int = 3, bits_per_channel: int = 1) -> int:
    for n, v in (("width", width), ("height", height), ("channels", channels), ("bits_per_channel", bits_per_channel)):
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise ValueError(f"{n} must be a positive integer, got {v!r}")
    return width * height * channels * bits_per_channel


def min_square_side(payload_bytes: int, channels: int = 3, bits_per_channel: int = 1) -> int:
    """Smallest square image side (pixels) whose capacity holds the payload."""
    _need_nonneg_int(payload_bytes, "payload_bytes")
    per_pixel = channels * bits_per_channel
    pixels = -(-payload_bytes * 8 // per_pixel)          # ceiling
    side = math.isqrt(pixels)
    return side if side * side >= pixels else side + 1


def frames_needed(payload_bytes: int, width: int, height: int, header_bits: int = HEADER_BITS_PER_FRAME,
                  channels: int = 3, bits_per_channel: int = 1) -> int:
    """Frames of this size needed when each frame also carries a length header."""
    _need_nonneg_int(payload_bytes, "payload_bytes")
    usable = capacity_bits(width, height, channels, bits_per_channel) - header_bits
    if usable <= 0:
        raise ValueError("frame too small for the per-frame header")
    return max(1, -(-payload_bytes * 8 // usable))


def embedding_rate(payload_bytes: int, capacity: int) -> float:
    """Fraction of the cover capacity used (a larger rate is easier to detect)."""
    if capacity <= 0:
        raise ValueError("capacity must be positive")
    return payload_bytes * 8 / capacity


def measure_library_sizes():
    """Measure sizes from the installed kyber-py and dilithium-py. Returns (sizes, errors)."""
    sizes, errors = {}, []
    try:
        from kyber_py.ml_kem import ML_KEM_512, ML_KEM_768, ML_KEM_1024
        for name, k in (("ML-KEM-512", ML_KEM_512), ("ML-KEM-768", ML_KEM_768), ("ML-KEM-1024", ML_KEM_1024)):
            ek, dk = k.keygen()
            ss, ct = k.encaps(ek)
            sizes[name] = dict(ek=len(ek), dk=len(dk), ct=len(ct), ss=len(ss))
    except Exception as e:  # noqa: BLE001
        errors.append(f"ML-KEM: {type(e).__name__}: {e}")
    try:
        from dilithium_py.ml_dsa import ML_DSA_44, ML_DSA_65, ML_DSA_87
        for name, d in (("ML-DSA-44", ML_DSA_44), ("ML-DSA-65", ML_DSA_65), ("ML-DSA-87", ML_DSA_87)):
            pk, sk = d.keygen()
            sig = d.sign(sk, b"size check")
            sizes[name] = dict(pk=len(pk), sk=len(sk), sig=len(sig))
    except Exception as e:  # noqa: BLE001
        errors.append(f"ML-DSA: {type(e).__name__}: {e}")
    return sizes, errors


def compare_with_table(measured: dict) -> list:
    """List of (name, field, table_value, measured_value) that differ."""
    diffs = []
    for name, got in measured.items():
        table = KEM.get(name) or DSA.get(name)
        for field, value in got.items():
            if field in table and table[field] != value:
                diffs.append((name, field, table[field], value))
    return diffs


def print_report(message_bytes, frame):
    print(f"Sizes in bytes (from the plan's table; verified against standards: {VERIFIED_AGAINST_STANDARDS})")
    for n, p in KEM.items():
        print(f"  {n:<12} cat {p['category']}  public {p['ek']:>5}  secret {p['dk']:>5}  ciphertext {p['ct']:>5}  shared secret {p['ss']}")
    for n, p in DSA.items():
        print(f"  {n:<12} cat {p['category']}  public {p['pk']:>5}  secret {p['sk']:>5}  signature  {p['sig']:>5}")
    print(f"\nPayload overhead (KEM ciphertext + {NONCE_LEN} nonce + {TAG_LEN} tag, plus signature) and total for a {message_bytes}-byte message")
    w, h = frame
    print(f"  {'setup':<30}{'overhead':>9}{'total':>8}{'min square':>12}{'frames of ' + str(w) + 'x' + str(h):>18}")
    for kem, dsa in PAIRINGS:
        for d in (None, dsa):
            ov, tot = payload_overhead(kem, d), payload_size(kem, message_bytes, d)
            label = kem if d is None else f"{kem} + {d}"
            print(f"  {label:<30}{ov:>9}{tot:>8}{min_square_side(tot):>9} px{frames_needed(tot, w, h):>16}")
    print("\nFor comparison, a textbook RSA ciphertext is "
          + ", ".join(f"{b} B ({k}-bit)" for k, b in RSA_CIPHERTEXT_BYTES.items()))
    cap = capacity_bits(256, 256)
    print("\nEmbedding rate in a 256x256 image (1 bit per channel, 3 channels):")
    for kem, dsa in PAIRINGS:
        for d in (None, dsa):
            tot = payload_size(kem, message_bytes, d)
            print(f"  {kem if d is None else kem + ' + ' + d:<30}{embedding_rate(tot, cap):>7.1%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--message-bytes", type=int, default=100)
    ap.add_argument("--frame", type=int, nargs=2, default=[128, 128], metavar=("W", "H"))
    ap.add_argument("--measure", action="store_true", help="compare the table with the installed libraries")
    a = ap.parse_args()
    print_report(a.message_bytes, a.frame)
    if a.measure:
        sizes, errors = measure_library_sizes()
        diffs = compare_with_table(sizes)
        print("\nMeasured from the installed libraries:")
        for n, s in sizes.items():
            print(f"  {n}: {s}")
        for e in errors:
            print("  could not measure:", e)
        print("  differences from the table:", diffs or "none")