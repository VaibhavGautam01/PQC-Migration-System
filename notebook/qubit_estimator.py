"""
qubit_estimator.py
------------------
Estimates the resources a quantum computer would need to attack
cryptographic primitives.

1. Shor's algorithm (asymmetric: RSA, ECC, DH, DSA)
   Logical qubits for an n-bit modulus (Beauregard's construction):
       q ≈ 2n + 3
   Shor's gives a FULL BREAK (polynomial time).

2. Grover's algorithm (symmetric: AES, hash functions)
   Effective security of a k-bit key is HALVED:
       effective_bits ≈ k / 2
   Grover's gives only a QUADRATIC speed-up, not a full break.

Note: all qubit counts are LOGICAL qubits. Physical qubits needed on
real hardware are much higher because of error-correction overhead.
"""

# Logical qubits for Grover's attack on AES, from published resource
# estimates (Grassl et al., 2016). Verify against the paper before
# citing in the final report.
GROVER_AES_LOGICAL_QUBITS = {
    128: 2953,
    192: 4449,
    256: 6681,
}


def _validate_bits(value, name="key_bits"):
    """Raise ValueError unless value is a positive integer."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")


def shor_logical_qubits(key_bits: int) -> int:
    """Return the estimated logical qubits to run Shor's on an n-bit key.

    Args:
        key_bits: Size of the RSA modulus in bits (e.g. 1024, 2048).

    Returns:
        Estimated logical qubits, computed as 2n + 3.

    Raises:
        ValueError: If key_bits is not a positive integer.
    """
    _validate_bits(key_bits)
    return 2 * key_bits + 3


def grover_effective_security(key_bits: int) -> int:
    """Return the effective security (in bits) of a symmetric key under Grover's.

    Grover's searches 2^k keys in about 2^(k/2) steps, so the effective
    security is k / 2.

    Args:
        key_bits: Symmetric key size in bits (e.g. 128, 256).

    Returns:
        Effective security in bits after Grover's speed-up.

    Raises:
        ValueError: If key_bits is not a positive integer.
    """
    _validate_bits(key_bits)
    return key_bits // 2


def grover_logical_qubits(key_bits: int):
    """Return the logical qubits for Grover's attack on AES with this key size.

    Args:
        key_bits: AES key size in bits (128, 192 or 256).

    Returns:
        Logical qubit count from the published table, or None if the
        key size has no published estimate.

    Raises:
        ValueError: If key_bits is not a positive integer.
    """
    _validate_bits(key_bits)
    return GROVER_AES_LOGICAL_QUBITS.get(key_bits)


def grover_verdict(key_bits: int) -> str:
    """Return a short risk verdict for a symmetric key under Grover's.

    Rule of thumb: effective security of 128 bits or more is considered safe.
    """
    effective = grover_effective_security(key_bits)
    if effective >= 128:
        return "SAFE (effective security >= 128 bits)"
    return "WEAKENED (effective security < 128 bits; upgrade to a larger key)"


if __name__ == "__main__":
    print("Shor's algorithm: logical qubit estimate (q = 2n + 3)")
    print("-" * 52)
    for bits, expected in {512: 1027, 1024: 2051}.items():
        result = shor_logical_qubits(bits)
        status = "PASS" if result == expected else "FAIL"
        print(f"{bits:>5}-bit key -> {result:>5} qubits (expected {expected}) [{status}]")
        assert result == expected, f"Mismatch for {bits}-bit key"

    print()
    print("Grover's algorithm: symmetric keys")
    print("-" * 52)
    # (key size, expected effective security)
    for bits, expected_eff in [(128, 64), (192, 96), (256, 128)]:
        eff = grover_effective_security(bits)
        qubits = grover_logical_qubits(bits)
        status = "PASS" if eff == expected_eff else "FAIL"
        print(f"AES-{bits}: effective {eff:>3} bits, {qubits} qubits, "
              f"{grover_verdict(bits)} [{status}]")
        assert eff == expected_eff, f"Mismatch for AES-{bits}"

    assert grover_logical_qubits(100) is None  # no published estimate

    for bad in (0, -5, 1.5, "128"):
        for fn in (shor_logical_qubits, grover_effective_security):
            try:
                fn(bad)
                raise AssertionError(f"{fn.__name__}({bad!r}) should fail")
            except ValueError:
                pass
    print("\nInvalid inputs correctly rejected [PASS]")