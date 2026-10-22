"""Video flow: hybrid ML-KEM-768 + AES-256-GCM split across frames with LSB embedding.

PROTOTYPE ONLY (kyber-py is educational, not hardened). ML-KEM is classical and quantum-resistant.
The LSB embedder here is a REFERENCE backend written for testing. It is NOT the pinned
video project's code. Results measured with it must say "reference backend".

frames: list of bytes-like objects (raw frame bytes, 1 hidden bit per byte).
order:  list of frame indices to fill, in order (default: 0..n-1). A frame-selection
        function (for example frame_select_v2) can supply this list.

Payload: flag (1 B: 0 plain, 1 signed) | body length (4 B, big-endian) | body
body:    hybrid blob, or ML-DSA signature + hybrid blob when signed.
"""
import struct

from pqc_stego import hybrid

AAD = b"pqc-stego-video"
HEADER_BYTES = 5
FLAG_PLAIN, FLAG_SIGNED = 0, 1


class VideoCapacityError(ValueError):
    """The frames are too small for the payload."""


class VideoFormatError(ValueError):
    """The hidden data is not a plausible payload."""


def frame_capacity(frame):
    return len(frame) // 8


def _check_order(frames, order):
    if order is None:
        return list(range(len(frames)))
    order = list(order)
    if len(set(order)) != len(order) or any(not 0 <= i < len(frames) for i in order):
        raise ValueError("order must list distinct valid frame indices")
    return order


def total_capacity(frames, order=None):
    return sum(frame_capacity(frames[i]) for i in _check_order(frames, order))


def _embed(frame, data):
    out = bytearray(frame)
    for i, byte in enumerate(data):
        for j in range(8):
            k = i * 8 + j
            out[k] = (out[k] & 0xFE) | ((byte >> (7 - j)) & 1)
    return bytes(out)


def _extract(frame, nbytes):
    out = bytearray(nbytes)
    for i in range(nbytes):
        value = 0
        for j in range(8):
            value = (value << 1) | (frame[i * 8 + j] & 1)
        out[i] = value
    return bytes(out)


def _write_stream(frames, order, payload):
    out = [bytes(f) for f in frames]
    pos = 0
    for idx in order:
        if pos >= len(payload):
            break
        chunk = payload[pos:pos + frame_capacity(frames[idx])]
        out[idx] = _embed(frames[idx], chunk)
        pos += len(chunk)
    if pos < len(payload):
        raise VideoCapacityError(f"payload is {len(payload)} B, capacity is {total_capacity(frames, order)} B")
    return out


def _read_stream(frames, order, nbytes):
    data = bytearray()
    for idx in order:
        if len(data) >= nbytes:
            break
        take = min(frame_capacity(frames[idx]), nbytes - len(data))
        data += _extract(frames[idx], take)
    if len(data) < nbytes:
        raise VideoFormatError("not enough frame capacity for the stated length")
    return bytes(data)


def hide_message(public_key, message, frames, order=None, signer_sk=None):
    order = _check_order(frames, order)
    body = hybrid.hybrid_encrypt(public_key, message, aad=AAD)
    flag = FLAG_PLAIN
    if signer_sk is not None:
        from pqc_stego import signing
        body = signing.attach(signer_sk, body)
        flag = FLAG_SIGNED
    return _write_stream(frames, order, struct.pack(">BI", flag, len(body)) + body)


def reveal_body(frames, order=None):
    """Extract the hidden body. Needs no secret: the embedding here is keyless."""
    order = _check_order(frames, order)
    flag, length = struct.unpack(">BI", _read_stream(frames, order, HEADER_BYTES))
    if flag not in (FLAG_PLAIN, FLAG_SIGNED):
        raise VideoFormatError("unknown flag")
    if length < hybrid.OVERHEAD or HEADER_BYTES + length > total_capacity(frames, order):
        raise VideoFormatError("hidden length is not plausible")
    return flag, _read_stream(frames, order, HEADER_BYTES + length)[HEADER_BYTES:]


def reveal_message(secret_key, frames, order=None, verifier_pk=None):
    flag, body = reveal_body(frames, order)
    if verifier_pk is not None:
        if flag != FLAG_SIGNED:
            raise VideoFormatError("expected a signed payload")
        from pqc_stego import signing
        body = signing.detach_and_verify(verifier_pk, body)
    elif flag == FLAG_SIGNED:
        raise VideoFormatError("signed payload: a verifier public key is required")
    return hybrid.hybrid_decrypt(secret_key, body, aad=AAD)