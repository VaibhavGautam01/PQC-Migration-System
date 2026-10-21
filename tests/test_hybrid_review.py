"""
Tests for src/hybrid_review.py. These test the REVIEW TOOL, using a toy mock
(HMAC-based, NOT secure) so no PQC library is needed. A good mock must pass the
dynamic checks and deliberately flawed mocks must be caught.
"""
import hashlib
import hmac
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import hybrid_review as hr  # type: ignore # noqa: E402


def _expand(seed: bytes, n: int) -> bytes:
    out, i = b"", 0
    while len(out) < n:
        out += hashlib.sha256(seed + i.to_bytes(4, "big")).digest()
        i += 1
    return out[:n]


class Mock:
    """Toy hybrid scheme with the real sizes. Flaws can be switched on."""
    def __init__(self, fixed_nonce=False, skip_tag=False, leaky_errors=False):
        self.fixed_nonce, self.skip_tag, self.leaky = fixed_nonce, skip_tag, leaky_errors

    def keygen(self):
        sk = os.urandom(hr.SK_LEN)
        return _expand(hashlib.sha256(sk).digest(), hr.PK_LEN), sk

    def _key(self, pk, ct):
        return hmac.new(pk, ct, hashlib.sha256).digest()

    def _stream(self, key, nonce, n):
        return _expand(key + nonce, n)

    def _tag(self, key, nonce, ct):
        return hmac.new(key, nonce + ct, hashlib.sha256).digest()[:hr.TAG_LEN]

    def encrypt(self, pk, msg):
        kem_ct = os.urandom(hr.KEM_CT_LEN)
        key = self._key(pk, kem_ct)
        nonce = b"\x00" * hr.NONCE_LEN if self.fixed_nonce else os.urandom(hr.NONCE_LEN)
        ct = bytes(a ^ b for a, b in zip(msg, self._stream(key, nonce, len(msg))))
        return kem_ct + nonce + self._tag(key, nonce, ct) + ct

    def decrypt(self, sk, blob):
        if len(blob) < hr.OVERHEAD:
            if self.leaky:
                return blob[hr.OVERHEAD]          # IndexError leaks
            raise ValueError("invalid payload")
        pk = _expand(hashlib.sha256(sk).digest(), hr.PK_LEN)
        kem_ct, nonce = blob[:hr.KEM_CT_LEN], blob[hr.KEM_CT_LEN:hr.KEM_CT_LEN + hr.NONCE_LEN]
        tag, ct = blob[hr.KEM_CT_LEN + hr.NONCE_LEN:hr.OVERHEAD], blob[hr.OVERHEAD:]
        key = self._key(pk, kem_ct)
        if not self.skip_tag and not hmac.compare_digest(tag, self._tag(key, nonce, ct)):
            raise ValueError("decryption failed")
        return bytes(a ^ b for a, b in zip(ct, self._stream(key, nonce, len(ct))))

    def adapter(self):
        return hr.Adapter(self.keygen, self.encrypt, self.decrypt)


def status(results):
    return {r["id"]: r["status"] for r in results}


class TestDynamicChecks(unittest.TestCase):
    def test_good_implementation_passes_everything(self):
        st = status(hr.dynamic_checks(Mock().adapter(), n_nonces=30))
        self.assertEqual(set(st.values()), {"PASS"}, st)

    def test_fixed_nonce_is_caught(self):
        st = status(hr.dynamic_checks(Mock(fixed_nonce=True).adapter(), n_nonces=30))
        self.assertEqual(st["D4"], "FAIL")
        self.assertEqual(st["D6"], "PASS")        # payloads still differ because of the KEM ciphertext

    def test_missing_tag_check_is_caught(self):
        st = status(hr.dynamic_checks(Mock(skip_tag=True).adapter(), n_nonces=30))
        self.assertEqual(st["D7"], "FAIL")
        self.assertEqual(st["D9"], "FAIL")

    def test_leaky_errors_are_flagged(self):
        st = status(hr.dynamic_checks(Mock(leaky_errors=True).adapter(), n_nonces=30))
        self.assertIn(st["D11"], ("WARN", "FAIL"))


class TestStaticScan(unittest.TestCase):
    GOOD = '''
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256
from kyber_py.ml_kem import ML_KEM_768

INFO = b"pqc-stego v1 aes-256-gcm"

def hybrid_encrypt(pk, msg):
    ss, ct = ML_KEM_768.encaps(pk)
    key = HKDF(ss, 32, b"", SHA256, context=INFO)
    nonce = get_random_bytes(12)
    c = AES.new(key, AES.MODE_GCM, nonce=nonce)
    c.update(INFO + ct)
    body, tag = c.encrypt_and_digest(msg)
    return ct + nonce + tag + body
'''

    def ids(self, src):
        return {f["id"] for f in hr.static_findings(src)}

    def test_good_source_has_no_fail(self):
        fails = [f for f in hr.static_findings(self.GOOD) if f["severity"] == "FAIL"]
        self.assertEqual(fails, [], fails)

    def test_random_module(self):
        self.assertIn("S1", self.ids(self.GOOD + "\nimport random\nnonce = random.randbytes(12)\n"))

    def test_ecb_mode(self):
        self.assertIn("S2", self.ids(self.GOOD + "\nAES.new(key, AES.MODE_ECB)\n"))

    def test_hardcoded_nonce(self):
        self.assertIn("S3", self.ids(self.GOOD + "\nnonce = b'123456789012'\n"))

    def test_shared_secret_as_key(self):
        self.assertIn("S4", self.ids(self.GOOD + "\nAES.new(ss, AES.MODE_GCM)\n"))

    def test_no_hkdf(self):
        self.assertIn("S9", self.ids("from Crypto.Cipher import AES\nAES.MODE_GCM\nget_random_bytes(12)\n"))

    def test_logging_secrets(self):
        self.assertIn("S7", self.ids(self.GOOD + "\nprint('key', key)\n"))

    def test_assert_and_broad_except(self):
        ids = self.ids(self.GOOD + "\nassert tag\ntry:\n    pass\nexcept Exception:\n    pass\n")
        self.assertTrue({"S5", "S6"} <= ids)

    def test_missing_aad_is_info_only(self):
        src = self.GOOD.replace("    c.update(INFO + ct)\n", "")
        sev = {f["id"]: f["severity"] for f in hr.static_findings(src)}
        self.assertEqual(sev.get("S13"), "INFO")

    def test_comments_ignored(self):
        self.assertNotIn("S1", self.ids(self.GOOD + "\n# import random\n"))


if __name__ == "__main__":
    unittest.main()