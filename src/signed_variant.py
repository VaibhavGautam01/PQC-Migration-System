"""
signed_variant.py
-----------------
Scores the signature layer (L5) and the signed variants of both projects with
the SAME engine (risk_score via layer_presets). Week 3 Day 3.

  python src/signed_variant.py
  python src/signed_variant.py --image-bits 256 --video-bits 2048

Rules used (see docs/risk_model.md):
  * a layer with no cryptography is NOT scored ("no protection"), so a missing
    signature is not a score;
  * the project score is 0.7 x worst layer + 0.3 x average of the scored layers;
  * in the migrated setups the integrity layer is the AES-GCM tag inside L1, so it
    is not scored as a separate layer.
Provisional presets (closest existing F4 category) are marked with *.
Weighted score, not a probability. Formulas only; no simulator result.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from layer_presets import is_provisional, score_preset  # noqa: E402
from risk_score import project_score  # noqa: E402

SIGNATURE_OPTIONS = ("rsa_signature_pss", "ml_dsa_65", "slh_dsa")


def signature_table(exposure: str, rsa_bits: int = 2048) -> list:
    rows = [{"option": "none", "overall": None, "band": "not scored (no protection)"}]
    for name in SIGNATURE_OPTIONS:
        r = score_preset(name, exposure, modulus_bits=rsa_bits)
        rows.append({"option": name + ("*" if is_provisional(name) else ""), "overall": r["overall"],
                     "quantum": r["quantum"], "classical": r["classical"], "band": r["band"]})
    return rows


def project_variants(image_bits: int = 256, video_bits: int = 2048) -> dict:
    """Layer scores and project scores: before, migrated unsigned, migrated signed."""
    def layers(spec):
        return {label: score_preset(name, exp, modulus_bits=bits)["overall"] for label, (name, exp, bits) in spec.items()}

    image_exp, video_exp = "keyless", "bypassable"
    spec = {
        "image": {
            "before": {"L1 RSA textbook": ("rsa_textbook", image_exp, image_bits)},
            "unsigned": {"L1 ML-KEM-768 + AES-GCM": ("ml_kem_768_aes_256_gcm", image_exp, None)},
            "signed": {"L1 ML-KEM-768 + AES-GCM": ("ml_kem_768_aes_256_gcm", image_exp, None),
                       "L5 ML-DSA-65": ("ml_dsa_65", image_exp, None)},
        },
        "video": {
            "before": {"L1 RSA textbook": ("rsa_textbook", video_exp, video_bits),
                       "L2 SHA-256 passphrase key": ("sha256_passphrase_frame_key", video_exp, None),
                       "L3 CRC32": ("crc32_integrity", video_exp, None)},
            "unsigned": {"L1 ML-KEM-768 + AES-GCM": ("ml_kem_768_aes_256_gcm", video_exp, None),
                         "L2 random-key frame selection v2": ("random_key_frame_selection_v2", video_exp, None)},
            "signed": {"L1 ML-KEM-768 + AES-GCM": ("ml_kem_768_aes_256_gcm", video_exp, None),
                       "L2 random-key frame selection v2": ("random_key_frame_selection_v2", video_exp, None),
                       "L5 ML-DSA-65": ("ml_dsa_65", video_exp, None)},
        },
    }
    out = {}
    for project, states in spec.items():
        out[project] = {}
        for state, s in states.items():
            lay = layers(s)
            out[project][state] = {"layers": lay, "project": project_score(lay.values())}
    return out


def print_report(image_bits, video_bits):
    print("Signature layer (L5), image exposure keyless, RSA-2048 for the RSA option (* = provisional category)")
    for r in signature_table("keyless"):
        val = "-" if r["overall"] is None else f"{r['overall']:.1f}"
        print(f"  {r['option']:<22}{val:>6}  {r['band']}")
    res = project_variants(image_bits, video_bits)
    for project in ("image", "video"):
        print(f"\n{project.capitalize()} project")
        for state in ("before", "unsigned", "signed"):
            s = res[project][state]
            parts = ", ".join(f"{k} {v:.1f}" for k, v in s["layers"].items())
            print(f"  {state:<9} project {s['project']:5.1f}   [{parts}]")
        d = res[project]["unsigned"]["project"] - res[project]["signed"]["project"]
        print(f"  adding the signature layer lowers the project score by {d:.2f} points (averaging effect)")
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--image-bits", type=int, default=256)
    ap.add_argument("--video-bits", type=int, default=2048)
    a = ap.parse_args()
    print_report(a.image_bits, a.video_bits)