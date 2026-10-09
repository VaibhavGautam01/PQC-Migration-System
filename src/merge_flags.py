"""
merge_flags.py - Add edge-case flags (padding, indirect usage) to a
findings.json so later stages read one file.

Usage (from src/):
  python merge_flags.py ../outputs/findings_image.json --out ../outputs/findings_image_merged.json
"""
import argparse
import json
from pathlib import Path

from edge_cases import check_padding, find_indirect_usage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("findings")
    ap.add_argument("--out", help="output file (default: overwrite input)")
    args = ap.parse_args()

    data = json.load(open(args.findings))
    root = Path(data["scan_root"])

    padding = []
    for f in data["findings"]:
        if f["pattern_id"] == "RSA-MODEXP":
            flag = check_padding(root / f["file"], f["line"])
            if flag:
                f["edge_flag"] = flag["flag"]
                padding.append(flag)

    providers = {f["file"] for f in data["findings"]}
    indirect = find_indirect_usage(root, provider_files=providers)

    data["edge_cases"] = {"padding": padding, "indirect_usage": indirect}
    out = args.out or args.findings
    json.dump(data, open(out, "w"), indent=2)
    print(f"Merged {len(padding)} padding flags and "
          f"{len(indirect)} indirect-usage flags -> {out}")


if __name__ == "__main__":
    main()