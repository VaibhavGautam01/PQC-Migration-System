"""QKD variant of the hybrid flow: a BB84-derived 256-bit key replaces ML-KEM.

PROTOTYPE ONLY. The key comes from a SIMULATED BB84 run (Aer simulator, toy size). Real QKD needs
dedicated optical hardware, so ML-KEM stays the software-only recommendation.

Blob layout: nonce (12) | tag (16) | AES-GCM ciphertext   (overhead 28 B, no KEM ciphertext)
"""
import os

from Crypto.Cipher import AES

from pqc_stego import hybrid

NONCE_LEN = 12
TAG_LEN = 16
OVERHEAD = NONCE_LEN + TAG_LEN
INFO = b"pqc-stego v1 | BB84 | AES-256-GCM"
AAD = b"pqc-stego-qkd"


def _key(shared):
    if len(shared) != 32:
        raise ValueError("QKD key must be 32 bytes")
    return hybrid.hkdf_sha256(shared, 32, info=INFO)


def qkd_encrypt(shared, plaintext):
    nonce = os.urandom(NONCE_LEN)
    cipher = AES.new(_key(shared), AES.MODE_GCM, nonce=nonce)
    cipher.update(AAD)
    ciphertext, tag = cipher.encrypt_and_digest(plaintext)
    return nonce + tag + ciphertext


def qkd_decrypt(shared, blob):
    if len(blob) < OVERHEAD:
        raise hybrid.HybridDecryptError("blob too short")
    nonce, tag, ciphertext = blob[:NONCE_LEN], blob[NONCE_LEN:OVERHEAD], blob[OVERHEAD:]
    cipher = AES.new(_key(shared), AES.MODE_GCM, nonce=nonce)
    cipher.update(AAD)
    try:
        return cipher.decrypt_and_verify(ciphertext, tag)
    except ValueError as exc:
        raise hybrid.HybridDecryptError("authentication failed") from exc