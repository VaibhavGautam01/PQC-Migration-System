"""Payload size and capacity: RSA ciphertext vs ML-KEM-768 hybrid blob.

ASSUMPTIONS (replace after reading the pinned image project):
  HEADER_BYTES  framing added by the embed code (4 B in pqc_stego/image_pqc.py)
  RSA blocks    textbook RSA splits a message into blocks of at most (modulus bytes - 1)
"""
import math

HEADER_BYTES = 4
OVERHEAD = 1088 + 12 + 16  # ML-KEM ciphertext + nonce + tag
MESSAGE_LENGTHS = [16, 64, 256, 1024]
RSA_BITS = [512, 1024, 2048, 3072]
EMBED_MODES = [("1 LSB, R channel only", 1, 1), ("1 LSB, RGB", 3, 1)]  # (label, channels, LSBs)


def rsa_ciphertext_bytes(msg_len, bits):
    k = bits // 8
    return max(1, math.ceil(msg_len / (k - 1))) * k


def smallest_square_side(payload_bytes, channels, lsbs):
    pixels = math.ceil((payload_bytes + HEADER_BYTES) * 8 / (channels * lsbs))
    return math.ceil(math.sqrt(pixels))


def main():
    print(f"Assumed header: {HEADER_BYTES} B. Hybrid overhead: {OVERHEAD} B.\n")
    print("| Message (B) | RSA bits | RSA ciphertext (B) | Hybrid blob (B) | Blob / RSA |")
    print("|---|---|---|---|---|")
    for m in MESSAGE_LENGTHS:
        for bits in RSA_BITS:
            r = rsa_ciphertext_bytes(m, bits)
            h = m + OVERHEAD
            print(f"| {m} | {bits} | {r} | {h} | {h / r:.1f}x |")
    print("\n| Payload | Mode | Smallest square image (pixels per side) |")
    print("|---|---|---|")
    for m in MESSAGE_LENGTHS:
        for label, ch, lsb in EMBED_MODES:
            print(f"| hybrid, message {m} B | {label} | {smallest_square_side(m + OVERHEAD, ch, lsb)} |")
        for bits in (1024, 2048):
            r = rsa_ciphertext_bytes(m, bits)
            print(f"| RSA-{bits}, message {m} B | 1 LSB, RGB | {smallest_square_side(r, 3, 1)} |")


if __name__ == "__main__":
    main()