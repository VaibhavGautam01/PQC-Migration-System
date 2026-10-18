"""Image flow: hybrid ML-KEM-768 + AES-256-GCM hidden with LSB embedding.

PROTOTYPE ONLY (kyber-py is educational, not hardened). ML-KEM is classical and quantum-resistant.

Backends:
  REFERENCE_BACKEND  a simple LSB embedder written for testing. NOT the pinned project's code.
  load_pinned_backend()  wraps functions from the pinned image project, loaded by file path.
                         We never edit the pinned repository.

A backend is a pair of functions:
  embed(cover: bytes, data: bytes) -> bytes        returns the stego pixel bytes
  extract(stego: bytes, nbytes: int) -> bytes      returns the first nbytes hidden bytes

Framing: 4-byte big-endian blob length, then the hybrid blob.
"""
import importlib.util
import struct
from collections import namedtuple
from pathlib import Path

from pqc_stego import hybrid

Backend = namedtuple("Backend", "name embed extract")
HEADER_BYTES = 4


class ImageCapacityError(ValueError):
    """The cover image is too small for the payload, or the hidden length is not plausible."""


def _ref_embed(cover, data):
    if len(data) * 8 > len(cover):
        raise ImageCapacityError(f"need {len(data) * 8} cover bytes, have {len(cover)}")
    out = bytearray(cover)
    for i, byte in enumerate(data):
        for j in range(8):
            idx = i * 8 + j
            out[idx] = (out[idx] & 0xFE) | ((byte >> (7 - j)) & 1)
    return bytes(out)


def _ref_extract(stego, nbytes):
    if nbytes * 8 > len(stego):
        raise ImageCapacityError("hidden length larger than the image")
    data = bytearray(nbytes)
    for i in range(nbytes):
        value = 0
        for j in range(8):
            value = (value << 1) | (stego[i * 8 + j] & 1)
        data[i] = value
    return bytes(data)


REFERENCE_BACKEND = Backend("reference-lsb (test stand-in, not pinned code)", _ref_embed, _ref_extract)


def load_pinned_backend(py_file, embed_name, extract_name):
    """Load embed/extract functions from the pinned project by file path.

    The pinned functions must match the backend signatures above. If they do not,
    write small wrapper functions around them and pass those instead.
    """
    spec = importlib.util.spec_from_file_location("pinned_image_module", str(Path(py_file)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return Backend(f"pinned:{Path(py_file).name}", getattr(module, embed_name), getattr(module, extract_name))


def capacity_bytes(cover_len):
    """Largest hybrid blob that fits in a cover of cover_len bytes (1 bit per byte)."""
    return max(0, cover_len // 8 - HEADER_BYTES)


def hide_message(public_key, message, cover, backend=REFERENCE_BACKEND):
    blob = hybrid.hybrid_encrypt(public_key, message)
    if len(blob) > capacity_bytes(len(cover)):
        raise ImageCapacityError(f"blob is {len(blob)} B, capacity is {capacity_bytes(len(cover))} B")
    return backend.embed(cover, struct.pack(">I", len(blob)) + blob)


def reveal_blob(stego, backend=REFERENCE_BACKEND):
    """Extract the hidden blob. Needs no secret: LSB embedding here is keyless."""
    (length,) = struct.unpack(">I", backend.extract(stego, HEADER_BYTES))
    if length < hybrid.OVERHEAD or length > capacity_bytes(len(stego)):
        raise ImageCapacityError("hidden length is not plausible")
    return backend.extract(stego, HEADER_BYTES + length)[HEADER_BYTES:]


def reveal_message(secret_key, stego, backend=REFERENCE_BACKEND):
    return hybrid.hybrid_decrypt(secret_key, reveal_blob(stego, backend))