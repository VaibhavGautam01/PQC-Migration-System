"""ML-DSA-65 (FIPS 204) signing of the hidden payload.

PROTOTYPE ONLY: dilithium-py is educational, not hardened against timing attacks.
Production route: liboqs-python. ML-DSA is classical and quantum-resistant.

Layout: signature (3309 B) | payload. The signature covers the payload (the hybrid blob),
so verification happens BEFORE decryption and tampering is caught early.
"""
from dilithium_py.ml_dsa import ML_DSA_65

SIG_LEN = 3309
PUBLIC_KEY_LEN = 1952


class SignatureError(ValueError):
    """The signature is missing, malformed, or does not verify."""


def generate_keypair():
    """Return (public_key, secret_key)."""
    return ML_DSA_65.keygen()


def attach(secret_key, blob):
    return ML_DSA_65.sign(secret_key, blob) + blob


def detach_and_verify(public_key, data):
    if len(data) < SIG_LEN:
        raise SignatureError("data too short to hold a signature")
    sig, blob = data[:SIG_LEN], data[SIG_LEN:]
    try:
        ok = ML_DSA_65.verify(public_key, blob, sig)
    except Exception as exc:
        raise SignatureError("signature could not be checked") from exc
    if not ok:
        raise SignatureError("signature does not verify")
    return blob