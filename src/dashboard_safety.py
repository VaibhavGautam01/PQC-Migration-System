"""
dashboard_safety.py - helpers that keep dashboard buttons from silently changing tracked files.

Pure functions (no Streamlit), so they can be tested.

  * git_changes(root): tracked files that differ from the last commit.
  * restore_hint(files): the exact command that undoes them.
  * session_path(root): where the live demo saves a run. It is NOT tracked (outputs/tmp_* is ignored),
    so a demo click can never change data/demo_results.json. To keep a run, copy it over the tracked
    file yourself and commit it.
"""
import subprocess
from pathlib import Path

SESSION_DEMO = Path("outputs") / "tmp_demo_results.json"


def session_path(root) -> Path:
    return Path(root) / SESSION_DEMO


def git_changes(root, timeout=20):
    """Modified tracked files (empty list when git is missing or this is not a repository)."""
    try:
        p = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=str(root),
                           capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if p.returncode != 0:
        return []
    return [line[3:].strip().strip('"') for line in p.stdout.splitlines() if line.strip()]


def restore_hint(files):
    """The command that puts the given tracked files back to the last commit."""
    if not files:
        return ""
    return "git checkout -- " + " ".join(files)
