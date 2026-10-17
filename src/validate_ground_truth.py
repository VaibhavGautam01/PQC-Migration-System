"""validate_ground_truth.py - precision and recall of the scanner on the two target repos.

Compares outputs/findings.json with the hand-labelled lines in
data/ground_truth.json.

  precision          = findings that sit on a labelled crypto line / all findings
  recall (findings)  = labelled lines that have a finding / labelled lines
  recall (+ flags)   = labelled lines that have a finding OR an INSECURE_RNG flag

Usage: python src/validate_ground_truth.py [findings.json] [ground_truth.json]
The numbers are in-sample: the patterns were written against these same repos.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def evaluate(report, truth):
    """Return a dict with the counts and the missed / extra lines."""
    findings = report["findings"] if isinstance(report, dict) else report
    flagged = {(f["project"], f["file"], f["line"]) for f in findings}
    rng = set()
    if isinstance(report, dict):
        for project, flags in report.get("edge_cases", {}).items():
            for fl in flags.get("insecure_rng", []):
                rng.add((project, fl["file"], fl["line"]))
    core = {(t["project"], t["file"], t["line"]): t["what"] for t in truth["core"]}
    border = {(t["project"], t["file"], t["line"]) for t in truth.get("borderline", [])}

    hit = {k for k in core if k in flagged}
    hit_flags = {k for k in core if k in flagged or k in rng}
    extra = sorted(k for k in flagged if k not in core and k not in border)
    borderline_hit = sorted(k for k in flagged if k in border)
    return {
        "findings": len(flagged), "labelled": len(core),
        "true_positives": len(flagged & set(core)),
        "precision": len(flagged & set(core)) / len(flagged) if flagged else 1.0,
        "recall_findings": len(hit) / len(core),
        "recall_with_flags": len(hit_flags) / len(core),
        "missed": sorted((k, core[k]) for k in core if k not in hit),
        "missed_after_flags": sorted((k, core[k]) for k in core if k not in hit_flags),
        "extra": extra, "borderline_hit": borderline_hit,
    }


def main(argv):
    report = _load(argv[1] if len(argv) > 1 else ROOT / "outputs" / "findings.json")
    truth = _load(argv[2] if len(argv) > 2 else ROOT / "data" / "ground_truth.json")
    r = evaluate(report, truth)
    print(f"Findings: {r['findings']}   Labelled crypto lines: {r['labelled']}")
    print(f"Precision:                 {r['true_positives']}/{r['findings']} = {r['precision']:.1%}")
    print(f"Recall (findings only):    {r['recall_findings']:.1%}")
    print(f"Recall (findings + flags): {r['recall_with_flags']:.1%}")
    for (key, what) in r["missed"]:
        covered = "covered by an INSECURE_RNG flag" if (key, what) not in r["missed_after_flags"] else "NOT covered"
        print(f"  missed by findings: {key[1]}:{key[2]} ({what}) -> {covered}")
    for key in r["extra"]:
        print(f"  extra finding (not labelled): {key[1]}:{key[2]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
