r"""Check that a patch applies cleanly to a throwaway copy of a pinned submodule.

Usage: python scripts\check_patch.py patches\image_pqc.diff image
The keyword picks the submodule from .gitmodules. The submodule itself is never touched.
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

patch = Path(sys.argv[1]).resolve()
key = sys.argv[2].lower()
paths = [p.strip() for p in re.findall(r"path\s*=\s*(.+)", Path(".gitmodules").read_text(encoding="utf-8"))]
cands = [p for p in paths if key in p.lower()]
if len(cands) != 1:
    print("could not pick one submodule; paths in .gitmodules:", paths)
    raise SystemExit(1)
src = Path(cands[0])
head = subprocess.run(["git", "-C", str(src), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
print("submodule:", src, "pinned at", head)
with tempfile.TemporaryDirectory() as d:
    dst = Path(d) / "copy"
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git"))
    r = subprocess.run(["git", "apply", "--check", "-v", str(patch)], cwd=dst, capture_output=True, text=True)
    print(r.stdout, r.stderr)
    print("APPLIES CLEANLY" if r.returncode == 0 else "DOES NOT APPLY")
raise SystemExit(r.returncode)
