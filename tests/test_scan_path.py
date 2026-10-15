import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import scanner  # noqa: E402


def test_scan_matches_scan_path_on_real_targets():
    targets = ROOT / "data" / "targets"
    dirs = sorted(p for p in targets.iterdir() if p.is_dir())
    assert dirs
    for d in dirs:
        assert scanner.scan(str(d)).findings == scanner.scan_path(str(d))


def test_skips_ignored_dirs(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.py").write_text("import rsa\n")
    (tmp_path / "a.py").write_text("x = 1\n")
    res = scanner.scan(str(tmp_path))
    assert res.files_scanned == 1


def test_skips_minified_and_oversized(tmp_path):
    (tmp_path / "lib.min.js").write_text("var a=1;")
    (tmp_path / "big.py").write_text("x = 1\n" * 50)
    res = scanner.scan(str(tmp_path), scanner.ScanOptions(max_file_bytes=10))
    assert res.files_scanned == 0
    assert res.files_skipped == 2


def test_missing_path_reports_error(tmp_path):
    res = scanner.scan(str(tmp_path / "nope"))
    assert res.errors and res.findings == []
