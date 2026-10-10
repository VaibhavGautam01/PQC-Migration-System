"""
validate_qubit_costs.py - Shor qubit-cost ki independent manual check (Issue #7)

Kaam: findings.json ke verified modulus sizes se qubits khud recalculate
karna (q = 2n + 3), aur haath se nikale numbers se match karna.
Usage: python validate_qubit_costs.py [outputs/findings.json]
Exit code: 0 = sab match, 1 = koi mismatch
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

# Haath se nikale numbers (Day 1 ke verified moduli, q = 2n + 3):
#   n = 256  -> 2*256  + 3 = 515
#   n = 512  -> 2*512  + 3 = 1027
#   n = 1024 -> 2*1024 + 3 = 2051
BY_HAND = {256: 515, 512: 1027, 1024: 2051}


def shor_qubits(n_bits):
    """Shor ke liye logical qubits: 2n + 3, n = modulus ke bits."""
    return 2 * n_bits + 3


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "outputs/findings.json"
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    # Project-wise RSA modulus sizes jama karo.
    # key_size per-prime hota hai, isliye sirf modulus_bits use karo.
    sizes = defaultdict(set)
    for f in data["findings"]:
        n = f.get("modulus_bits")
        if str(f.get("primitive", "")).upper() == "RSA" and isinstance(n, int):
            sizes[f.get("project", "?")].add(n)

    failed = False
    print(f"{'PROJECT':<28}{'n(bits)':<10}{'script':<9}{'by hand':<9}RESULT")
    for project, ns in sorted(sizes.items()):
        for n in sorted(ns):
            calc = shor_qubits(n)
            hand = BY_HAND.get(n)
            ok = hand == calc
            failed = failed or not ok
            result = "MATCH" if ok else "MISMATCH / hand value missing"
            print(f"{project:<28}{n:<10}{calc:<9}{str(hand):<9}{result}")

    # Sanity: koi RSA size mila hi nahi to bhi fail, warna khali pass hoga.
    if not sizes:
        print("ERROR: koi RSA modulus_bits nahi mila.")
        return 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
