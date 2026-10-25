"""
analyzer_testset_run.py - run the Stego Analyzer on the whole generated test set and measure it.

  python scripts/make_analyzer_testset.py
  python scripts/analyzer_testset_run.py                      # live runs: records go to an untracked session file
  python scripts/analyzer_testset_run.py --save-evidence      # records go to data/quantum_runs.json (commit them)

Measured on images made by OUR projects only. The numbers say nothing about images from other tools.
Exit code 0 = every image gave the expected result, 1 = at least one differs or stopped early.
"""
import argparse
import json
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import risk_score as rs  # noqa: E402
from stego_analyzer import pipeline as sa, quantum_stage  # noqa: E402


def check_case(label, report):
    """Compare one report with its label. Returns a dict of booleans (None where not applicable)."""
    complete = report["pipeline_status"] == "complete"
    got_state = (report.get("attack") or {}).get("state")
    exp_msg = label.get("message")
    score = report.get("score")
    consistent = None
    if score:
        again = rs.score_layer(**score["layer_inputs"])
        consistent = round(again["overall"], 1) == score["overall"]
    return {"complete": complete,
            "hiding_ok": complete and (report.get("hiding") or {}).get("method") == label["expected_hiding"],
            "cipher_ok": (None if label["expected_cipher"] is None
                          else complete and (report.get("cipher") or {}).get("kind") == label["expected_cipher"]),
            "state_ok": complete and got_state == label["expected_state"],
            "message_ok": (None if label["expected_state"] != "broken_toy"
                           else (report.get("attack") or {}).get("recovered_message") == exp_msg),
            "score_matches_engine": consistent,
            "no_report_problems": not report.get("problems")}


def evaluate(cases, analyze_fn):
    """cases: [(label, image_path)]. analyze_fn(path, public_key) -> report. Returns (rows, summary)."""
    rows = []
    for label, path in cases:
        report = analyze_fn(path, label.get("public_key"))
        rows.append({"file": label["file"], "status": report["pipeline_status"],
                     "got_state": (report.get("attack") or {}).get("state"),
                     "expected_state": label["expected_state"], **check_case(label, report)})

    def rate(key):
        vals = [r[key] for r in rows if r[key] is not None]
        return None if not vals else sum(bool(v) for v in vals) / len(vals)

    summary = {"images": len(rows), "completed": sum(r["complete"] for r in rows),
               "hiding_accuracy": rate("hiding_ok"), "cipher_accuracy": rate("cipher_ok"),
               "state_accuracy": rate("state_ok"), "message_recovered": rate("message_ok"),
               "score_matches_engine": rate("score_matches_engine"),
               "all_as_expected": all(r["state_ok"] and r["hiding_ok"] and r["no_report_problems"] and r["cipher_ok"] is not False
                                      for r in rows)}
    return rows, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(ROOT / "outputs" / "tmp_analyzer_testset"))
    ap.add_argument("--save-evidence", action="store_true",
                    help="write the Shor run records to data/quantum_runs.json and docs/circuits")
    ap.add_argument("--json", default=str(ROOT / "outputs" / "tmp_analyzer_testset_results.json"))
    args = ap.parse_args(argv)
    folder = Path(args.dir)
    labels_file = folder / "labels.json"
    if not labels_file.is_file():
        print(f"No test set at {folder}. Run: python scripts/make_analyzer_testset.py")
        return 2
    labels = json.loads(labels_file.read_text(encoding="utf-8"))
    stages = {}
    if args.save_evidence:
        stages["attack_toy"] = partial(quantum_stage.attack_toy, record_path=ROOT / "data" / "quantum_runs.json",
                                       diagram_dir=ROOT / "docs" / "circuits")
    rows, summary = evaluate([(l, folder / l["file"]) for l in labels],
                             lambda p, key: sa.analyze(p, stages or None, public_key=key))
    for r in rows:
        mark = "ok  " if r["state_ok"] and r["hiding_ok"] else "DIFF"
        print(f"{mark} {r['file']:<24} expected {r['expected_state']:<14} got {str(r['got_state']):<14} {r['status']}")
    pct = lambda v: "n/a" if v is None else f"{v:.0%}"          # noqa: E731
    print(f"\nImages {summary['images']}, completed {summary['completed']}. Measured on our own images only.")
    print(f"Hiding method {pct(summary['hiding_accuracy'])}, cipher {pct(summary['cipher_accuracy'])}, "
          f"final state {pct(summary['state_accuracy'])}, message recovered {pct(summary['message_recovered'])}, "
          f"score equals the engine {pct(summary['score_matches_engine'])}")
    Path(args.json).parent.mkdir(exist_ok=True)
    Path(args.json).write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    return 0 if summary["all_as_expected"] else 1


if __name__ == "__main__":
    sys.exit(main())
