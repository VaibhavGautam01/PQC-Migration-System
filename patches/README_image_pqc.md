# image_pqc.diff

Replaces RSA key transport in the image project with ML-KEM-768 + HKDF + AES-256-GCM (pqc_stego/hybrid.py).

Applies to: final-year-part1 at commit bb6d944. The pinned repository itself is never edited.

## Apply
    git clone URL final-year-part1
    cd final-year-part1
    git checkout bb6d944
    git apply --check path/to/patches/image_pqc.diff
    git apply path/to/patches/image_pqc.diff

## Check behaviour
    python -m unittest discover -s tests -p "test_image_equivalence.py" -v

## Warnings
- kyber-py is educational and not hardened against timing attacks. Production route: liboqs-python.
- The hybrid blob is much larger than an RSA ciphertext and may be easier to detect. See docs/pqc_placement.md.
- Results here were measured on: ____ (reference backend or pinned commit).