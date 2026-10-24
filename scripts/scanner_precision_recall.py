"""Precision/recall of the scanner on hand-checked findings.

hand_checked.csv columns: file,line,verdict   (verdict = tp | fp | fn)
precision = tp / (tp + fp)    recall = tp / (tp + fn)
"""
import csv
import json
import sys


def load_findings(path):
    data = json.load(open(path, encoding="utf-8"))
    return data["findings"] if isinstance(data, dict) and "findings" in data else data


def key_of(f):
    # ADAPT these field names if findings.json uses different ones
    return (str(f.get("file") or f.get("path")), str(f.get("line") or f.get("lineno")))


def main(findings_path, labels_path):
    reported = {key_of(f) for f in load_findings(findings_path)}
    tp = fp = fn = 0
    unmatched = []
    with open(labels_path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            k = (row["file"], str(row["line"]))
            v = row["verdict"].strip().lower()
            if v == "fn":
                fn += 1
            elif k not in reported:
                unmatched.append(k)
            elif v == "tp":
                tp += 1
            elif v == "fp":
                fp += 1
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    print(f"tp={tp} fp={fp} fn={fn}")
    print(f"precision={prec:.3f} recall={rec:.3f}")
    print(f"findings reported: {len(reported)}; hand-checked rows not matched to a finding: {len(unmatched)}")
    for k in unmatched:
        print("  unmatched label:", k)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python scripts/scanner_precision_recall.py findings.json data/hand_checked.csv")
    main(sys.argv[1], sys.argv[2])