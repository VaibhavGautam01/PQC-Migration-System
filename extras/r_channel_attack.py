"""
r_channel_attack.py - Attack on the R-channel + RSA steganography module (pinned image project).

How the target works (from r_channel_stego.py):
  - Pixel 0: its RED value stores the message length.
  - Pixels 1..length: each RED value stores one RSA-encrypted character.
  - The RSA modulus n is always an 8-bit number (128 <= n < 256), built from two primes below 40.

This script breaks it in two ways, using only the stego image:
  Attack A (public key): read the red values, split n into its two primes, rebuild the private
                         key d, decrypt.
  Attack B (keyless):    the generator can only produce a few hundred different keys, so try
                         all of them and keep the results that look like readable text.

Both attacks run on an ordinary computer. Nothing here is quantum.

Usage (from the project root, venv active):
  python extras\\r_channel_attack.py --project data\\targets\\final-year-part1 --message "HELLO QUANTUM"
"""
import argparse   # reads the command-line options
import os         # os.urandom makes the random cover image
import sys        # lets us import the target project's modules
import time       # measures how long each attack takes
from pathlib import Path

import numpy as np                     # fast access to the pixel values
from PIL import Image                  # opens and creates images
from sympy import factorint, isprime   # splits a number into primes / tests for primes


def read_red_values(image_path):
    """Step 1 of both attacks. No key is needed to do this.

    Returns (length, ciphertext): the message length stored in pixel 0 and the list of
    encrypted character values stored in the red channel of the next pixels.
    """
    # Load the image as an array of shape (height, width, 3) and flatten it to a list of
    # pixels, each with 3 values (red, green, blue).
    flat = np.array(Image.open(image_path).convert("RGB")).reshape(-1, 3)
    length = int(flat[0, 0])                                   # red value of the first pixel
    ciphertext = [int(v) for v in flat[1:length + 1, 0]]       # red values of the next pixels
    return length, ciphertext


def public_key_attack(pub, ciphertext):
    """Attack A: use the public key (e, n) to rebuild the private key and decrypt.

    RSA is safe only if n cannot be split into its two primes. Here n is an 8-bit number,
    so splitting it takes a fraction of a millisecond.
    """
    e, n = pub                                  # public exponent and public modulus
    t0 = time.time()
    factors = factorint(n)                      # e.g. {7: 1, 23: 1} for n = 161
    p, q = sorted(factors)                      # the two secret primes
    d = pow(e, -1, (p - 1) * (q - 1))           # private exponent: inverse of e modulo phi(n)
    # Decrypt every value with the textbook RSA rule: plaintext = ciphertext^d mod n.
    text = "".join(chr(pow(c, d, n)) for c in ciphertext)
    return text, (p, q, d), time.time() - t0


def keyspace(max_n=256, min_n=128):
    """List every (n, d) pair that the key generator can possibly produce.

    This follows the published method (primes below 40, p != q, min_n <= p*q < max_n,
    e prime and coprime to phi) and uses nothing from the real key. An attacker who knows
    the algorithm can build the same list.
    """
    primes = [p for p in range(2, 40) if isprime(p)]
    keys = set()                                       # a set removes duplicate keys
    for p in primes:
        for q in primes:
            if p != q and min_n <= p * q < max_n:
                n, phi = p * q, (p - 1) * (q - 1)
                for e in range(3, phi):
                    if isprime(e) and phi % e != 0:    # e must share no factor with phi
                        keys.add((n, pow(e, -1, phi)))
    return sorted(keys)


def readable_score(text):
    """Fraction of characters that are letters or spaces. Higher means more like English text."""
    return sum(ch.isalpha() or ch == " " for ch in text) / len(text)


def keyless_attack(ciphertext):
    """Attack B: try every possible key and keep the readable results.

    A wrong key turns the ciphertext into random-looking characters, so we keep only the
    results made entirely of printable ASCII, then rank them by how English-like they are.
    Returns (number of keys tried, ranked candidate texts, dict text -> (n, d)).
    """
    keys = keyspace()
    found = {}
    for n, d in keys:
        chars = []
        for c in ciphertext:
            m = pow(c, d, n)                           # decrypt one value with this guess
            chars.append(chr(m) if m < 128 else "\x00")  # values above 127 cannot be ASCII
        text = "".join(chars)
        if all(32 <= ord(ch) <= 126 for ch in text):   # printable ASCII only
            found.setdefault(text, (n, d))             # remember the first key that gave it
    ranked = sorted(found, key=lambda s: -readable_score(s))
    return len(keys), ranked, found


def demo(project, message):
    """Play the sender: hide `message` in a random image with the pinned project's own code."""
    # Make the target project's modules (r_channel_stego, rsa_utils, ...) importable.
    sys.path.insert(0, str(Path(project).resolve()))
    import r_channel_stego as rc

    out = Path("outputs")                       # generated files go here (ignored by git)
    out.mkdir(exist_ok=True)
    cover, stego = out / "rchannel_cover.png", out / "rchannel_stego.png"
    # A random 64 x 64 colour image is a big enough cover for a short message.
    Image.frombytes("RGB", (64, 64), os.urandom(64 * 64 * 3)).save(cover)

    pub, priv = rc.generate_small_keypair()     # the project's own (weak) key generator
    rc.embed_r_channel(str(cover), message, str(stego), pub)
    print(f"[sender]   hid {len(message)} characters; public key e={pub[0]} n={pub[1]} "
          f"({pub[1].bit_length()} bits)")
    return str(stego), pub, message


def main():
    """Run the demo, then attack the stego image both ways and report the results."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="path to the pinned image project")
    ap.add_argument("--message", default="HELLO QUANTUM", help="secret text to hide")
    args = ap.parse_args()

    stego, pub, secret = demo(args.project, args.message)

    # The attacker starts from the stego image only.
    length, ciphertext = read_red_values(stego)
    print(f"[attacker] read {length} ciphertext values from the red channel (no key used)")

    # Attack A: needs the public key (which is public by definition).
    text, (p, q, d), secs = public_key_attack(pub, ciphertext)
    print(f"[attack A] public key: factored n = {p} x {q} in {secs:.4f}s, d = {d}")
    verdict = "BREAK SUCCESSFUL" if text == secret else "BREAK FAILED"
    print(f"[attack A] DECRYPTED: {text}   ->   {verdict}")

    # Attack B: needs no key at all.
    t0 = time.time()
    tried, ranked, found = keyless_attack(ciphertext)
    print(f"[attack B] keyless: tried all {tried} possible keys in {time.time() - t0:.3f}s; "
          f"{len(ranked)} gave printable text")
    for s in ranked[:3]:                        # show the three most readable candidates
        print(f"[attack B]   candidate: {s!r}  (readable {readable_score(s):.2f})")
    best = ranked[0] if ranked else None
    print(f"[attack B] best candidate {'matches' if best == secret else 'does NOT match'} the secret")


if __name__ == "__main__":
    main()