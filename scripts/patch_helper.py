r"""Make a reviewable patch against a pinned submodule without touching it.

  python scripts\patch_helper.py prepare image   copy the pinned code to a scratch git repo
  (edit the files in the scratch folder it prints)
  python scripts\patch_helper.py make image      write patches\image_pqc.diff and check that it applies
Use 'video' instead of 'image' for the video project. Run from the repository root.
"""
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

KEYS = {"image": ("final-year", "image_pqc.diff"), "video": ("steganography", "video_pqc.diff")}


def rm(path):
    def fix(func, p, *_):
        os.chmod(p, stat.S_IWRITE)
        func(p)
    if path.exists():
        try:
            shutil.rmtree(path, onexc=fix)
        except TypeError:
            shutil.rmtree(path, onerror=fix)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


if len(sys.argv) != 3 or sys.argv[1] not in ("prepare", "make") or sys.argv[2] not in KEYS:
    raise SystemExit(__doc__)
action, which = sys.argv[1], sys.argv[2]
key, name = KEYS[which]
paths = [p.strip() for p in re.findall(r"path\s*=\s*(.+)", Path(".gitmodules").read_text(encoding="utf-8"))]
hits = [p for p in paths if key in p.lower()]
if len(hits) != 1:
    raise SystemExit(f"cannot pick one submodule from {paths}")
src = Path(hits[0])
work = Path(tempfile.gettempdir()) / f"patch_work_{which}"
ignore = shutil.ignore_patterns(".git")

if action == "prepare":
    rm(work)
    shutil.copytree(src, work, ignore=ignore)
    git("init", "-q", cwd=work)
    git("config", "core.autocrlf", "false", cwd=work)
    git("config", "core.safecrlf", "false", cwd=work)
    git("add", "-A", cwd=work)
    git("-c", "user.name=x", "-c", "user.email=x@x", "commit", "-q", "-m", "base", cwd=work)
    print("scratch copy of", src, "is ready at:", work)
    print("edit the files there, then run: python scripts\\patch_helper.py make", which)
else:
    if not work.exists():
        raise SystemExit("run 'prepare' first")
    git("add", "-A", cwd=work)
    Path("patches").mkdir(exist_ok=True)
    out = Path("patches").resolve() / name
    git("diff", "--cached", f"--output={out}", cwd=work)
    if out.stat().st_size == 0:
        out.unlink()
        raise SystemExit("empty diff: nothing was changed in the scratch copy")
    print(git("diff", "--cached", "--stat", cwd=work).stdout)
    chk = Path(tempfile.gettempdir()) / f"patch_check_{which}"
    rm(chk)
    shutil.copytree(src, chk, ignore=ignore)
    r = subprocess.run(["git", "apply", "--check", "-v", str(out)], cwd=chk, capture_output=True, text=True)
    print(r.stdout, r.stderr)
    print("wrote", out, "-", "APPLIES CLEANLY" if r.returncode == 0 else "DOES NOT APPLY")
    raise SystemExit(r.returncode)
