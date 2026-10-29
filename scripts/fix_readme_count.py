"""Apply the README test-count fix that repo_check --release asks for.

Refuses to run unless both numbers are digits. Run it once, last, after the test count stops changing.
"""
import re
import subprocess
import sys

out = subprocess.run([sys.executable, "scripts/repo_check.py", "--release"],
                     capture_output=True, text=True).stdout
m = re.search(r"badge says (\d+) tests, run_tests\.py runs (\d+)", out)
if not m:
    print("repo_check reports no README test-count mismatch; nothing to do")
    raise SystemExit(0)
old, new = m.groups()
with open("README.md", encoding="utf-8", newline="") as f:
    t = f.read()
print(f"replacing {t.count(old)} occurrence(s) of {old} with {new}")
if t.count(old) > 4:
    print("refusing: too many occurrences; edit README.md by hand")
    raise SystemExit(1)
with open("README.md", "w", encoding="utf-8", newline="") as f:
    f.write(t.replace(old, new))
