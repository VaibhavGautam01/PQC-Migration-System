import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import export_findings


class TestExport(unittest.TestCase):
    def test_csv_and_pdf_written(self):
        findings = [{"file": "a.py", "line": 3, "pattern": "RSA <b>"},
                    {"file": "b.py", "line": 9, "pattern": "AES & co", "extra": [1, 2]}]
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "findings.json"
            src.write_text(json.dumps({"findings": findings}), encoding="utf-8")
            export_findings.main(str(src), d)
            with open(Path(d) / "findings.csv", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["file"], "a.py")
            self.assertGreater((Path(d) / "findings.pdf").stat().st_size, 500)


if __name__ == "__main__":
    unittest.main()