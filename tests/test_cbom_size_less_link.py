"""Size-less CBOM entries point at the sized entries they serve."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import cbom  # noqa: E402

VIDEO = "Secure-Video-Steganography"


def video_findings():
    raw = json.loads((ROOT / "outputs" / "findings.json").read_text(encoding="utf-8"))
    items = raw["findings"] if isinstance(raw, dict) else raw
    return [f for f in items if f["project"] == VIDEO and f["primitive"] == "RSA"]


def build(findings):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "findings.json"
        path.write_text(json.dumps(findings), encoding="utf-8")
        return cbom.build_cbom_from_files(str(path))[0]


class TestSizeLessLink(unittest.TestCase):
    def test_unknown_entry_points_at_the_sized_entry(self):
        data = build(video_findings())
        unknown = [e for e in data["entries"] if e["key_size_bits"] is None]
        sized = [e for e in data["entries"] if e["key_size_bits"] is not None]
        self.assertEqual(len(unknown), 1)
        self.assertTrue(sized)
        text = " ".join(unknown[0]["notes"])
        self.assertIn("usage of those keys", text)
        for entry in sized:
            self.assertIn(entry["id"], text)
        self.assertIsNone(unknown[0]["quantum_risk"]["logical_qubits_estimate"])

    def test_no_link_note_when_there_is_no_sized_entry(self):
        only_unsized = [f for f in video_findings() if f.get("key_size") is None]
        data = build(only_unsized)
        self.assertEqual(len(data["entries"]), 1)
        self.assertNotIn("usage of those keys", " ".join(data["entries"][0]["notes"]))

    def test_sized_entries_get_no_link_note(self):
        data = build(video_findings())
        for entry in data["entries"]:
            if entry["key_size_bits"] is not None:
                self.assertNotIn("usage of those keys", " ".join(entry["notes"]))


if __name__ == "__main__":
    unittest.main()
