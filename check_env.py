"""
check_env.py - Q13 environment check (Tarun).
Run:  python check_env.py
Checks: Python version, pinned versions, Bell-circuit smoke test (seeded),
PQC libraries (ML-KEM, ML-DSA, AES-GCM), qiskit-ibm-runtime import.
All quantum output here: Aer simulator, toy size.
"""
import sys
from importlib import metadata

PINNED = {"qiskit": "2.5.2", "qiskit-aer": "0.17.2"}
OPTIONAL = ["kyber-py", "dilithium-py", "pycryptodome", "qiskit-ibm-runtime"]
from src.qconfig import SEED


def ver(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def main():
    ok = True
    print(f"Python {sys.version.split()[0]}")

    for name, want in PINNED.items():
        got = ver(name)
        status = "OK" if got == want else ("DIFFERENT" if got else "MISSING")
        print(f"  {name}: {got} (pinned {want}) -> {status}")
        ok &= got is not None

    # Bell circuit: only 00 and 11 should appear
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator
        qc = QuantumCircuit(2, 2)
        qc.h(0); qc.cx(0, 1); qc.measure([0, 1], [0, 1])
        sim = AerSimulator()
        tqc = transpile(qc, sim, seed_transpiler=SEED)
        counts = sim.run(tqc, shots=1000, seed_simulator=SEED).result().get_counts()
        bell_ok = set(counts) <= {"00", "11"} and sum(counts.values()) == 1000
        print(f"  Bell test (Aer simulator, toy size): {counts} -> {'OK' if bell_ok else 'FAIL'}")
        ok &= bell_ok
    except Exception as e:
        print(f"  Bell test FAILED: {e!r}")
        ok = False

    # PQC libraries (educational, pure Python)
    try:
        from kyber_py.ml_kem import ML_KEM_768
        pk, sk = ML_KEM_768.keygen()
        key, ct = ML_KEM_768.encaps(pk)
        assert ML_KEM_768.decaps(sk, ct) == key
        print(f"  ML-KEM-768 round trip OK (pk {len(pk)} B, ct {len(ct)} B)")
    except Exception as e:
        print(f"  ML-KEM-768 FAILED: {e!r}")
        ok = False
    try:
        from dilithium_py.ml_dsa import ML_DSA_65
        pk, sk = ML_DSA_65.keygen()
        sig = ML_DSA_65.sign(sk, b"msg")
        assert ML_DSA_65.verify(pk, b"msg", sig)
        print(f"  ML-DSA-65 sign/verify OK (pk {len(pk)} B, sig {len(sig)} B)")
    except Exception as e:
        print(f"  ML-DSA-65 FAILED: {e!r}")
        ok = False
    try:
        from Crypto.Cipher import AES
        import os
        k, n = os.urandom(32), os.urandom(12)
        c = AES.new(k, AES.MODE_GCM, nonce=n)
        ct, tag = c.encrypt_and_digest(b"hello")
        AES.new(k, AES.MODE_GCM, nonce=n).decrypt_and_verify(ct, tag)
        print("  AES-256-GCM round trip OK")
    except Exception as e:
        print(f"  AES-GCM FAILED: {e!r}")
        ok = False
    try:
        import qiskit_ibm_runtime  # noqa: F401
        print(f"  qiskit-ibm-runtime import OK ({ver('qiskit-ibm-runtime')})")
    except Exception as e:
        print(f"  qiskit-ibm-runtime import FAILED (only needed for Q8, Could): {e!r}")

    print("\nRESULT:", "ALL REQUIRED CHECKS PASSED" if ok else "SOME REQUIRED CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

