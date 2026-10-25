"""The analyzer report: allowed values and the rules every report must follow (docs/analyzer_spec.md)."""

SCHEMA_VERSION = 1
HIDING_METHODS = ("lsb", "xor_lsb", "clean_or_unknown")
CIPHER_KINDS = ("textbook_rsa", "oaep_style", "ml_kem_aes_gcm", "unrecognised")
STATES = ("broken_toy", "broken_classical_small_key", "vulnerable_estimate", "resists", "unrecognised")
BROKEN = ("broken_toy", "broken_classical_small_key")
QUANTUM_LABEL = "Aer simulator, toy size"
TIME_WORDS = ("second", "minute", "hour", "day", "year", "time")        # an estimate never carries a time


def validate_report(report):
    """Return a list of problems (empty list = the report follows the rules)."""
    p = []
    for key in ("schema_version", "created_utc", "input", "pipeline_status", "limits"):
        if key not in report:
            p.append(f"missing key: {key}")
    if report.get("schema_version") != SCHEMA_VERSION:
        p.append(f"schema_version must be {SCHEMA_VERSION}")
    complete = report.get("pipeline_status") == "complete"
    attack = report.get("attack") or {}
    state = attack.get("state")

    if complete and state not in STATES:
        p.append(f"attack.state must be one of {STATES} when the pipeline is complete")
    if not complete and state is not None:
        p.append("an incomplete pipeline must not claim an attack state")
    if (report.get("hiding") or {}).get("method") not in (None,) + HIDING_METHODS:
        p.append("hiding.method is not an allowed value")
    if (report.get("cipher") or {}).get("kind") not in (None,) + CIPHER_KINDS:
        p.append("cipher.kind is not an allowed value")

    if state in BROKEN:
        if not attack.get("recovered_message"):
            p.append("a broken state needs recovered_message")
    elif "recovered_message" in attack:
        p.append(f"recovered_message is only allowed for {BROKEN}")
    if state == "broken_toy":
        if attack.get("label") != QUANTUM_LABEL:
            p.append(f"broken_toy needs label {QUANTUM_LABEL!r}")
        if not attack.get("run_id"):
            p.append("broken_toy needs the run_id of its evidence record")
    if state == "vulnerable_estimate":
        est = report.get("estimate") or {}
        if not est:
            p.append("vulnerable_estimate needs an estimate block")
        for k in est:
            if any(w in k.lower() for w in TIME_WORDS):
                p.append(f"estimate must not carry a time (found key {k!r})")
        if "ESTIMATE" not in str(est.get("published", "")):
            p.append("estimate.published must say ESTIMATE")
    if state == "unrecognised" and report.get("score") is not None:
        p.append("an unrecognised image must not get a score")
    if state in ("resists", "vulnerable_estimate", "broken_toy", "broken_classical_small_key") and not report.get("score"):
        p.append(f"state {state} needs a score from the engine")
    return p
