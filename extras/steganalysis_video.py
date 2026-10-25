"""
steganalysis_video.py - RSA payload vs PQC payload vs SIGNED PQC payload, for the video
project (Week 3 Day 4). Black-box: measured on the stego frames' LSB plane only.

THREE PAYLOADS COMPARED, same frames, same message
  RSA (size stand-in)    bytes sized like textbook RSA ciphertext (one 128-byte block per
                          message byte at 1024 bits), embedded with video_pqc's OWN LSB
                          mechanics (_write_stream) so only the payload SIZE differs, not
                          the embedding method. Content is random bytes: this script measures
                          size and LSB statistics, not an RSA round trip (video_pqc has no
                          RSA path of its own to compare against).
  PQC plain               pqc_stego.video_pqc.hide_message(), unsigned
  PQC signed               pqc_stego.video_pqc.hide_message(..., signer_sk=...), ML-DSA-65
                          signed (+3,309 bytes, Section 6 of the plan)

WHAT IS MEASURED, pooled over the frames each payload actually used
  payload size             bytes, and share of total capacity used
  frames used              how many of the available frames the payload touched
  LSB ones fraction         share of 1s in the LSB plane (clean frame bytes ~ 0.5)
  chi-square pair test      p near 1 means byte-value pairs are equalised (LSB replacement);
                           the repo's rule (steganalysis_chi2.py) flags p > 0.5

Usage (from the project root, venv active):
  python extras/steganalysis_video.py
  python extras/steganalysis_video.py --frames 30 --frame-size 4000 --lengths 5 40 200

HONEST LIMITS
-------------
* Synthetic frames (random bytes), not real decoded video.
* Uses video_pqc's REFERENCE backend (its own docstring: not the pinned project's code).
* Simple detectors, not state-of-the-art steganalysis.
"""
import argparse
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np                                            # noqa: E402

from pqc_stego import hybrid, signing, video_pqc              # noqa: E402
from src import shor_post as SP                                # noqa: E402  (chi-square p-value)

RULE_P = 0.5


def make_frames(count, frame_bytes, seed=1):
    import random
    rng = random.Random(seed)
    return [bytes(rng.randrange(256) for _ in range(frame_bytes)) for _ in range(count)]


def ones_fraction(data: bytes) -> float:
    arr = np.frombuffer(data, dtype=np.uint8)
    return float((arr & 1).mean()) if arr.size else float("nan")


def chi_square_pair_p(data: bytes) -> float:
    arr = np.frombuffer(data, dtype=np.uint8)
    hist = np.bincount(arr, minlength=256).astype(float)
    obs = hist[0::2]
    exp = (hist[0::2] + hist[1::2]) / 2
    keep = exp >= 5
    if keep.sum() < 2:
        return float("nan")
    stat = float(np.sum((obs[keep] - exp[keep]) ** 2 / exp[keep]))
    return SP.chi2_sf(stat, int(keep.sum()) - 1)


def used_frames(original, stego, order):
    return [i for i in order if original[i] != stego[i]]


def analyse(frames, stego, used, payload_bytes, label):
    clean_bytes = b"".join(frames[i] for i in used)
    stego_bytes = b"".join(stego[i] for i in used)
    p = chi_square_pair_p(stego_bytes)
    return {"payload": label, "payload_bytes": payload_bytes, "frames_used": len(used),
           "ones_clean": round(ones_fraction(clean_bytes), 4) if used else None,
           "ones_stego": round(ones_fraction(stego_bytes), 4) if used else None,
           "chi_p_region": None if np.isnan(p) else round(p, 4),
           "flagged_region": bool(p > RULE_P) if not np.isnan(p) else False}


def raw_rsa_sized_payload(message_len, rsa_bits=1024):
    """Byte count a real RSA-1024 ciphertext stream would need for this message length (one
    128-byte block per byte of message); filled with random bytes for the LSB-statistics
    measurement (video_pqc has no RSA path to compare a real round trip against)."""
    block = (rsa_bits + 7) // 8
    return os.urandom(block * message_len)


def run_experiment(frames, lengths):
    public_key, _ = hybrid.generate_keypair()
    spk, ssk = signing.generate_keypair()
    order = list(range(len(frames)))
    results = []
    for length in lengths:
        msg = (b"The quick brown fox jumps over the lazy dog. " * 10)[:length]
        rows = []

        rsa_payload = raw_rsa_sized_payload(length)
        rsa_full = struct.pack(">BI", video_pqc.FLAG_PLAIN, len(rsa_payload)) + rsa_payload
        try:
            rsa_stego = video_pqc._write_stream(frames, order, rsa_full)
            rows.append(analyse(frames, rsa_stego, used_frames(frames, rsa_stego, order),
                                len(rsa_payload), "RSA-sized (stand-in)"))
        except video_pqc.VideoCapacityError:
            rows.append({"payload": "RSA-sized (stand-in)", "payload_bytes": len(rsa_payload),
                        "note": "does not fit in these frames"})

        try:
            plain_stego = video_pqc.hide_message(public_key, msg, frames)
            rows.append(analyse(frames, plain_stego, used_frames(frames, plain_stego, order),
                                hybrid.OVERHEAD + length, "PQC plain"))
        except video_pqc.VideoCapacityError:
            rows.append({"payload": "PQC plain", "payload_bytes": hybrid.OVERHEAD + length,
                        "note": "does not fit in these frames"})

        try:
            signed_stego = video_pqc.hide_message(public_key, msg, frames, signer_sk=ssk)
            rows.append(analyse(frames, signed_stego, used_frames(frames, signed_stego, order),
                                hybrid.OVERHEAD + length + 3309, "PQC signed (ML-DSA-65)"))
        except video_pqc.VideoCapacityError:
            rows.append({"payload": "PQC signed (ML-DSA-65)",
                        "payload_bytes": hybrid.OVERHEAD + length + 3309,
                        "note": "does not fit in these frames"})

        results.append({"message_chars": length, "rows": rows})
    return results


def to_markdown(results, cap):
    lines = [f"Steganalysis: RSA-sized vs PQC vs signed PQC payload (video, reference backend) | "
             f"total capacity {cap} bytes", "",
             "| msg chars | payload | bytes | frames used | ones (clean) | ones (stego) | "
             "chi p (region) | flagged (p>0.5) |", "|---|---|---|---|---|---|---|---|"]
    for block in results:
        for r in block["rows"]:
            if "note" in r:
                lines.append(f"| {block['message_chars']} | {r['payload']} | {r['payload_bytes']} | "
                             f"{r['note']} ||||")
                continue
            lines.append(f"| {block['message_chars']} | {r['payload']} | {r['payload_bytes']} | "
                         f"{r['frames_used']} | {r['ones_clean']} | {r['ones_stego']} | "
                         f"{r['chi_p_region']} | {r['flagged_region']} |")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", type=int, default=30)
    ap.add_argument("--frame-size", type=int, default=4000, help="raw bytes per frame")
    ap.add_argument("--lengths", type=int, nargs="+", default=[5, 40, 200])
    ap.add_argument("--out", default="outputs/steganalysis_pqc_video")
    args = ap.parse_args()

    frames = make_frames(args.frames, args.frame_size)
    cap = video_pqc.total_capacity(frames)
    results = run_experiment(frames, args.lengths)
    text = to_markdown(results, cap)
    print(text)
    print("Reading the table: compare 'ones (stego)' with 'ones (clean)' for the SAME frames. A "
          "payload is detectable here only if the two diverge, or chi p region is flagged.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".md").write_text(text, encoding="utf-8")
    out.with_suffix(".json").write_text(
        json.dumps({"capacity_bytes": cap, "results": results}, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.with_suffix('.md')} and {out.with_suffix('.json')}")


if __name__ == "__main__":
    main()
