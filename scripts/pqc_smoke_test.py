"""Smoke test: ML-KEM, ML-DSA, AES-256-GCM. Educational libraries, not production crypto."""
import os
from kyber_py.ml_kem import ML_KEM_512, ML_KEM_768, ML_KEM_1024
from dilithium_py.ml_dsa import ML_DSA_44, ML_DSA_65, ML_DSA_87
from Crypto.Cipher import AES

EXPECTED_KEM = {  # (object, public key bytes, ciphertext bytes), FIPS 203
    "ML-KEM-512": (ML_KEM_512, 800, 768),
    "ML-KEM-768": (ML_KEM_768, 1184, 1088),
    "ML-KEM-1024": (ML_KEM_1024, 1568, 1568),
}
EXPECTED_DSA = {  # (object, public key bytes, signature bytes), FIPS 204
    "ML-DSA-44": (ML_DSA_44, 1312, 2420),
    "ML-DSA-65": (ML_DSA_65, 1952, 3309),
    "ML-DSA-87": (ML_DSA_87, 2592, 4627),
}

def check(name, got, want):
    print(f"  [{'OK ' if got == want else 'BAD'}] {name}: got {got}, expected {want}")
    return got == want

ok = True
for name, (kem, pk_len, ct_len) in EXPECTED_KEM.items():
    print(name)
    ek, dk = kem.keygen()
    shared1, ct = kem.encaps(ek)
    shared2 = kem.decaps(dk, ct)
    ok &= check("public key bytes", len(ek), pk_len)
    ok &= check("ciphertext bytes", len(ct), ct_len)
    ok &= check("shared secret matches", shared1 == shared2, True)

msg = b"smoke test message"
for name, (dsa, pk_len, sig_len) in EXPECTED_DSA.items():
    print(name)
    pk, sk = dsa.keygen()
    sig = dsa.sign(sk, msg)
    ok &= check("public key bytes", len(pk), pk_len)
    ok &= check("signature bytes", len(sig), sig_len)
    ok &= check("verify good", dsa.verify(pk, msg, sig), True)
    ok &= check("verify tampered", dsa.verify(pk, msg + b"x", sig), False)

print("AES-256-GCM")
key, nonce = os.urandom(32), os.urandom(12)
ct, tag = AES.new(key, AES.MODE_GCM, nonce=nonce).encrypt_and_digest(msg)
ok &= check("round trip", AES.new(key, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(ct, tag), msg)
try:
    bad = bytes([ct[0] ^ 1]) + ct[1:]
    AES.new(key, AES.MODE_GCM, nonce=nonce).decrypt_and_verify(bad, tag)
    ok &= check("tamper detected", False, True)
except ValueError:
    ok &= check("tamper detected", True, True)

print("\nALL OK" if ok else "\nFAILURES ABOVE")
raise SystemExit(0 if ok else 1)