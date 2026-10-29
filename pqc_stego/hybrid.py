"""Hybrid ML-KEM-768 + HKDF + AES-256-GCM.

Educational libraries (kyber-py, PyCryptodome): not hardened against timing attacks.
Blob layout: KEM ciphertext (1088) | nonce (12) | tag (16) | AES ciphertext.
"""
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF
from Crypto.Random import get_random_bytes
from kyber_py.ml_kem import ML_KEM_768

KEM_CT_LEN = 1088
NONCE_LEN = 12
TAG_LEN = 16
HEADER_LEN = KEM_CT_LEN + NONCE_LEN + TAG_LEN   # 1116
HKDF_INFO = b"pqc_stego hybrid v1 ML-KEM-768 AES-256-GCM"


def generate_keypair():
    """Receiver keypair: (encapsulation key, decapsulation key)."""
    return ML_KEM_768.keygen()


def _derive_key(shared_secret: bytes) -> bytes:
    return HKDF(shared_secret, 32, salt=None, hashmod=SHA256, context=HKDF_INFO)


def hybrid_encrypt(receiver_ek: bytes, message: bytes) -> bytes:
    shared, kem_ct = ML_KEM_768.encaps(receiver_ek)
    nonce = get_random_bytes(NONCE_LEN)          # fresh random nonce per message
    cipher = AES.new(_derive_key(shared), AES.MODE_GCM, nonce=nonce, mac_len=TAG_LEN)
    ct, tag = cipher.encrypt_and_digest(message)
    return kem_ct + nonce + tag + ct


def hybrid_decrypt(receiver_dk: bytes, blob: bytes) -> bytes:
    if len(blob) < HEADER_LEN:
        raise ValueError("blob too short for ML-KEM-768 hybrid payload")
    kem_ct = blob[:KEM_CT_LEN]
    nonce = blob[KEM_CT_LEN:KEM_CT_LEN + NONCE_LEN]
    tag = blob[KEM_CT_LEN + NONCE_LEN:HEADER_LEN]
    ct = blob[HEADER_LEN:]
    shared = ML_KEM_768.decaps(receiver_dk, kem_ct)
    cipher = AES.new(_derive_key(shared), AES.MODE_GCM, nonce=nonce, mac_len=TAG_LEN)
    return cipher.decrypt_and_verify(ct, tag)    # raises ValueError if anything was changed
