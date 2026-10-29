"""Every percentage in a report must appear in outputs/risk_scores.json (rounded to 1 decimal).

Usage: python scripts\numbers_check.py docs\some_report.md
Non-score percentages (QBER 11%, 0.1% gate error) get flagged; review those by hand.
"""
import json
import re
import sys
from pathlib import Path


def flatten(x, out):
    if isinstance(x, dict):
        for v in x.values():
            flatten(v, out)
    elif isinstance(x, list):
        for v in x:
            flatten(v, out)
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        out.add(round(float(x), 1))


known = set()
flatten(json.loads(Path("outputs/risk_scores.json").read_text(encoding="utf-8-sig")), known)
bad = 0
for path in sys.argv[1:]:
    text = Path(path).read_text(encoding="utf-8-sig")
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text):
        if round(float(m.group(1)), 1) not in known:
            line = text.count("\n", 0, m.start()) + 1
            print(f"{path}:{line}: {m.group(0)} not found in risk_scores.json")
            bad += 1
print(f"{bad} unmatched percentage(s)")
raise SystemExit(1 if bad else 0)
