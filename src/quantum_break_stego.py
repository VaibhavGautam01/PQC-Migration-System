"""
quantum_break_stego.py - break an RSA + LSB stego image with a REAL quantum circuit.

WHAT THIS DOES
--------------
Given a stego image made by the image project (RSA ciphertext hidden with LSB embedding) and
the PUBLIC key (e, N), this module:
  1. extracts the hidden ciphertext blocks from the image (no secret needed - keyless LSB)
  2. factors N with Shor's algorithm, run as a REAL quantum circuit on the Aer simulator
     (src/q1_shor_pe.py: Hadamards, controlled modular-multiplication unitaries, inverse QFT,
     measurement - the same circuit used for Q1). Classical code does ONLY the continued-fraction
     and gcd post-processing Shor's algorithm itself defines (src/shor_post.py); it never factors
     N by itself.
  3. rebuilds the private exponent d from the measured factors and decrypts every block

This is Shor's algorithm, not a name used for a classical shortcut: the factors come only from
circuit measurements (src/q1_factor.quantum_factor), exactly as in Q1 and the toy-stego demo. The
same static guard (src/quantum_guard.py) that checks Q1 and Q3 checks this file too.

WHY THE MODULUS MUST BE SMALL
------------------------------
The circuit (q1_shor_pe.py) builds its controlled-U gates as dense matrices and simulates them
exactly, so it does not scale: an N of b bits needs about 3b + 3 qubits, and the Aer statevector
simulator needs 2**qubits of memory. This module refuses to even try above MAX_MODULUS_BITS bits
(default 16, about 51 qubits) rather than silently hang or crash; anything a real attacker would
call "breaking RSA" (1024 bits and up) is completely out of reach for this simulator. This is the
same honest limit as Q1: a correct demonstration of the algorithm, not a demonstration that real
RSA keys can be factored today.

TWO WAYS TO READ THE IMAGE
---------------------------
reference format   (default) : a 32-bit length header (bytes), then the ciphertext as ASCII hex
                                text, one bit per pixel byte, written by embed_reference() below.
                                Self-contained: needs no project code.
pinned project format         : the pinned image project's own lsb_stego.extract_lsb (and, for
                                making a demo image, rsa_lsb_embed). Pass project_dir to use it.
Both end up with the same hex string, split into RSA ciphertext integers by hex_width(N) - the
same function the project's own extras/stego_attack_image.py uses.
"""
import struct
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MAX_MODULUS_BITS = 16                    # about 51 qubits; refuse anything larger, see above
HEADER_BITS = 32


class BreakError(Exception):
    """Raised for any problem specific to this module (bad image, modulus too big, ...)."""


# ------------------------------------------------------------------ reference image format
def embed_reference(cover_path, hex_text: str, out_path) -> None:
    """Write `hex_text` behind a 32-bit length header, 1 bit per pixel byte (for making demo images)."""
    cover = np.array(Image.open(cover_path).convert("RGB"))
    flat = cover.reshape(-1).copy()
    data = hex_text.encode("ascii")
    bits = np.unpackbits(np.frombuffer(struct.pack(">I", len(data)) + data, dtype=np.uint8))
    if bits.size > flat.size:
        raise BreakError("the message does not fit in this cover image")
    flat[:bits.size] = (flat[:bits.size] & 0xFE) | bits
    Image.fromarray(flat.reshape(cover.shape)).save(out_path)


def extract_reference(stego_path) -> str:
    """Read the hex text back from the 32-bit-header reference format."""
    flat = np.array(Image.open(stego_path).convert("RGB")).reshape(-1)
    if flat.size < HEADER_BITS:
        raise BreakError("image is too small to hold a header")
    length = struct.unpack(">I", np.packbits(flat[:HEADER_BITS] & 1).tobytes())[0]
    end_bit = HEADER_BITS + length * 8
    if end_bit > flat.size:
        raise BreakError("the header's length does not fit in this image: wrong N, or not a "
                         "reference-format stego image")
    return np.packbits(flat[HEADER_BITS:end_bit] & 1).tobytes().decode("ascii")


def extract_pinned(stego_path, project_dir) -> str:
    """Read the hex text back with the pinned image project's own extract_lsb."""
    sys.path.insert(0, str(project_dir))
    from lsb_stego import extract_lsb              # the pinned project's own function
    return extract_lsb(str(stego_path))


# ------------------------------------------------------------------ RSA block splitting (public data only)
def hex_width(n: int) -> int:
    """Hex-string width of one RSA ciphertext block for modulus n (same rule as the project's)."""
    return ((n.bit_length() + 7) // 8) * 2


def blocks_from_hex(hex_text: str, n: int) -> list:
    """Split the extracted hex text into ciphertext integers, hex_width(n) characters each."""
    hex_text = hex_text.strip()
    w = hex_width(n)
    if w == 0 or len(hex_text) % w != 0 or len(hex_text) == 0:
        raise BreakError(f"extracted text is not a whole number of {w}-character blocks for "
                         f"this N; check that N matches this image")
    try:
        return [int(hex_text[i:i + w], 16) for i in range(0, len(hex_text), w)]
    except ValueError as exc:
        raise BreakError(f"extracted text is not valid hex for this N ({exc})") from exc


# ------------------------------------------------------------------ the quantum break
def factor_modulus(n: int, shots: int = 2048, max_tries: int = 6, progress=None):
    """Factor the PUBLIC modulus n with Shor's algorithm, run as a real circuit on Aer.

    Delegates to src.q1_factor.quantum_factor: the same code path used for Q1 and the toy-stego
    demo. `progress`, if given, is called once per base tried with a short status string.
    Returns the dict quantum_factor returns: factors, the base used, the measured period, every
    attempt, and the evidence record of every circuit run (for --save-evidence).
    """
    if n.bit_length() > MAX_MODULUS_BITS:
        raise BreakError(
            f"N is {n.bit_length()} bits; this simulator only handles up to {MAX_MODULUS_BITS} "
            f"bits (about {3 * MAX_MODULUS_BITS + 3} qubits). Real RSA sizes (1024+ bits) are far "
            f"beyond what any simulator or today's quantum hardware can factor; see the Quantum "
            f"Lab's honest-limits rules.")
    from src.q1_factor import quantum_factor        # imported late: needs qiskit
    if progress is None:
        return quantum_factor(n, shots=shots, max_tries=max_tries)

    from math import gcd
    from src.q1_factor import STEGO_GROUP, candidate_bases
    from src.q1_run import run_q1
    from src import shor_post as SP
    attempts, records = [], []
    for a in candidate_bases(n):
        if len(attempts) >= max_tries:
            break
        g = gcd(a, n)
        if g != 1:
            attempts.append({"a": a, "outcome": f"gcd(a, N) = {g}"})
            progress(f"a={a}: gcd(a, N) = {g} (lucky factor, no circuit needed)")
            return {"factors": tuple(sorted((g, n // g))), "a": a, "period": None,
                    "method": "lucky gcd", "attempts": attempts, "records": records}
        progress(f"a={a}: running the Shor circuit on Aer ...")
        record, _ = run_q1(a, n, shots, cross_check=False)
        record["question_group"] = STEGO_GROUP
        records.append(record)
        found = SP.analyse_counts(record["counts"], record["inputs"]["counting_qubits"], a, n)
        attempts.append({"a": a, "period": found["period"], "factors": found["factors"]})
        progress(f"a={a}: measured period r={found['period']}, factors={found['factors']}")
        if found["factors"]:
            return {"factors": tuple(found["factors"]), "a": a, "period": found["period"],
                    "method": "quantum circuit", "attempts": attempts, "records": records}
    return {"factors": None, "a": None, "period": None, "method": "failed",
            "attempts": attempts, "records": records}


def rebuild_private_key(e: int, n: int, p: int, q: int) -> int:
    """Rebuild the RSA private exponent d from the MEASURED factors (classical, standard RSA
    maths - this is the "recover d" step every RSA break ends with, not a shortcut around Shor)."""
    if {p, q} == {1} or p * q != n or p == q:
        raise BreakError(f"p={p}, q={q} do not multiply to N={n}")
    phi = (p - 1) * (q - 1)
    return pow(e, -1, phi)


def decrypt_blocks(blocks: list, d: int, n: int) -> bytes:
    """Textbook RSA decryption of every block with the recovered private key."""
    out = bytearray()
    for c in blocks:
        m = pow(c, d, n)
        if m >= 256:
            raise BreakError(f"decrypted value {m} is not a single byte; check e and N")
        out.append(m)
    return bytes(out)


def break_stego_image(stego_path, e: int, n: int, project_dir=None, shots: int = 2048,
                      progress=None) -> dict:
    """Run the whole break: extract -> factor with Shor -> rebuild d -> decrypt.

    The attacker uses ONLY the stego image and the public key (e, n). Returns a dict with the
    extracted blocks, the Shor result, the recovered key and the decrypted message, or raises
    BreakError with a message safe to show in the dashboard.
    """
    t0 = time.perf_counter()
    hex_text = (extract_pinned(stego_path, project_dir) if project_dir
               else extract_reference(stego_path))
    blocks = blocks_from_hex(hex_text, n)
    shor = factor_modulus(n, shots=shots, progress=progress)
    if shor["factors"] is None:
        raise BreakError(f"the Shor circuit did not find the factors of N in {len(shor['attempts'])} "
                         f"attempt(s); try more shots or more attempts")
    p, q = shor["factors"]
    d = rebuild_private_key(e, n, p, q)
    message = decrypt_blocks(blocks, d, n)
    return {"hex_text": hex_text, "blocks": blocks, "p": p, "q": q, "d": d, "message": message,
           "shor": shor, "elapsed_seconds": round(time.perf_counter() - t0, 3)}
