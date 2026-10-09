"""
qubit_estimator.py
------------------
Estimates the number of LOGICAL qubits a quantum computer would need
to break a public-key cryptosystem using Shor's algorithm.

Formula (Beauregard's construction for factoring an n-bit modulus):
    q ≈ 2n + 3

Note: this is a logical-qubit count. Physical qubits needed on real
hardware are much higher because of error-correction overhead.
"""


def shor_logical_qubits(key_bits: int) -> int:
    """Return the estimated logical qubits to run Shor's on an n-bit key.

    Args:
        key_bits: Size of the RSA modulus in bits (e.g. 1024, 2048).

    Returns:
        Estimated logical qubits, computed as 2n + 3.

    Raises:
        ValueError: If key_bits is not a positive integer.
    """
    if isinstance(key_bits, bool) or not isinstance(key_bits, int) or key_bits <= 0:
        raise ValueError(f"key_bits must be a positive integer, got {key_bits!r}")
    return 2 * key_bits + 3


if __name__ == "__main__":
    # Dummy-key test: expected values worked out by hand
    dummy_keys = {512: 1027, 1024: 2051}

    print("Shor's algorithm: logical qubit estimate (q = 2n + 3)")
    print("-" * 52)
    for bits, expected in dummy_keys.items():
        result = shor_logical_qubits(bits)
        status = "PASS" if result == expected else "FAIL"
        print(f"{bits:>5}-bit key -> {result:>5} qubits (expected {expected}) [{status}]")
        assert result == expected, f"Mismatch for {bits}-bit key"

    # Invalid input should be rejected
    try:
        shor_logical_qubits(0)
    except ValueError:
        print("Invalid input (0) correctly rejected  [PASS]")