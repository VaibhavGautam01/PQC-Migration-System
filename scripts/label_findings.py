"""Label scanner findings by hand. Saves after every answer; safe to quit and resume.

Usage: python scripts\label_findings.py
Reads data\hand_checked_template.csv, writes data\hand_checked.csv.
"""
import csv
from pathlib import Path

SRC = Path("data/hand_checked_template.csv")
DST = Path("data/hand_checked.csv")

with SRC.open(encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    rows = list(reader)

done = {}
if DST.exists():
    with DST.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r.get("correct"):
                done[(r["file"], r["line"], r["pattern_id"])] = r["correct"]


def save():
    with DST.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            r["correct"] = done.get((r["file"], r["line"], r["pattern_id"]), "")
            w.writerow(r)


todo = [r for r in rows if (r["file"], r["line"], r["pattern_id"]) not in done]
print(f"{len(rows)} findings, {len(done)} labelled, {len(todo)} to go")
for i, r in enumerate(todo, 1):
    print(f"\n[{i}/{len(todo)}] {r['file']}:{r['line']}  {r['pattern_id']}  ({r['primitive']})")
    print("   ", r["snippet"])
    while True:
        a = input("   real crypto usage? [y]es / [n]o / [q]uit and save: ").strip().lower()
        if a in ("y", "n", "q"):
            break
    if a == "q":
        break
    done[(r["file"], r["line"], r["pattern_id"])] = "yes" if a == "y" else "no"
    save()
save()
print(f"saved {DST}: {sum(1 for v in done.values() if v)} labelled")
