"""
test_risk_report_generation.py - end-to-end check (Issue #8)

generate_risk_report.py ko asli CLI ki tarah chalata hai (subprocess),
taaki wahi path test ho jo team use karegi.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "generate_risk_report.py"
COMMITTED = ROOT / "docs" / "risk_report.md"


def run_script(out_path):
    """Script ko --out ke saath chalao, CompletedProcess wapas karo."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--out", str(out_path)],
        cwd=ROOT, capture_output=True, text=True,
    )


def read(path):
    """Text padho (newline normalise: Windows CRLF aur LF same maane jayein)."""
    return Path(path).read_text(encoding="utf-8")


class TestRiskReportGeneration(unittest.TestCase):
    """Auto-generated risk_report.md ke end-to-end checks."""

    def test_report_matches_committed_version(self):
        """Fresh report committed docs/risk_report.md se exactly match kare."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.md"
            result = run_script(out)
            self.assertEqual(result.returncode, 0, result.stderr)
            # Fail ka matlab: findings ya script badle, report regenerate karo.
            self.assertEqual(read(out), read(COMMITTED))

    def test_two_runs_are_identical(self):
        """Do alag runs ka output byte-for-byte same ho (timestamp nahi)."""
        with tempfile.TemporaryDirectory() as tmp:
            first = Path(tmp) / "a.md"
            second = Path(tmp) / "b.md"
            self.assertEqual(run_script(first).returncode, 0)
            self.assertEqual(run_script(second).returncode, 0)
            self.assertEqual(read(first), read(second))

    def test_qubit_column_is_2n_plus_3(self):
        """Section 2 ki har row mein qubits == 2n + 3 ho."""
        text = read(COMMITTED)
        section = text.split("## 2.")[1].split("## 3.")[0]
        checked = 0
        for line in section.splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            # Header aur separator rows skip: unka 2nd cell number nahi hota.
            if len(cells) > 3 and cells[1].isdigit():
                n, qubits = int(cells[1]), int(cells[3])
                self.assertEqual(qubits, 2 * n + 3, line)
                checked += 1
        # Khali pass na ho: kam se kam ek row check hui ho.
        self.assertGreater(checked, 0)

    def test_handwritten_file_is_not_overwritten(self):
        """Bina marker wali file par script REFUSE kare, content na badle."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "report.md"
            out.write_text("hand-written notes\n", encoding="utf-8")
            result = run_script(out)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(read(out), "hand-written notes\n")


if __name__ == "__main__":
    unittest.main()
