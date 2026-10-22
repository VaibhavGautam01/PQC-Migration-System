"""
layer_presets.py
----------------
One place that says how each primitive used in the two projects is described to
the scoring engine (risk_score.score_layer). Every claim about a primitive lives
here, so a change of mind (for example a new F4 category) touches one file.

A preset gives the F1 category, the F4 construction and, for symmetric
primitives, the effective strength after Grover's halving. The exposure (F6) and
the RSA modulus size depend on the project and are passed in.

PROVISIONAL presets use the closest existing F4 category; the note says why.
The weights file is frozen (v1.0): a new category would be a new key in it, with a
change-log row and a new lock.
"""
from risk_score import score_layer

PRESETS = {
    "rsa_textbook": dict(category="shor_broken", construction="no_padding_deterministic", needs_bits=True,
                         note="textbook RSA: no padding, deterministic"),
    "rsa_oaep": dict(category="shor_broken", construction="oaep", needs_bits=True,
                     note="RSA encryption with OAEP padding"),
    "rsa_signature_pss": dict(category="shor_broken", construction="oaep", needs_bits=True, provisional=True,
                              note="RSA signature with PSS padding, scored like a padded construction (F4 = oaep)"),
    "ml_kem_768_aes_256_gcm": dict(category="nist_pqc", construction="aead",
                                   note="ML-KEM-768 key transport, HKDF, AES-256-GCM (plan section 4: F1 = 5)"),
    "ml_dsa_65": dict(category="nist_pqc", construction="aead", provisional=True,
                      note="ML-DSA-65 signature; F4 = aead is the closest existing category, not literally AEAD"),
    "slh_dsa": dict(category="nist_pqc", construction="aead", provisional=True,
                    note="SLH-DSA signature; same closest-category choice as ML-DSA"),
    "sha256_passphrase_frame_key": dict(category="symmetric", effective_bits=128,
                                        construction="deterministic_or_oracle",
                                        note="unsalted SHA-256 of a passphrase, no key stretching (decision by Tarun)"),
    "random_key_frame_selection_v2": dict(category="symmetric", effective_bits=128, construction="aead",
                                          provisional=True,
                                          note="random 256-bit key with HMAC-SHA256; F4 = aead is the closest existing category"),
    "crc32_integrity": dict(category="none", construction="deterministic_or_oracle",
                            note="CRC32 is not cryptographic; it works as a key-check oracle"),
}


def preset_names():
    return sorted(PRESETS)


def is_provisional(name: str) -> bool:
    return bool(_get(name).get("provisional", False))


def _get(name):
    if name not in PRESETS:
        raise ValueError(f"unknown preset {name!r}; use one of {preset_names()}")
    return PRESETS[name]


def score_preset(name: str, exposure: str, modulus_bits=None, weights=None, **overrides) -> dict:
    """Score a named primitive with the same engine; returns score_layer's result."""
    p = _get(name)
    if p.get("needs_bits") and modulus_bits is None:
        raise ValueError(f"preset {name!r} needs modulus_bits")
    kw = dict(category=p["category"], construction=p["construction"], exposure=exposure,
              modulus_bits=modulus_bits if p.get("needs_bits") else None,
              effective_bits=p.get("effective_bits"), weights=weights)
    kw.update(overrides)
    return score_layer(**kw)