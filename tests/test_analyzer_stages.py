"""Tests of the analyzer stages that are built: extract, detect, identify, estimate, the Shor stage, exports."""
import csv
import json
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest import mock

from src import quantum_guard as guard
from src import quantum_runs as QR
from stego_analyzer import cipher_identify, detect_method, estimate, extract, pipeline as sa, quantum_stage, report, schema, toyformat
from tests.slow import slow
from tests.test_shor_run_record import fake_record

ROOT = Path(__file__).resolve().parent.parent
TOY_KEYS = {15: (3, 5), 21: (3, 7), 35: (5, 7)}

FAKE_PINNED = '''
def extract_lsb(path):
    data = open(path, "rb").read()
    if not data.startswith(b"HEX:"):
        raise ValueError("no payload")
    return data[4:].decode()
'''


def public_key(n):
    from math import gcd
    p, q = TOY_KEYS[n]
    phi = (p - 1) * (q - 1)
    e = next(x for x in range(3, phi) if gcd(x, phi) == 1)
    return {"n": n, "e": e}


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pinned = self.root / "pinned"
        self.pinned.mkdir()
        (self.pinned / "lsb_stego.py").write_text(FAKE_PINNED, encoding="utf-8")
        patch = mock.patch.object(extract, "PINNED_DIR", self.pinned)
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

    def image(self, name, hex_text=None):
        p = self.root / name
        p.write_bytes(b"HEX:" + hex_text.encode() if hex_text is not None else b"plain cover, nothing hidden")
        return p

    def toy_image(self, n, text="HELLO"):
        key = public_key(n)
        return self.image(f"toy{n}.png", toyformat.encrypt_blocks(text, key["e"], n)), key


class ExtractAndDetect(Workspace):
    def test_hex_payload_is_extracted_as_ascii_bytes(self):
        img = self.image("a.png", "0a0b0c")
        out = extract.extract(img, "lsb")
        self.assertEqual((out["ok"], out["blob"]), (True, b"0a0b0c"))
        self.assertIn("by path", out["source"])

    def test_image_without_a_payload_is_not_extracted(self):
        out = extract.extract(self.image("b.png"), "lsb")
        self.assertEqual((out["ok"], out["blob"]), (False, b""))

    def test_other_methods_are_not_covered(self):
        from stego_analyzer import NotImplementedStage
        with self.assertRaises(NotImplementedStage):
            extract.extract(self.image("c.png", "00"), "xor_lsb")

    def test_missing_pinned_project_is_a_clear_error(self):
        with mock.patch.object(extract, "PINNED_DIR", self.root / "nowhere"):
            with self.assertRaises(FileNotFoundError):
                detect_method.detect(self.image("d.png", "00"))

    def test_detect_says_lsb_for_our_format_and_unknown_otherwise(self):
        self.assertEqual(detect_method.detect(self.image("e.png", "00ff"))["method"], "lsb")
        self.assertEqual(detect_method.detect(self.image("f.png"))["method"], "clean_or_unknown")

    def test_detect_claims_no_confidence(self):
        d = detect_method.detect(self.image("g.png", "00ff"))
        self.assertIsNone(d["confidence"])
        self.assertIn("our own format", d["basis"])


class Identify(Workspace):
    def test_toy_rsa_blob_with_its_public_key_is_textbook_rsa(self):
        img, key = self.toy_image(21)
        blob = extract.extract(img, "lsb")["blob"]
        c = cipher_identify.identify(blob, key)
        self.assertEqual((c["kind"], c["n"], c["modulus_bits"]), ("textbook_rsa", 21, 5))

    def test_the_same_blob_with_another_modulus_is_not_textbook(self):
        img, key = self.toy_image(35)
        blob = extract.extract(img, "lsb")["blob"]
        wrong = {"n": 15, "e": 7}
        self.assertNotEqual(cipher_identify.identify(blob, wrong)["kind"], "textbook_rsa")

    def test_rsa_blob_without_a_public_key_is_not_guessed(self):
        img, _ = self.toy_image(15)
        self.assertEqual(cipher_identify.identify(extract.extract(img, "lsb")["blob"])["kind"], "unrecognised")

    def test_long_blob_is_recognised_as_ml_kem_by_length_only(self):
        blob = ("ab" * (1116 + 4)).encode()
        c = cipher_identify.identify(blob)
        self.assertEqual(c["kind"], "ml_kem_aes_gcm")
        self.assertIn("length only", c["evidence"])

    def test_short_or_non_hex_blob_is_unrecognised(self):
        self.assertEqual(cipher_identify.identify(b"abcd")["kind"], "unrecognised")
        self.assertEqual(cipher_identify.identify(b"zz" * 600)["kind"], "unrecognised")


class Estimate(unittest.TestCase):
    def test_2048_has_the_published_figure_labelled_estimate(self):
        e = estimate.estimate(2048)
        self.assertEqual(e["logical_qubits_2n_plus_3"], 4099)
        self.assertIn("ESTIMATE", e["published"])
        self.assertIn("20,000,000", e["published"])

    def test_size_without_a_published_figure_says_so(self):
        e = estimate.estimate(1024)
        self.assertIn("no published figure", e["published"])
        self.assertIn("ESTIMATE", e["published"])

    def test_estimate_block_has_no_time_key(self):
        for bits in (512, 1024, 2048):
            for key in estimate.estimate(bits):
                self.assertFalse(any(w in key.lower() for w in schema.TIME_WORDS), key)


class ShorStage(Workspace):
    def fake_shor(self, factors):
        def run(a, n, shots):
            rec = fake_record(n, a, factors, f"t{a}")
            from q2_shor import build_shor_ipea  # noqa: F401  (src is on sys.path through shor_run)
            return rec, build_shor_ipea(a, n)
        return run

    def attack(self, n, shor, text="HELLO"):
        img, key = self.toy_image(n, text)
        blob = extract.extract(img, "lsb")["blob"]
        return quantum_stage.attack_toy(key, blob, record_path=self.root / "runs.json",
                                        diagram_dir=self.root / "diag", shor=shor), key

    def test_factors_measured_by_the_circuit_decrypt_the_message(self):
        quantum_stage._shor_run()                         # puts src/ on sys.path
        out, _ = self.attack(15, self.fake_shor((3, 5)))
        self.assertEqual(out["state"], "broken_toy")
        self.assertEqual(out["recovered_message"], "HELLO")
        self.assertEqual(out["label"], "Aer simulator, toy size")
        self.assertEqual(out["factors"], [3, 5])

    def test_every_run_is_saved_as_a_valid_evidence_record(self):
        quantum_stage._shor_run()
        out, _ = self.attack(21, self.fake_shor((3, 7)))
        runs = QR.load_runs(self.root / "runs.json")
        self.assertEqual(len(runs), len(out["runs_tried"]))
        self.assertTrue(all(QR.validate_run(r) == [] for r in runs))
        self.assertEqual(runs[-1]["run_id"], out["run_id"])
        self.assertTrue((self.root / "diag").is_dir())

    def test_a_failed_base_is_saved_and_the_next_base_is_tried(self):
        quantum_stage._shor_run()
        good = self.fake_shor((3, 5))
        calls = []

        def run(a, n, shots):
            rec, qc = good(a, n, shots)
            calls.append(a)
            if len(calls) == 1:
                rec["factors_found"], rec["success_rate"] = {}, 0.0
            return rec, qc

        out, _ = self.attack(15, run)
        self.assertEqual(len(out["runs_tried"]), 2)
        self.assertEqual(len(QR.load_runs(self.root / "runs.json")), 2)

    def test_no_factors_anywhere_raises_instead_of_guessing(self):
        quantum_stage._shor_run()
        good = self.fake_shor((3, 5))

        def never(a, n, shots):
            rec, qc = good(a, n, shots)
            rec["factors_found"], rec["success_rate"] = {}, 0.0
            return rec, qc

        with self.assertRaises(RuntimeError):
            self.attack(15, never)

    def test_blob_that_does_not_fit_the_key_is_refused(self):
        with self.assertRaises(ValueError):
            quantum_stage.attack_toy({"n": 15, "e": 7}, b"zz", record_path=self.root / "r.json")

    def test_the_circuit_gets_the_modulus_from_the_public_key_and_it_changes_with_it(self):
        quantum_stage._shor_run()
        seen = []
        for n, f in ((15, (3, 5)), (21, (3, 7)), (35, (5, 7))):
            inner = self.fake_shor(f)

            def run(a, nn, shots, inner=inner):
                seen.append(nn)
                return inner(a, nn, shots)

            self.attack(n, run)
        self.assertEqual(seen, [15, 21, 35])

    def test_the_stage_passes_the_static_guard_and_is_guarded(self):
        self.assertIn("stego_analyzer/quantum_stage.py", guard.discover_guarded())
        self.assertEqual(guard.scan_file("stego_analyzer/quantum_stage.py", "all"), [])

    def test_the_guard_catches_a_classical_shortcut_in_this_module(self):
        bad = quantum_stage_source() + "\n\ndef shortcut(n):\n    from sympy import factorint\n    return factorint(n)\n"
        self.assertTrue(guard.scan_source(bad, "all", "stego_analyzer/quantum_stage.py"))

    @slow
    def test_real_circuit_two_images_with_different_n_give_different_factors(self):
        results = {}
        for n in (15, 21):
            img, key = self.toy_image(n)
            r = sa.analyze(img, stages={"attack_toy": partial(quantum_stage.attack_toy, record_path=self.root / f"r{n}.json",
                                                              diagram_dir=self.root / "diag")}, public_key=key)
            self.assertEqual(r["problems"], [], r["pipeline_status"])
            self.assertEqual(r["attack"]["state"], "broken_toy", r["pipeline_status"])
            self.assertEqual(r["attack"]["recovered_message"], "HELLO")
            results[n] = r["attack"]["factors"]
        self.assertEqual(results, {15: [3, 5], 21: [3, 7]})


def quantum_stage_source():
    return (ROOT / "stego_analyzer" / "quantum_stage.py").read_text(encoding="utf-8")


class EndToEnd(Workspace):
    def fast_stages(self):
        quantum_stage._shor_run()
        helper = ShorStage("fake_shor")
        return {"attack_toy": partial(quantum_stage.attack_toy, record_path=self.root / "runs.json",
                                      diagram_dir=self.root / "diag", shor=helper.fake_shor((3, 5)))}

    def test_toy_rsa_image_goes_through_every_real_stage(self):
        img, key = self.toy_image(15)
        r = sa.analyze(img, self.fast_stages(), public_key=key)
        self.assertEqual((r["pipeline_status"], r["problems"]), ("complete", []))
        self.assertEqual(r["hiding"]["method"], "lsb")
        self.assertEqual(r["cipher"]["kind"], "textbook_rsa")
        self.assertEqual(r["attack"]["state"], "broken_toy")
        self.assertEqual(r["attack"]["recovered_message"], "HELLO")
        self.assertEqual(r["score"]["overall"], 95.5)
        self.assertEqual([x["stage"] for x in r["stage_log"]],
                         ["accept", "detect_method", "extract", "cipher_identify", "quantum_stage"])

    def test_same_image_without_the_public_key_is_not_attacked(self):
        img, _ = self.toy_image(15)
        r = sa.analyze(img, self.fast_stages())
        self.assertEqual(r["cipher"]["kind"], "unrecognised")
        self.assertEqual(r["attack"]["state"], "unrecognised")
        self.assertIsNone(r["score"])

    def test_clean_cover_is_unrecognised(self):
        r = sa.analyze(self.image("clean.png"), self.fast_stages())
        self.assertEqual(r["attack"]["state"], "unrecognised")
        self.assertEqual(r["problems"], [])

    def test_ml_kem_sized_payload_resists(self):
        img = self.image("pqc.png", "cd" * (1116 + 8))
        r = sa.analyze(img, self.fast_stages())
        self.assertEqual(r["attack"]["state"], "resists")
        self.assertEqual(r["score"]["overall"], 4.7)


class Exports(Workspace):
    def sample(self):
        img, key = self.toy_image(15)
        return sa.analyze(img, EndToEnd("fast_stages").fast_stages.__func__(self), public_key=key)

    def test_csv_has_a_header_the_result_and_no_blob_bytes(self):
        r = self.sample()
        out = report.export_csv(r, self.root / "r.csv")
        rows = list(csv.reader(open(out, encoding="utf-8")))
        self.assertEqual(rows[0], ["field", "value"])
        fields = dict(rows[1:])
        self.assertEqual(fields["attack.state"], "broken_toy")
        self.assertEqual(fields["attack.label"], "Aer simulator, toy size")
        self.assertEqual(fields["score.overall"], "95.5")

    def test_pdf_is_written_and_starts_like_a_pdf(self):
        out = report.export_pdf(self.sample(), self.root / "r.pdf")
        self.assertEqual(out.read_bytes()[:5], b"%PDF-")

    def test_pdf_text_says_it_is_not_a_probability(self):
        text = "\n".join(report._lines(self.sample()))
        self.assertIn("not a probability", text)
        self.assertIn("Aer simulator, toy size", text)


if __name__ == "__main__":
    unittest.main()
