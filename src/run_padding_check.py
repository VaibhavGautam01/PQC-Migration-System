import json
import sys
from pathlib import Path
from edge_cases import check_padding

findings_file = sys.argv[1]
data = json.load(open(findings_file))
root = Path(data["scan_root"])

for f in data["findings"]:
    if f["pattern_id"] == "RSA-MODEXP":
        flag = check_padding(root / f["file"], f["line"])
        print(f["file"], f["line"], "->", flag["flag"] if flag else "padding found")