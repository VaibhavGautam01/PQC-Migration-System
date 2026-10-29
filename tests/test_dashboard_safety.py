import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import dashboard_safety as ds  # type: ignore # noqa: E402

HAS_GIT = shutil.which("git") is not None


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


class TestSessionPath(unittest.TestCase):
    def test_session_file_is_not_the_tracked_demo_file(self):
        p = ds.session_path("/repo")
        self.assertNotEqual(p.name, "demo_results.json")
        self.assertEqual(p.parent.name, "outputs")

    def test_session_file_matches_the_gitignore_rule(self):
        ignore = (Path(__file__).resolve().parent.parent / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("outputs/tmp_*", ignore)
        self.assertTrue(ds.SESSION_DEMO.name.startswith("tmp_"))


class TestDashboardSource(unittest.TestCase):
    """A static check: no dashboard code opens a tracked data file for writing."""

    @classmethod
    def setUpClass(cls):
        cls.src = (Path(__file__).resolve().parent.parent / "src" / "live_dashboard.py").read_text(encoding="utf-8")

    def test_demo_save_never_opens_the_tracked_file_for_writing(self):
        self.assertNotIn('open(DEMO, "w"', self.src)
        self.assertIn('open(DEMO_SESSION, "w"', self.src)

    def test_overwriting_buttons_wait_for_the_checkbox(self):
        self.assertIn("allow_overwrite", self.src)
        # Scan targets, Rebuild CBOM and Full pipeline are the three buttons that overwrite tracked files
        self.assertEqual(self.src.count("not allow)"), 3)
        self.assertEqual(self.src.count("bool(missing) or not allow"), 2)


class TestRestoreHint(unittest.TestCase):
    def test_hint_names_every_file(self):
        self.assertEqual(ds.restore_hint(["a.json", "docs/b.md"]), "git checkout -- a.json docs/b.md")

    def test_no_files_no_hint(self):
        self.assertEqual(ds.restore_hint([]), "")


@unittest.skipUnless(HAS_GIT, "git is not installed")
class TestGitChanges(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        git(self.root, "init", "-q")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "t")
        (self.root / "tracked.json").write_text("{}", encoding="utf-8")
        git(self.root, "add", "tracked.json")
        git(self.root, "commit", "-q", "-m", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_repository_has_no_changes(self):
        self.assertEqual(ds.git_changes(self.root), [])

    def test_modified_tracked_file_is_reported(self):
        (self.root / "tracked.json").write_text('{"a": 1}', encoding="utf-8")
        self.assertEqual(ds.git_changes(self.root), ["tracked.json"])

    def test_untracked_file_is_not_reported(self):
        (self.root / "outputs").mkdir()
        (self.root / "outputs" / "tmp_demo_results.json").write_text("{}", encoding="utf-8")
        self.assertEqual(ds.git_changes(self.root), [])

    def test_not_a_repository_gives_empty_list(self):
        with tempfile.TemporaryDirectory() as plain:
            self.assertEqual(ds.git_changes(plain), [])


if __name__ == "__main__":
    unittest.main()
