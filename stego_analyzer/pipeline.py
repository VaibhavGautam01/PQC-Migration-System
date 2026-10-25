"""The Stego Analyzer pipeline: image in, report out.  Owner: Tarun.  (design: docs/analyzer_spec.md)

    accept -> detect hiding method -> extract blob -> identify cipher -> route
           -> (Shor at toy size | small-key attack | estimate | resists | unrecognised) -> score -> report

The score is not computed here: layer_inputs() builds one layer configuration and risk_score.score_layer()
scores it, so the analyzer's number equals the engine's number for the same configuration.

The image does not carry the modulus: the attacker holds the stego image AND the public key (plan Section 5).
So analyze() takes an optional public key {"n": int, "e": int}. Without it the analyzer can detect, extract and
(by length) recognise an ML-KEM payload, but it cannot attack an RSA payload and says so.

A stage that is not built yet raises NotImplementedStage. The pipeline then stops, says which stage, and
the report carries no attack state. Nothing is invented to fill the gap.
"""
import hashlib
import sys
from pathlib import Path

from . import NotImplementedStage, schema
from . import attack_classical, cipher_identify, detect_method, extract, quantum_stage
from . import estimate as estimate_stage

ROOT = Path(__file__).resolve().parent.parent
try:
    from src import quantum_runs as QR
    from src import risk_score as rs
except ImportError:                                    # root not on sys.path (streamlit run src/...)
    sys.path.insert(0, str(ROOT))
    from src import quantum_runs as QR
    from src import risk_score as rs

TOY_MAX_N = 35               # largest N the Q2 circuit is committed to (221 if the stretch goal is met)
SMALL_KEY_MAX_BITS = 96      # largest modulus our existing small-key attacks handled (video 95 bit); Vaibhav to confirm
SESSION_REPORT = Path("outputs") / "tmp_analyzer_report.json"      # untracked (outputs/tmp_* is ignored)

LIMITS = ["The image does not carry the modulus: breaking an RSA payload needs the public key (n, e).",
          "Detector and identifier accuracy are measured only on images made by our own projects; "
          "accuracy on other tools' images is unknown.",
          "A weighted score, not a probability.",
          "Quantum results are simulator results at toy size; real-size keys get labelled estimates, never a time.",
          "Scope with sir: flow agreed on 22 October 2026; the format limit is not confirmed yet."]

DEFAULT_STAGES = {"detect": detect_method.detect, "extract": extract.extract,
                  "identify": cipher_identify.identify, "attack_toy": quantum_stage.attack_toy,
                  "attack_classical": attack_classical.attack, "estimate": estimate_stage.estimate}


def choose_route(cipher, toy_max_n=TOY_MAX_N, small_key_max_bits=SMALL_KEY_MAX_BITS):
    """Which attack path a cipher takes: shor_toy, classical_small_key, estimate, resists, needs_public_key
    or unrecognised."""
    kind = (cipher or {}).get("kind")
    if kind == "ml_kem_aes_gcm":
        return "resists"
    if kind in ("oaep_style", "textbook_rsa") and cipher.get("n") is None and cipher.get("modulus_bits") is None:
        return "needs_public_key"    # the image does not carry the modulus
    if kind == "oaep_style":
        return "estimate"            # the padding cannot be undone with a toy modulus; report the estimate
    if kind == "textbook_rsa":
        n, bits = cipher.get("n"), cipher.get("modulus_bits")
        if n is not None and n <= toy_max_n:
            return "shor_toy"
        if bits is not None and bits <= small_key_max_bits:
            return "classical_small_key"
        return "estimate"
    return "unrecognised"


def exposure_for(method):
    """F6 input from the hiding method. LSB has no secret (keyless). XOR-LSB is keyed, but the header scan can
    still find the frames, so it is 'bypassable'. Assumption, to be confirmed by Yatharth."""
    return "keyless" if method == "lsb" else "bypassable"


def layer_inputs(cipher, method="lsb"):
    """The layer configuration for the engine, or None when the cipher is not recognised."""
    kind = (cipher or {}).get("kind")
    exposure = exposure_for(method)
    if kind == "textbook_rsa":
        return dict(category="shor_broken", construction="no_padding_deterministic", exposure=exposure,
                    modulus_bits=cipher.get("modulus_bits"))
    if kind == "oaep_style":
        return dict(category="shor_broken", construction="oaep", exposure=exposure,
                    modulus_bits=cipher.get("modulus_bits"))
    if kind == "ml_kem_aes_gcm":
        return dict(category="nist_pqc", construction="aead", exposure=exposure)
    return None


def score_for(cipher, method="lsb"):
    """Score from the SAME engine as the rest of the project, or None for an unrecognised cipher."""
    inputs = layer_inputs(cipher, method)
    if inputs is None:
        return None
    s = rs.score_layer(**inputs)
    return {"quantum": round(s["quantum"], 1), "classical": round(s["classical"], 1),
            "overall": round(s["overall"], 1), "band": s["band"],
            "weights_version": rs.load_weights()["version"], "layer_inputs": inputs}


def _technique(cipher):
    kind = cipher.get("kind")
    if kind in ("textbook_rsa", "oaep_style"):
        return {"algorithm": "shor", "reason": "RSA is broken by Shor's algorithm"}
    if kind == "ml_kem_aes_gcm":
        return {"algorithm": "grover", "reason": "ML-KEM has nothing for Shor to factor; AES-256 is only "
                "weakened by Grover to about 128 bits, which is no break at real size"}
    return {"algorithm": "none", "reason": "cipher not recognised"}


class _Stop(Exception):
    pass


def _call(report, name, fn, *args):
    """Run one stage, log it, and stop the pipeline (not crash) if it is missing or fails."""
    try:
        result = fn(*args)
    except NotImplementedStage:
        report["stage_log"].append({"stage": name, "status": "not implemented yet"})
        report["pipeline_status"] = f"stopped at {name}: not implemented yet"
        raise _Stop()
    except Exception as exc:                                    # a bug in a stage must be visible, not hidden
        report["stage_log"].append({"stage": name, "status": f"error: {exc.__class__.__name__}: {exc}"})
        report["pipeline_status"] = f"stopped at {name}: {exc.__class__.__name__}: {exc}"
        raise _Stop()
    report["stage_log"].append({"stage": name, "status": "ok"})
    return result


def _unrecognised(report, reason):
    report["attack"] = {"state": "unrecognised", "reason": reason}
    report["technique"] = _technique({})
    report["score"] = None


def _clean_key(public_key):
    if not public_key:
        return None
    n, e = int(public_key["n"]), int(public_key["e"])
    if n < 4 or e < 2:
        raise ValueError("public key needs n >= 4 and e >= 2")
    return {"n": n, "e": e}


def analyze(path, stages=None, public_key=None):
    """Analyse one stego image and return the report dict (schema in docs/analyzer_spec.md).

    public_key: optional {"n": int, "e": int}, the attacker's public key (needed to attack RSA).
    stages: optional dict that replaces stage functions (tests use it); see DEFAULT_STAGES for the keys.
    Raises FileNotFoundError if the file does not exist.
    """
    public_key = _clean_key(public_key)
    st = {**DEFAULT_STAGES, **(stages or {})}
    path = Path(path)
    data = path.read_bytes()                                   # FileNotFoundError is the caller's to handle
    report = {"schema_version": schema.SCHEMA_VERSION, "created_utc": QR.now_utc(),
              "input": {"file": path.name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
                        "public_key": public_key},
              "pipeline_status": "complete", "stage_log": [{"stage": "accept", "status": "ok"}],
              "hiding": None, "extraction": None, "cipher": None, "technique": None, "attack": None,
              "estimate": None, "score": None, "limits": list(LIMITS)}
    try:
        hiding = _call(report, "detect_method", st["detect"], str(path))
        report["hiding"] = hiding
        if hiding["method"] not in ("lsb", "xor_lsb"):
            _unrecognised(report, "hiding method not in our formats (clean or unknown)")
            return _finish(report)

        ext = _call(report, "extract", st["extract"], str(path), hiding["method"])
        report["extraction"] = {"ok": ext["ok"], "blob_bytes": len(ext.get("blob") or b""),
                                "source": ext.get("source")}
        if not ext["ok"]:
            _unrecognised(report, "nothing could be extracted")
            return _finish(report)

        cipher = _call(report, "cipher_identify", st["identify"], ext["blob"], public_key)
        report["cipher"] = cipher
        if public_key and cipher.get("kind") in ("textbook_rsa", "oaep_style"):
            if cipher.get("n") is None:
                cipher["n"] = public_key["n"]
            if cipher.get("modulus_bits") is None:
                cipher["modulus_bits"] = public_key["n"].bit_length()
        route = choose_route(cipher)
        if route == "unrecognised":
            _unrecognised(report, "cipher not in our formats")
            return _finish(report)
        report["technique"] = _technique(cipher)
        if route == "needs_public_key":
            _unrecognised(report, "modulus unknown: the image does not carry the public key; give it with "
                                  "--public-key N,E (or the two fields on the dashboard page)")
            report["technique"] = _technique(cipher)
            return _finish(report)

        if route == "shor_toy":
            report["attack"] = _call(report, "quantum_stage", st["attack_toy"], public_key, ext["blob"])
        elif route == "classical_small_key":
            report["attack"] = _call(report, "attack_classical", st["attack_classical"], public_key, ext["blob"])
        elif route == "estimate":
            report["estimate"] = _call(report, "estimate", st["estimate"], cipher["modulus_bits"])
            report["attack"] = {"state": "vulnerable_estimate"}
        else:                                                   # resists
            report["attack"] = {"state": "resists", "reason": "extraction works, nothing to factor"}
        report["score"] = score_for(cipher, hiding["method"])
    except _Stop:
        pass
    return _finish(report)


def _finish(report):
    report["problems"] = schema.validate_report(report)
    return report


def stage_rows(report):
    """Rows for the dashboard table: one per stage that ran."""
    return [{"stage": r["stage"], "status": r["status"]} for r in report["stage_log"]]


def evidence_rows(report):
    """Where the evidence for a result lives, for the dashboard and the report."""
    rows = []
    a = report.get("attack") or {}
    ev = a.get("evidence") or {}
    if ev:
        rows.append({"what": "Shor runs (evidence records)", "where": ev.get("record_file"), "id": ev.get("run_id")})
        rows.append({"what": "circuit summaries", "where": "docs/circuits or outputs/tmp_analyzer_diagrams",
                     "id": ", ".join(t["run_id"] for t in a.get("runs_tried", []))})
    if report.get("estimate"):
        rows.append({"what": "estimate sources", "where": "data/published_estimates.json, outputs/q4_metrics.json",
                     "id": ""})
    if report.get("score"):
        rows.append({"what": "score", "where": "src/risk_score.py with data/risk_weights.json",
                     "id": report["score"]["weights_version"]})
    return rows


def summary_text(report):
    """A few plain lines for the command line."""
    lines = [f"Image: {report['input']['file']}  (sha256 {report['input']['sha256'][:12]}...)"]
    if report.get("hiding"):
        h = report["hiding"]
        lines.append(f"Hiding method: {h['method']} (confidence {h.get('confidence')})")
    if report.get("cipher"):
        lines.append(f"Cipher: {report['cipher']['kind']}")
    a = report.get("attack") or {}
    if a.get("state"):
        lines.append(f"Result: {a['state']}" + (f" ({a['label']})" if a.get("label") else ""))
    if report.get("score"):
        s = report["score"]
        lines.append(f"Risk score: {s['overall']} ({s['band']}), quantum {s['quantum']}, classical {s['classical']}, "
                     f"weights {s['weights_version']}")
    lines.append(f"Pipeline: {report['pipeline_status']}")
    for p in report.get("problems", []):
        lines.append(f"PROBLEM: {p}")
    return "\n".join(lines)
