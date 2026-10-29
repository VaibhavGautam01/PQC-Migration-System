"""Stage 4: identify the cipher from the blob.  Owner: Uday (written in Week 6, please review).

What can be decided, and how:
  * textbook RSA: needs the public key. The blob must be hex whose length is a whole number of ciphertext
    blocks for this modulus and every block must be below N (extras/stego_attack_toy.py layout).
  * ML-KEM + AES-GCM: the hex decodes to at least 1,116 bytes (1,088 KEM ciphertext + 12 nonce + 16 tag,
    sizes from FIPS 203 and pqc_stego/hybrid.py) and is not a textbook layout. The structure inside cannot
    be verified without the secret key, so the evidence says "length only".
  * OAEP-style RSA is NOT identified: one OAEP block looks like one textbook block. It is reported as
    unrecognised rather than guessed.
  * anything else: "unrecognised".
"""
import sys
from pathlib import Path

from . import toyformat

ROOT = Path(__file__).resolve().parent.parent
try:
    from pqc_stego import hybrid
except ImportError:
    sys.path.insert(0, str(ROOT))
    from pqc_stego import hybrid


def identify(blob, public_key=None):
    text = blob.decode("ascii", errors="replace") if isinstance(blob, (bytes, bytearray)) else str(blob)
    n = None
    if public_key:
        try:
            n = int(public_key["n"])
        except (KeyError, TypeError, ValueError):
            n = None
    if n is not None and n > 1 and toyformat.is_hex(text):
        blocks = toyformat.split_blocks(text, n)
        if blocks is not None and len(blocks) >= 2:
            return {"kind": "textbook_rsa", "n": n, "modulus_bits": n.bit_length(),
                    "evidence": f"hex length is {len(blocks)} blocks of {toyformat.hex_width(n)} characters "
                                "for this modulus and every block is below N"}
    if toyformat.is_hex(text) and len(text) % 2 == 0 and len(text) // 2 >= hybrid.OVERHEAD:
        return {"kind": "ml_kem_aes_gcm", "n": None, "modulus_bits": None,
                "evidence": f"{len(text) // 2} bytes, at least the {hybrid.OVERHEAD} bytes of KEM ciphertext "
                            "(1,088), nonce (12) and tag (16); length only, the structure cannot be checked "
                            "without the secret key"}
    return {"kind": "unrecognised", "n": None, "modulus_bits": None,
            "evidence": "no known layout fits (OAEP-style blobs are not identified)"}
