"""The toy-RSA stego format of extras/stego_attack_toy.py, used by the analyzer's toy-size stages.

Each ASCII character is split into two base-N digits (each below N); every digit is RSA-encrypted; the
ciphertexts are written as fixed-width hex and hidden with the image project's own LSB routine. The
attacker holds the stego image and the PUBLIC key (e, N): the image does not carry N.
"""


def hex_width(n):
    """Hex characters per ciphertext block for modulus n (same rule as extras/stego_attack_image.py)."""
    return ((n.bit_length() + 7) // 8) * 2


def is_hex(text):
    return bool(text) and all(c in "0123456789abcdefABCDEF" for c in text)


def split_blocks(hex_text, n):
    """Cut the hex string into ciphertext integers, or None if the layout does not fit this modulus."""
    w = hex_width(n)
    if not is_hex(hex_text) or len(hex_text) % w:
        return None
    blocks = [int(hex_text[i:i + w], 16) for i in range(0, len(hex_text), w)]
    return blocks if all(b < n for b in blocks) else None


def encode(text, n):
    """char -> two base-n digits, all below n."""
    digits = []
    for ch in text:
        c = ord(ch)
        if c >= 128:
            raise ValueError("ASCII only")
        digits += [c // n, c % n]
    return digits


def decode(digits, n):
    """Rebuild text from base-n digit pairs."""
    if len(digits) % 2:
        raise ValueError("odd number of digits")
    return "".join(chr(digits[i] * n + digits[i + 1]) for i in range(0, len(digits), 2))


def encrypt_blocks(text, e, n):
    """The sender side: hex string to hide in the image."""
    w = hex_width(n)
    return "".join(format(pow(m, e, n), f"0{w}x") for m in encode(text, n))
