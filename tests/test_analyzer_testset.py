import json
import sys
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import analyzer_testset_run as run  # type: ignore # noqa: E402
import make_analyzer_testset as mk  # type: ignore # noqa: E402
from stego_analyzer import extract, pipeline as sa, quantum_stage  # noqa: E402
from tests.test_analyzer_stages import ShorStage  # noqa: E402

FAKE_PINNED = '''
def embed_lsb(cover, text, stego):
    open(stego, "wb").write(b"HEX:" + text.encode())

def extract_lsb(path):
    d = open(path, "rb").read()
    if not d.startswith(b"HEX:"):
        raise ValueError("no payload")
    return d[4:].decode()
'''


class TestsetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.pinned = self.root / "pinned"
        self.pinned.mkdir()
        (self.pinned / "lsb_stego.py").write_text(FAKE_PINNED, encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(extract, "PINNED_DIR", self.pinned)
        p.start()
        self.addCleanup(p.stop)
        quantum_stage._shor_run()

    def test_generator_writes_every_case_and_labels(self):
        out = self.root / "set"
        labels = mk.generate(self.pinned, out)
        self.assertEqual([l["file"] for l in labels], ["toy_rsa_N15.png", "toy_rsa_N21.png", "toy_rsa_N35.png",
                                                       "toy_rsa_N15_no_key.png", "ml_kem_aes_gcm.png", "clean_image.png"])
        self.assertEqual(sorted(p.name for p in out.glob("*.png")), sorted(l["file"] for l in labels))
        self.assertEqual(json.loads((out / "labels.json").read_text(encoding="utf-8")), labels)
        self.assertFalse(list(out.glob("*_cover.png")))             # the covers are removed

    def test_generator_refuses_a_missing_pinned_project(self):
        with self.assertRaises(SystemExit):
            mk.generate(self.root / "nowhere", self.root / "set")

    def test_toy_keys_are_valid_rsa_keys(self):
        from math import gcd
        for n, (p, q) in mk.TOY_PRIMES.items():
            self.assertEqual(p * q, n)
            self.assertEqual(gcd(mk.toy_public_key(n)["e"], (p - 1) * (q - 1)), 1)

    def test_whole_set_with_a_fast_shor_gives_the_expected_results(self):
        out = self.root / "set"
        labels = mk.generate(self.pinned, out)
        helper = ShorStage("fake_shor")
        factors = {15: (3, 5), 21: (3, 7), 35: (5, 7)}

        def analyze(path, key):
            stages = {}
            if key:
                stages["attack_toy"] = partial(quantum_stage.attack_toy, record_path=self.root / "runs.json",
                                               diagram_dir=self.root / "diag", shor=helper.fake_shor(factors[key["n"]]))
            return sa.analyze(path, stages, public_key=key)

        rows, summary = run.evaluate([(l, out / l["file"]) for l in labels], analyze)
        self.assertEqual([r["got_state"] for r in rows],
                         ["broken_toy", "broken_toy", "broken_toy", "unrecognised", "resists", "unrecognised"])
        self.assertTrue(summary["all_as_expected"], rows)
        self.assertEqual(summary["completed"], 6)
        self.assertEqual(summary["message_recovered"], 1.0)
        self.assertEqual(summary["score_matches_engine"], 1.0)
        self.assertEqual(summary["hiding_accuracy"], 1.0)

    def test_a_wrong_result_is_counted_as_wrong(self):
        label = {"file": "x.png", "expected_hiding": "lsb", "expected_cipher": "textbook_rsa",
                 "expected_state": "broken_toy", "public_key": None, "message": "HELLO"}
        wrong = {"pipeline_status": "complete", "hiding": {"method": "clean_or_unknown"}, "cipher": {"kind": "unrecognised"},
                 "attack": {"state": "unrecognised"}, "score": None, "problems": []}
        rows, summary = run.evaluate([(label, Path("x.png"))], lambda p, k: wrong)
        self.assertFalse(summary["all_as_expected"])
        self.assertEqual(summary["state_accuracy"], 0.0)
        self.assertFalse(rows[0]["message_ok"])

    def test_an_unfinished_run_is_not_counted_as_correct(self):
        label = {"file": "x.png", "expected_hiding": "lsb", "expected_cipher": None,
                 "expected_state": "resists", "public_key": None, "message": None}
        stopped = {"pipeline_status": "stopped at extract: not implemented yet", "hiding": None, "cipher": None,
                   "attack": None, "score": None, "problems": []}
        _, summary = run.evaluate([(label, Path("x.png"))], lambda p, k: stopped)
        self.assertEqual(summary["completed"], 0)
        self.assertFalse(summary["all_as_expected"])

    def test_runner_without_a_test_set_says_what_to_do(self):
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run.main(["--dir", str(self.root / "none")])
        self.assertEqual(code, 2)
        self.assertIn("make_analyzer_testset.py", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
