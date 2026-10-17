"""
layers.py - assign every scanner finding to a layer (Week 1 Day 2 spec, started Day 1).

Layers (Team Task Plan, Section 4):
  L1 message encryption   L2 frame-selection key   L3 integrity   L5 signature
The hiding layer (LSB / XOR-LSB) is measured by steganalysis, not scored here.

Rules are plain data (RULES), so a change is one edit, not a code change.
L3 (CRC32) has no scanner finding: it is declared in LAYER_DEFS as a manual layer.
"""
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# findings.json project name -> short key used by --project
PROJECT_KEYS = {
    "Final-Year-project-part1": "image",
    "Secure-Video-Steganography": "video",
}

# Layers that exist per project. source = "scanner" or "manual" (from manual_facts.json).
LAYER_DEFS = {
    "image": {
        "L1": {"name": "Message encryption", "today": "textbook RSA, no padding", "source": "scanner"},
        "L2": {"name": "Frame-selection key", "today": "none (keyless embedding)", "source": "manual"},
        "L3": {"name": "Integrity", "today": "none", "source": "manual"},
        "L5": {"name": "Signature", "today": "none", "source": "manual"},
    },
    "video": {
        "L1": {"name": "Message encryption", "today": "textbook RSA, no padding", "source": "scanner"},
        "L2": {"name": "Frame-selection key", "today": "SHA-256 of passphrase", "source": "scanner"},
        "L3": {"name": "Integrity", "today": "CRC32 (key-check oracle)", "source": "manual"},
        "L5": {"name": "Signature", "today": "none", "source": "manual"},
    },
}

# First matching rule wins. A field that is absent matches anything.
RULES = [
    {"project": "video", "primitive": "SHA", "file_contains": "frame_selector", "layer": "L2"},
    {"primitive": "RSA", "layer": "L1"},
]


def project_key(finding):
    return PROJECT_KEYS.get(finding.get("project"))


def assign_layer(finding):
    """Return 'L1'/'L2'/... for a finding, or None if no rule matches."""
    key = project_key(finding)
    if key is None:
        return None
    for rule in RULES:
        if "project" in rule and rule["project"] != key:
            continue
        if "primitive" in rule and rule["primitive"] != finding.get("primitive"):
            continue
        if "file_contains" in rule and rule["file_contains"] not in finding.get("file", ""):
            continue
        return rule["layer"]
    return None


def load_findings(path=None):
    path = Path(path) if path else ROOT / "outputs" / "findings.json"
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)["findings"]


def build_layer_map(findings):
    """{'image': {'L1': [findings...]}, 'video': {...}, 'unmapped': [...]}"""
    out = {"image": defaultdict(list), "video": defaultdict(list), "unmapped": []}
    for f in findings:
        layer, key = assign_layer(f), project_key(f)
        if layer is None or key is None:
            out["unmapped"].append(f)
        else:
            out[key][layer].append(f)
    return out


if __name__ == "__main__":
    m = build_layer_map(load_findings())
    for proj in ("image", "video"):
        print(proj, {l: len(v) for l, v in sorted(m[proj].items())})
    print("unmapped:", len(m["unmapped"]))
