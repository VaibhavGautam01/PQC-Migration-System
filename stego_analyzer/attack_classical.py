"""Stage 6b: the existing small-key attack.  Owner: Vaibhav.  (stub: not built yet)

Use the existing classical attacks (extras/stego_attack_image.py, extras/stego_attack_toy.py) on a local
small-key copy. Say what it was measured on (tool, version, time).
"""
from . import NotImplementedStage


def attack(public_key, blob):
    """public_key: {"n": int, "e": int}. blob: the extracted hex text as ASCII bytes.

    Return {"state": "broken_classical_small_key", "tool": str, "recovered_message": str}.

    Not built because the message layout of the pinned project for a non-toy modulus is not known here
    (only the toy layout in stego_analyzer/toyformat.py is). It needs extras/stego_attack_image.py and
    the pinned rsa_utils.py / rsa_lsb_stego.py. Say what it was measured on: tool, version, time.
    """
    raise NotImplementedStage("attack_classical")
