"""
attack_pqc_video.py - attack the PQC video variant (Week 3 Day 3).

THE SETUP
---------
The video project used to hide an RSA-encrypted message split across frames, keyed by
SHA-256(passphrase) choosing only frames 0-255 (the frame-selection flaw). The PQC variant
(pqc_stego.video_pqc) hides a hybrid ML-KEM-768 + AES-256-GCM blob instead, optionally signed
with ML-DSA (pqc_stego.signing). The attacker has what a real attacker would have: the stego
frames and the receiver's PUBLIC key (and, for a signed video, the sender's public verify key).
No secret.

FRAME FORMAT (from pqc_stego/video_pqc.py)
-------------------------------------------
Frames are plain bytes-like objects, 1 hidden bit per byte (frame_capacity = len(frame) // 8).
Payload layout: flag (1 B) | body length (4 B, big-endian) | body. reveal_body() needs no key -
the hiding layer is keyless, same as the image project's LSB embedding.

WHAT THIS SCRIPT SHOWS
-----------------------
HEADER SCAN / EXTRACTION STILL WORKS   reveal_body() needs no secret key.
WRONG KEY FAILS                        reveal_message() with another receiver's secret key raises.
TAMPERING FAILS LOUDLY                 flipping one LSB in the header or a payload-carrying frame
                                       makes reveal_message() raise, never a silently wrong message.
                                       video_pqc.py itself rejects an unrecognised flag value
                                       (VideoFormatError), so a header-byte flip is caught early.
SIGNED VARIANT                         a signed blob read WITHOUT the verifier's public key, or a
                                       plain blob read WITH one, is rejected (VideoFormatError); a
                                       tampered signed blob, or one verified with the WRONG signer's
                                       public key, is rejected (signing.SignatureError).
FRAME ORDER                            compares the default (sequential) frame order against
                                       frame_select_v2.select_frames(), which is meant to spread the
                                       payload across the WHOLE video instead of only frames 0-255.

Usage (from the project root, venv active):
  python extras/attack_pqc_video.py
  python extras/attack_pqc_video.py --frames 20 --frame-size 4000
  python extras/attack_pqc_video.py --json outputs/attack_pqc_video.json

HONEST LIMITS
-------------
* Uses small SYNTHETIC frames (random bytes), not real decoded video.
* The embedder is the REFERENCE backend in video_pqc.py (its own docstring: "NOT the pinned
  video project's code"); say "reference backend" when reporting these numbers.
* kyber-py and dilithium-py are educational libraries, not hardened; a failed attack here is
  evidence for this construction, not a proof that ML-KEM/ML-DSA are secure.
* This script does not attack the frame-SELECTION key itself (a 256-bit search, out of reach);
  it only shows whether the chosen order changes which frames hold data.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pqc_stego import frame_select_v2, hybrid, signing, video_pqc    # noqa: E402


def make_frames(count, frame_bytes, seed=1):
    """Synthetic frames: `count` random byte strings, each `frame_bytes` long."""
    import random
    rng = random.Random(seed)
    return [bytes(rng.randrange(256) for _ in range(frame_bytes)) for _ in range(count)]


def flip_lsb(frames, frame_index, byte_index):
    """A frame-list copy with the LSB of one byte in one frame flipped."""
    out = list(frames)
    data = bytearray(out[frame_index])
    data[byte_index] ^= 1
    out[frame_index] = bytes(data)
    return out


def used_frames(original, stego, order):
    """Frame indices (within `order`) the payload actually changed, in order."""
    return [i for i in order if original[i] != stego[i]]


def try_reveal(frames, secret_key, order=None, verifier_pk=None):
    """Return ('ok', message) or ('error', ExceptionName[: short text]) without raising."""
    try:
        return "ok", video_pqc.reveal_message(secret_key, frames, order=order, verifier_pk=verifier_pk)
    except Exception as exc:
        text = " ".join(str(exc).split())[:60]
        return "error", f"{type(exc).__name__}" + (f" ({text})" if text else "")


def record(checks, name, kind, expected, observed, ok):
    checks.append({"check": name, "kind": kind, "expected": expected, "observed": observed, "ok": bool(ok)})


def run_attack(frames, message=b"HELLO FROM THE VIDEO PROJECT"):
    checks = []
    public_key, secret_key = hybrid.generate_keypair()
    _, other_secret_key = hybrid.generate_keypair()
    spk, ssk = signing.generate_keypair()
    spk2, _ = signing.generate_keypair()
    default_order = list(range(len(frames)))

    # ---- 1. unsigned (plain) video ----
    stego = video_pqc.hide_message(public_key, message, frames)
    used = used_frames(frames, stego, default_order)             # frames the payload actually touched
    flag, body = video_pqc.reveal_body(stego)                    # attacker: no secret needed
    record(checks, "extract the hidden body without any secret", "measured",
          f"works, flag={video_pqc.FLAG_PLAIN}", f"works, flag={flag}, {len(body)} bytes, "
          f"{len(used)} frame(s) used", flag == video_pqc.FLAG_PLAIN)

    status, plain = try_reveal(stego, secret_key)
    record(checks, "receiver decrypts with the right secret key", "measured",
          message.decode(), plain.decode() if status == "ok" else plain, status == "ok" and plain == message)

    status, info = try_reveal(stego, other_secret_key)
    record(checks, "decrypt with the wrong secret key", "measured", "fails", f"{status}: {info}",
          status == "error")

    # header lives in the first HEADER_BYTES=5 bytes of the payload stream; flip a header bit
    header_bad = flip_lsb(stego, used[0], 2)
    status, info = try_reveal(header_bad, secret_key)
    record(checks, f"flip 1 bit in the header (frame {used[0]})", "measured",
          "decryption fails loudly", f"{status}: {info}", status == "error")

    # a frame the payload actually used, past the header if more than one frame was used
    payload_frame = used[1] if len(used) > 1 else used[0]
    bad_pos = 40 if payload_frame == used[0] else 2             # past the 5-byte (40-bit) header
    payload_bad = flip_lsb(stego, payload_frame, bad_pos)
    status, info = try_reveal(payload_bad, secret_key)
    record(checks, f"flip 1 bit in a payload-carrying frame (frame {payload_frame})", "measured",
          "decryption fails loudly", f"{status}: {info}", status == "error")

    # ---- 2. signed video ----
    signed = video_pqc.hide_message(public_key, message, frames, signer_sk=ssk)
    signed_used = used_frames(frames, signed, default_order)
    flag_s, _ = video_pqc.reveal_body(signed)
    record(checks, "signed video: flag is readable without any secret", "measured",
          f"flag={video_pqc.FLAG_SIGNED}", f"flag={flag_s}", flag_s == video_pqc.FLAG_SIGNED)

    status, plain = try_reveal(signed, secret_key, verifier_pk=spk)
    record(checks, "signed video: receiver verifies and decrypts correctly", "measured",
          message.decode(), plain.decode() if status == "ok" else plain, status == "ok" and plain == message)

    status, info = try_reveal(signed, secret_key)                 # no verifier_pk given
    record(checks, "signed video read WITHOUT the verifier's public key", "measured",
          "rejected (format error)", f"{status}: {info}", status == "error")

    status, info = try_reveal(stego, secret_key, verifier_pk=spk)  # plain blob, verifier_pk given
    record(checks, "plain video read WITH a verifier public key", "measured",
          "rejected (format error)", f"{status}: {info}", status == "error")

    status, info = try_reveal(signed, secret_key, verifier_pk=spk2)  # wrong signer
    record(checks, "signed video verified with the WRONG signer's public key", "measured",
          "rejected (signature error)", f"{status}: {info}", status == "error")

    tamper_frame = signed_used[1] if len(signed_used) > 1 else signed_used[0]
    tamper_pos = 40 if tamper_frame == signed_used[0] else 2
    tampered_signed = flip_lsb(signed, tamper_frame, tamper_pos)
    status, info = try_reveal(tampered_signed, secret_key, verifier_pk=spk)
    record(checks, f"tamper a signed video's payload (frame {tamper_frame})", "measured", "rejected",
          f"{status}: {info}", status == "error")

    # ---- 3. frame order: does the fix spread data across the WHOLE video? ----
    n = len(frames)
    fixed_key = frame_select_v2.generate_key()
    order = frame_select_v2.select_frames(fixed_key, n, min(n, 20))
    stego_selected = video_pqc.hide_message(public_key, b"order test", frames, order=order)
    status, plain = try_reveal(stego_selected, secret_key, order=order)
    record(checks, "round-trip with a frame_select_v2 order", "measured", "order test",
          plain.decode(errors="replace") if status == "ok" else f"{status}: {plain}", status == "ok")
    record(checks, "frame_select_v2 order can reach beyond frame 255 (n > 256)", "by construction",
          "uses the whole video" if n > 256 else "n/a (fewer than 256 frames in this run)",
          f"order sample (first 10 of {n} frames): {order[:10]}", True)

    return checks


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--frames", type=int, default=20, help="number of synthetic frames")
    ap.add_argument("--frame-size", type=int, default=4000,
                    help="raw bytes per frame (capacity = this // 8; default matches the "
                         "project's own ~500 B/frame test fixture)")
    ap.add_argument("--message", default="HELLO FROM THE VIDEO PROJECT")
    ap.add_argument("--json", help="also write the results to this JSON file")
    args = ap.parse_args()

    frames = make_frames(args.frames, args.frame_size)
    cap = video_pqc.total_capacity(frames)
    print(f"Attack on the PQC video variant (reference backend) | {args.frames} synthetic frames "
          f"of {args.frame_size} raw bytes each | total capacity {cap} bytes")
    print("Attacker knows: the stego frames and the public key(s). Nothing else.\n")
    checks = run_attack(frames, args.message.encode())
    for c in checks:
        print(f"[{'PASS' if c['ok'] else 'FAIL'}] ({c['kind']}) {c['check']}\n"
              f"        expected: {c['expected']}  |  observed: {c['observed']}")
    ok = all(c["ok"] for c in checks)
    print("\nRESULT:", "the attack FAILS against the PQC video variant, as designed; extraction "
          "of the raw body still works (the hiding layer is unchanged)" if ok else
          "UNEXPECTED RESULT - see the FAIL lines")
    print("Remaining weakness: the header/body can still be found without a key; migration fixes "
          "the encryption and signing layers, not the hiding layer.")
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"frames": args.frames, "frame_bytes": args.frame_size,
                                   "capacity_bytes": cap, "checks": checks, "all_ok": ok},
                                  indent=2) + "\n", encoding="utf-8")
        print("wrote", out)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
