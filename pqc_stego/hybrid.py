"""Hybrid ML-KEM-768 + HKDF-SHA256 + AES-256-GCM.

PROTOTYPE ONLY: kyber-py is educational and not hardened against timing attacks.
Production route: liboqs-python. ML-KEM is classical and quantum-resistant, not a quantum circuit.

Blob layout: KEM ciphertext (1088) | nonce (12) | tag (16) | AES-GCM ciphertext
"""
import hashlib
import hmac
import os

from Crypto.Cipher import AES
from kyber_py.ml_kem import ML_KEM_768

KEM_CT_LEN = 1088
NONCE_LEN = 12
TAG_LEN = 16
OVERHEAD = KEM_CT_LEN + NONCE_LEN + TAG_LEN  # 1116 bytes added to the message
INFO = b"pqc-stego v1 | ML-KEM-768 | AES-256-GCM"


class HybridDecryptError(ValueError):
    """Raised when a blob is malformed, tampered with, or the key is wrong."""


def hkdf_sha256(ikm, length, salt=b"", info=b""):
    """HKDF per RFC 5869 (extract then expand) with SHA-256."""
    if length > 255 * 32:
        raise ValueError("requested length too large")
    if not salt:
        salt = b"\x00" * 32
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    okm, block, counter = b"", b"", 1
    while len(okm) < length:
        block = hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        okm += block
        counter += 1
    return okm[:length]


def generate_keypair():
    """Return (public_key, secret_key) for ML-KEM-768."""
    return ML_KEM_768.keygen()


def hybrid_encrypt(public_key, plaintext, aad=b""):
    shared, kem_ct = ML_KEM_768.encaps(public_key)
    key = hkdf_sha256(shared, 32, salt=b"", info=INFO)
    nonce = os.urandom(NONCE_LEN)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(kem_ct + aad)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return kem_ct + nonce + tag + ciphertext


def hybrid_decrypt(secret_key, blob, aad=b""):
    if len(blob) < OVERHEAD:
        raise HybridDecryptError("blob too short")
    kem_ct = blob[:KEM_CT_LEN]
    nonce = blob[KEM_CT_LEN:KEM_CT_LEN + NONCE_LEN]
    tag = blob[KEM_CT_LEN + NONCE_LEN:OVERHEAD]
    ciphertext = blob[OVERHEAD:]
    shared = ML_KEM_768.decaps(secret_key, kem_ct)  # wrong ciphertext gives a different key
    key = hkdf_sha256(shared, 32, salt=b"", info=INFO)
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    cipher.update(kem_ct + aad)
    try:
        return cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError as exc:
        raise HybridDecryptError("authentication failed") from exc