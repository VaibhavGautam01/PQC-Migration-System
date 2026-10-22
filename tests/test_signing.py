import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pqc_stego import hybrid, signing, video_pqc

FRAMES = [random.Random(200 + i).randbytes(4000) for i in range(20)]


class TestSigning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spk, cls.ssk = signing.generate_keypair()
        cls.spk2, cls.ssk2 = signing.generate_keypair()
        cls.kpk, cls.ksk = hybrid.generate_keypair()

    def test_key_and_signature_sizes(self):
        self.assertEqual(len(self.spk), 1952)
        self.assertEqual(len(signing.attach(self.ssk, b"payload")) - len(b"payload"), 3309)

    def test_round_trip(self):
        self.assertEqual(signing.detach_and_verify(self.spk, signing.attach(self.ssk, b"payload")), b"payload")

    def test_tampered_payload_fails(self):
        data = bytearray(signing.attach(self.ssk, b"payload bytes"))
        data[-1] ^= 1
        with self.assertRaises(signing.SignatureError):
            signing.detach_and_verify(self.spk, bytes(data))

    def test_tampered_signature_fails(self):
        data = bytearray(signing.attach(self.ssk, b"payload bytes"))
        data[10] ^= 1
        with self.assertRaises(signing.SignatureError):
            signing.detach_and_verify(self.spk, bytes(data))

    def test_wrong_public_key_fails(self):
        with self.assertRaises(signing.SignatureError):
            signing.detach_and_verify(self.spk2, signing.attach(self.ssk, b"payload"))

    def test_short_data_fails(self):
        with self.assertRaises(signing.SignatureError):
            signing.detach_and_verify(self.spk, b"short")

    def test_signed_video_round_trip_and_size_effect(self):
        msg = b"signed video message"
        plain = video_pqc.hide_message(self.kpk, msg, FRAMES)
        signed = video_pqc.hide_message(self.kpk, msg, FRAMES, signer_sk=self.ssk)
        self.assertEqual(video_pqc.reveal_message(self.ksk, signed, verifier_pk=self.spk), msg)
        _, plain_body = video_pqc.reveal_body(plain)
        _, signed_body = video_pqc.reveal_body(signed)
        self.assertEqual(len(signed_body) - len(plain_body), 3309)

    def test_signed_video_tamper_fails(self):
        signed = video_pqc.hide_message(self.kpk, b"tamper me", FRAMES, signer_sk=self.ssk)
        bad = [bytes(f) for f in signed]
        f = bytearray(bad[3]); f[50] ^= 1; bad[3] = bytes(f)
        with self.assertRaises(ValueError):
            video_pqc.reveal_message(self.ksk, bad, verifier_pk=self.spk)

    def test_signed_payload_needs_verifier_and_unsigned_is_refused(self):
        msg = b"mode checks"
        signed = video_pqc.hide_message(self.kpk, msg, FRAMES, signer_sk=self.ssk)
        plain = video_pqc.hide_message(self.kpk, msg, FRAMES)
        with self.assertRaises(video_pqc.VideoFormatError):
            video_pqc.reveal_message(self.ksk, signed)
        with self.assertRaises(video_pqc.VideoFormatError):
            video_pqc.reveal_message(self.ksk, plain, verifier_pk=self.spk)

    def test_wrong_signer_fails(self):
        signed = video_pqc.hide_message(self.kpk, b"x", FRAMES, signer_sk=self.ssk2)
        with self.assertRaises(ValueError):
            video_pqc.reveal_message(self.ksk, signed, verifier_pk=self.spk)


if __name__ == "__main__":
    unittest.main()