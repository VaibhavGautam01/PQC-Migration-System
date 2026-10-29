import json
import re
from datetime import date
from pathlib import Path

TODAY = date.today().isoformat()


def fmt(v):
    return "n/a" if v is None else f"{v:.1f}"


def risk_table():
    d = json.loads(Path("outputs/risk_scores.json").read_text(encoding="utf-8-sig"))
    out = ["| Project | Layer | Quantum % | Classical % | Overall % | Band | Overall range, Z = 5 to 20 |",
           "|---|---|---|---|---|---|---|"]
    notes = []
    for pname, proj in d["projects"].items():
        for key, layer in proj.items():
            if re.fullmatch(r"L\d+", key) and isinstance(layer, dict) and "score" in layer:
                s = layer["score"]
                zs = [v["overall"] for v in layer.get("z_scenarios", {}).values()]
                zr = f"{min(zs):.1f} to {max(zs):.1f}" if zs else "n/a"
                out.append(f"| {pname} | {key} | {fmt(s.get('quantum'))} | {fmt(s.get('classical'))} | "
                           f"{fmt(s.get('overall'))} | {s.get('band')} | {zr} |")
                for v in layer.get("variants", []):
                    out.append(f"| {pname} | {key}, {v.get('label')} | {fmt(v.get('quantum'))} | "
                               f"{fmt(v.get('classical'))} | {fmt(v.get('overall'))} | {v.get('band')} | n/a |")
        z = proj.get("z_range") or {}
        zt = f"{z['min']:.1f} to {z['max']:.1f}" if "min" in z and "max" in z else "n/a"
        out.append(f"| **{pname} project** | weakest-link rule | | | {fmt(proj.get('project_score'))} | {proj.get('band')} | {zt} |")
        if proj.get("no_protection"):
            notes.append(f"{pname}: no protection, so not scored: {', '.join(proj['no_protection'])}.")
    text = "\n".join(out)
    if notes:
        text += "\n\n" + " ".join(notes)
    text += "\nThe score is a transparent weighted score, not a probability. Scores come from outputs/risk_scores.json."
    return text


FACTORS = """- F1 quantum exposure: 100 for Shor-broken public-key algorithms (RSA, ECC, DSA, DH); 5 for NIST post-quantum algorithms with AES-256; for symmetric and hash layers 10, 30 or 60 by the effective bits left after Grover (128 or more, 112 to 127, below 112).
- F2 qubit cost: q = 2n + 3 logical qubits, score = 100 x (1 - (log10(q) - 2) / 3), limited to 20 to 100; it applies only to Shor-broken layers.
- F3 classical key weakness: modulus up to 512 bits = 100, 513 to 1,023 = 80, 1,024 to 2,047 = 50, 2,048 and above = 10; it does not apply to ML-KEM.
- F4 construction weakness: no padding and deterministic = 100, deterministic framing or a key-check oracle = 80, padding without AEAD = 40, AES-GCM or OAEP about 5 (the plan allows 0 to 10).
- F5 data lifetime (harvest now, decrypt later): Mosca test 100 x (X + Y) / Z, limited to 100, then gated: F5_eff = F5 x F1 / 100.
- F6 exposure: keyless = 100, keyed but bypassable (the video header scan) = 90, keyed and not bypassable = 30, then gated: F6_eff = F6 x max(F3, F4) / 100 (F4 alone when F3 does not apply)."""

SCOPE = ("Sir agreed to limit the new risk system to our two projects (Plan v3, Section 1). "
         "The assumptions for F5 were agreed with him on 2026-10-17, and the six-week schedule and the analyzer flow on 2026-10-22. "
         "His confirmation of the analyzer scope line is still open (see the scope paragraph).")

PARAMS = ("Choose ML-KEM-512 only when payload capacity is the binding limit: its KEM ciphertext is 768 B instead of 1,088 B, "
          "320 B less. Choose ML-KEM-1024 for data that must stay secret longest: its ciphertext is 1,568 B, 480 B more. "
          "For signatures, ML-DSA-44 saves 889 B per payload (2,420 B against 3,309 B) and ML-DSA-87 adds 1,318 B (4,627 B). "
          "Sizes are from the FIPS parameter tables and are checked by tests/test_sizes_match_libraries.py")

RESIDUAL = ("The remaining score comes from factors that do not reach zero even for ML-KEM-768 + AES-256-GCM: F1 is 5 for NIST post-quantum "
            "algorithms, F4 is about 5 for AEAD, and the gated F5 and F6 follow them. In the worked reference case this gives about 4.7 % overall "
            "(confirm against the 'after' value in our before/after output). The hiding layer is outside the percentage and stays detectable: "
            "the larger payload, and in the video project the header scan")

FIXES = [
    ("docs/attack_evidence_week2.md",
     r"numbers marked \*\*\[FILL\]\*\* must be pasted", "numbers must be pasted"),
    ("docs/report/chapter_risk_score.md",
     r"\[FILL: date and wording of what sir agreed about the scope\.\]", SCOPE),
    ("docs/report/chapter_risk_score.md",
     r"\[FILL: one sentence per factor[^\]]*\]", FACTORS),
    ("docs/report/chapter_risk_score.md",
     r"\[FILL: frozen version from docs/risk_model\.md\]", "v1.0 (data/risk_weights.json)"),
    ("docs/report/chapter_risk_score.md",
     r"\[FILL: X, Y, Z and the date agreed with sir\]",
     "X = 5 years (scenarios 2, 5 and 10), Y = 2 years, Z = 10 years as the central value (scenarios 5, 10 and 20), "
     "agreed with sir on 2026-10-17 (data/manual_facts.json)"),
    ("docs/report/chapter_pqc_advisor.md",
     r"\[FILL: when to choose another[^\]]*\]", PARAMS),
    ("docs/report/chapter_pqc_advisor.md",
     r"was an initial public draft when last checked on \[FILL: date\], so these dates are proposed\.",
     f"was finalised on 27 October 2026 (csrc.nist.gov/pubs/ir/8547/final; last checked on {TODAY}). Outside federal systems it is guidance."),
    ("docs/viva_answers_week6.md",
     r"<name the exact residual factors[^>]*>", RESIDUAL),
    ("docs/viva_answers_week6.md",
     r"<copy from the agreed Scope paragraph; claim nothing that was not measured>",
     "See docs/report/scope.md for exactly what was delivered and what sir agreed. We claim no Java, JavaScript or LLM result that we did not measure (Plan v3, Section 1)."),
    ("docs/viva_answers_week6.md",
     r"X = <years>, Y = <years>, Z = <central value, with scenarios 5, 10, 20>, agreed with sir on <date>,",
     "X = 5 years, Y = 2 years, Z = 10 years central with scenarios 5, 10 and 20, agreed with sir on 2026-10-17,"),
    ("docs/q14_resource_estimates.md",
     r"\| 4,099 for n = 2048 \| VERIFY \|", "| 4,099 for n = 2048 | n/a (not used by F2) |"),
    ("docs/q14_resource_estimates.md",
     r"^\| Newer architecture claims \(2026\)[^\n]*\r?\n", ""),
    ("docs/deck_check.md",
     r"^\| ____ \| NIST IR 8547: 2030 deprecated / 2035 disallowed[^\n]*",
     "| ____ | NIST IR 8547: 2030 deprecated / 2035 disallowed | https://csrc.nist.gov/pubs/ir/8547/final | "
     "Final, published 27 October 2026; the 2030 and 2035 dates were kept; guidance outside federal systems | "
     "Replace 'proposed' wording with the final status |"),
    ("docs/deck_check.md",
     r"^\| ____ \| FIPS 203, 204, 205 published August 2024 \| NIST FIPS pages \| ____ \| ____ \|",
     "| ____ | FIPS 203, 204, 205 published August 2024 | NIST FIPS pages | Correct: published as final standards in August 2024 | None |"),
    ("docs/deck_check.md",
     r"Status of IR 8547 last checked: ____ \(re-check the NIST page before quoting\)\.",
     f"Status of IR 8547: final, published 27 October 2026; last checked {TODAY} (re-check the NIST page before quoting)."),
]

try:
    FIXES.append(("docs/report/chapter_risk_score.md", r"\[FILL: table from outputs/risk_scores\.json[^\]]*\]", risk_table()))
except Exception as exc:
    print("could not build the risk table:", exc)

for name, pattern, repl in FIXES:
    p = Path(name)
    if not p.exists():
        print("MISSING FILE:", name)
        continue
    with open(p, encoding="utf-8", newline="") as f:
        t = f.read()
    nl = "\r\n" if "\r\n" in t else "\n"
    r = repl.replace("\r\n", "\n").replace("\n", nl)
    new, n = re.subn(pattern, lambda m: r, t, flags=re.M)
    if n == 1:
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        print("fixed  :", name, "|", pattern[:55])
    else:
        print(f"SKIPPED ({n} matches):", name, "|", pattern[:55])
