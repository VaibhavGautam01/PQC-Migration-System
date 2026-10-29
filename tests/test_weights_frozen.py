"""Fails if the risk weights change without a version bump and a new lock."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import weights_lock as wl  # type: ignore # noqa: E402


class TestWeightsFrozen(unittest.TestCase):
    def test_weights_match_the_lock(self):
        ok, msg = wl.check_lock()
        self.assertTrue(ok, msg)

    def test_lock_records_version_v1_0(self):
        rec = json.loads(wl.LOCK.read_text(encoding="utf-8"))
        self.assertEqual(rec["version"], "v1.0")
        self.assertEqual(len(rec["sha256"]), 64)

    def test_fingerprint_ignores_spacing(self):
        data = json.loads(wl.WEIGHTS.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "w.json"
            p.write_text(json.dumps(data, indent=8), encoding="utf-8")
            self.assertEqual(wl.fingerprint(p), wl.fingerprint())

    def test_any_weight_change_is_detected(self):
        data = json.loads(wl.WEIGHTS.read_text(encoding="utf-8"))
        data["quantum_weights"]["f1"] += 0.01
        with tempfile.TemporaryDirectory() as d:
            w, lock = Path(d) / "w.json", Path(d) / "lock.json"
            w.write_text(json.dumps(wl.json.loads(wl.WEIGHTS.read_text())), encoding="utf-8")
            wl.write_lock(w, lock)
            self.assertTrue(wl.check_lock(w, lock)[0])
            w.write_text(json.dumps(data), encoding="utf-8")
            self.assertFalse(wl.check_lock(w, lock)[0])


if __name__ == "__main__":
    unittest.main()