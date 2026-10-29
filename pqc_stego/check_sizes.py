"""Compare real key/ciphertext/signature sizes with the plan's Section 6 table."""
from kyber_py.ml_kem import ML_KEM_512, ML_KEM_768, ML_KEM_1024
from dilithium_py.ml_dsa import ML_DSA_44, ML_DSA_65, ML_DSA_87

EXPECTED_KEM = {  # name: (public key, ciphertext)
    "ML-KEM-512": (800, 768),
    "ML-KEM-768": (1184, 1088),
    "ML-KEM-1024": (1568, 1568),
}
EXPECTED_DSA = {  # name: (public key, signature)
    "ML-DSA-44": (1312, 2420),
    "ML-DSA-65": (1952, 3309),
    "ML-DSA-87": (2592, 4627),
}
KEMS = {"ML-KEM-512": ML_KEM_512, "ML-KEM-768": ML_KEM_768, "ML-KEM-1024": ML_KEM_1024}
DSAS = {"ML-DSA-44": ML_DSA_44, "ML-DSA-65": ML_DSA_65, "ML-DSA-87": ML_DSA_87}

ok = True
for name, alg in KEMS.items():
    ek, dk = alg.keygen()
    _, ct = alg.encaps(ek)
    got, want = (len(ek), len(ct)), EXPECTED_KEM[name]
    ok &= got == want
    print(f"{name:12} pk/ct {got} expected {want} {'OK' if got == want else 'MISMATCH'}")
for name, alg in DSAS.items():
    pk, sk = alg.keygen()
    sig = alg.sign(sk, b"x")
    got, want = (len(pk), len(sig)), EXPECTED_DSA[name]
    ok &= got == want
    print(f"{name:12} pk/sig {got} expected {want} {'OK' if got == want else 'MISMATCH'}")
raise SystemExit(0 if ok else 1)
