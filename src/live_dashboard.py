"""
live_dashboard.py - working Streamlit dashboard for the PQC Migration Advisor.

Everything on screen is read from the real pipeline outputs, nothing is
hard-coded:
    outputs/findings.json        scanner + edge-case results
    docs/cbom.json               Cryptographic Bill of Materials
    data/manual_facts.json       manual size overrides (confirmed / unconfirmed)
    data/demo_results.json       saved Shor's demo runs (optional)

It can also DO things: run Shor's algorithm on the Aer simulator, calculate
qubit costs for any key size, and run the pipeline steps with one click.

Put this file in src/ and run from the repo root:
    pip install -r requirements.txt
    streamlit run src/live_dashboard.py
"""
import html
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from fractions import Fraction

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:                                   # streamlit run puts src/ on the path, tests use the package
    from src import risk_page_data as rpd
except ImportError:
    import risk_page_data as rpd

try:
    from src import advisor_page_data as adv
except ImportError:
    import advisor_page_data as adv

try:
    from src import before_after_page_data as ba
except ImportError:
    import before_after_page_data as ba

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINDINGS = os.path.join(ROOT, "outputs", "findings.json")
CBOM = os.path.join(ROOT, "docs", "cbom.json")
CBOM_MD = os.path.join(ROOT, "docs", "cbom.md")
FACTS = os.path.join(ROOT, "data", "manual_facts.json")
DEMO = os.path.join(ROOT, "data", "demo_results.json")
RISK = os.path.join(ROOT, "outputs", "risk_scores.json")
ADVISOR = os.path.join(ROOT, "data", "pqc_recommendations.json")
BEFORE_AFTER = os.path.join(ROOT, "outputs", "before_after_image.json")
TARGETS = [os.path.join(ROOT, "data", "targets", "steganography"),
           os.path.join(ROOT, "data", "targets", "final-year-part1")]

SHOR = {"RSA", "ECC", "DSA", "DH"}      # broken outright by Shor's algorithm
GROVER = {"AES", "SHA"}                 # strength roughly halved by Grover's
PRIM_COLORS = {"RSA": "#00B0FF", "ECC": "#B388FF", "DSA": "#FF4081",
               "DH": "#1DE9B6", "AES": "#FFAB40", "SHA": "#76FF03"}
CONF_COLORS = {"high": "#FF5252", "medium": "#FFB300", "low": "#90A4AE"}
CLASSICAL_COLORS = {"practically-breakable": "#FF1744", "below-minimum": "#FF9100",
                    "meets-minimum": "#00E676", "unknown": "#90A4AE",
                    "not-applicable": "#607D8B"}
CLASSICAL_OK = {"meets-minimum", "unknown", "not-applicable"}

st.set_page_config(page_title="PQC Migration Advisor", page_icon="🔐", layout="wide")

st.markdown("""
<style>
.stApp{background:radial-gradient(circle at 12% 0%,#1d2160 0%,#0b0e1f 52%,#070914 100%);color:#eef1fb}
[data-testid="stSidebar"]{background:#0e1230;border-right:1px solid #262d5a}
h1,h2,h3,h4,p,label,span,li{color:#eef1fb}
.hero{background:linear-gradient(120deg,#2979ff,#7c4dff 45%,#ff4081 80%,#ffab40);border-radius:20px;
 padding:24px 30px;margin-bottom:16px;box-shadow:0 10px 40px #2979ff44}
.hero h1{margin:0;font-size:2rem;color:#fff}.hero p{margin:4px 0 0;color:#ffffffdd}
.chip{display:inline-block;background:#ffffff2e;border-radius:99px;padding:3px 12px;font-size:.78rem;margin:10px 6px 0 0;color:#fff}
.kpi{border-radius:16px;padding:16px 18px;background:#141939;border:1px solid #2a3170;border-top:4px solid var(--c)}
.kpi b{display:block;font-size:2rem;color:var(--c)}.kpi span{font-size:.8rem;color:#aab2e0}
.card{background:#141939;border:1px solid #2a3170;border-radius:16px;padding:14px 18px;margin:8px 0}
.badge{display:inline-block;border-radius:99px;padding:2px 11px;font-size:.74rem;font-weight:700;color:#0b0e1f;margin-right:6px}
.note{border-left:4px solid #FFAB00;background:#1a1f45;border-radius:10px;padding:10px 14px;margin:8px 0;font-size:.9rem}
.good{border-left-color:#00E676}.bad{border-left-color:#FF1744}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers
def esc(x):
    """HTML-escape any value before it goes into unsafe_allow_html markup."""
    return html.escape(str(x))


def kpi_row(items):
    """Row of coloured KPI cards: items = [(label, value, colour)]."""
    for col, (label, val, color) in zip(st.columns(len(items)), items):
        col.markdown(f'<div class="kpi" style="--c:{color}"><b>{esc(val)}</b><span>{esc(label)}</span></div>',
                     unsafe_allow_html=True)
    st.write("")


def badge(text, color):
    """Small coloured pill."""
    return f'<span class="badge" style="background:{color}">{esc(text)}</span>'


def style(fig, h=340):
    """Shared dark look for every plotly chart."""
    fig.update_layout(height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font_color="#dfe4ff", margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(gridcolor="#262d5a")
    fig.update_yaxes(gridcolor="#262d5a")
    return fig


@st.cache_data(show_spinner=False)
def _load_json(path, mtime):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def get_json(path):
    """Read a JSON file (cached per modification time). None if missing or broken."""
    if not os.path.isfile(path):
        return None
    try:
        return _load_json(path, os.path.getmtime(path))
    except (OSError, ValueError):
        return None


@st.cache_resource(show_spinner=False)
def load_module(name, rel):
    """Import a project file by path (notebook/ is not a package)."""
    path = os.path.join(ROOT, rel)
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def shor_qubits(bits):
    """Logical qubits for Shor's on an n-bit modulus (project estimator, 2n+3)."""
    try:
        return load_module("qubit_estimator", "notebook/qubit_estimator.py").shor_logical_qubits(int(bits))
    except (OSError, ImportError, AttributeError, ValueError):
        return 2 * int(bits) + 3


def findings_frame(raw):
    """Findings as a DataFrame with a few helper columns."""
    df = pd.DataFrame(raw.get("findings", []))
    if df.empty:
        return df
    for col in ("key_size", "modulus_bits"):
        df[col] = pd.to_numeric(df.get(col), errors="coerce")
    df["where"] = df["file"] + ":" + df["line"].astype(str)
    df["quantum"] = df["primitive"].map(lambda p: "Shor's" if p in SHOR else "Grover's" if p in GROVER else "Other")
    return df


# ------------------------------------------------------------------- load
raw = get_json(FINDINGS)
cbom = get_json(CBOM)
facts = get_json(FACTS) or {}
if raw is None:
    st.error("outputs/findings.json not found or unreadable. Run:  python src/run_all.py")
    st.stop()
df = findings_frame(raw)
entries = (cbom or {}).get("entries", [])

st.markdown(f"""
<div class="hero"><h1>🔐 PQC Migration Advisor</h1>
<p>Quantum-Vulnerability Testing Pipeline · Detect → Map → Estimate → Migrate</p>
<span class="chip">Scanner v{esc(raw.get('scanner_version', '?'))}</span>
<span class="chip">{len(df)} findings</span>
<span class="chip">{len(raw.get('projects', {}))} projects</span>
<span class="chip">{len(entries)} CBOM entries</span>
<span class="chip">HCST Mathura · AKTU</span></div>""", unsafe_allow_html=True)

PAGES = ["📊 Overview", "🔎 Findings", "🧾 CBOM and risk", "🎯 Risk score", "🔁 Before and after", "🧭 PQC advisor", "📈 Qubit calculator",
         "🎬 Shor's demo (live)", "🛡️ Migration demo", "⚙️ Pipeline"]
page = st.sidebar.radio("Navigate", PAGES, key="nav")
st.sidebar.caption("Data: outputs/findings.json, docs/cbom.json")
st.sidebar.caption("Refresh the page after re-running the pipeline.")


# ================================================================ OVERVIEW
def page_overview():
    """KPIs, charts and honest data-quality warnings."""
    rsa = df[df["primitive"] == "RSA"]
    known = int(rsa["modulus_bits"].notna().sum())
    weak = sum(1 for e in entries if e.get("classical_risk", {}).get("status") not in CLASSICAL_OK)
    kpi_row([("Findings", len(df), "#00B0FF"),
             ("Files with crypto", df["file"].nunique() if len(df) else 0, "#B388FF"),
             ("Broken by Shor's", int(df["primitive"].isin(SHOR).sum()), "#FF4081"),
             ("Weakened by Grover's", int(df["primitive"].isin(GROVER).sum()), "#00E5FF"),
             ("CBOM entries", len(entries), "#1DE9B6"),
             ("Classical key problems", weak, "#FF1744")])

    c1, c2 = st.columns(2)
    d = df["primitive"].value_counts().reset_index()
    d.columns = ["primitive", "count"]
    c1.plotly_chart(style(px.pie(d, names="primitive", values="count", hole=0.55, color="primitive",
                                 color_discrete_map=PRIM_COLORS, title="Findings by primitive")), key="ov_pie")
    d = df.groupby(["project", "primitive"]).size().reset_index(name="count")
    c2.plotly_chart(style(px.bar(d, x="project", y="count", color="primitive", barmode="stack",
                                 color_discrete_map=PRIM_COLORS, title="Findings by project")), key="ov_proj")

    c3, c4 = st.columns(2)
    if entries:
        d = pd.Series([e.get("classical_risk", {}).get("status", "unknown") for e in entries]
                      ).value_counts().reset_index()
        d.columns = ["status", "entries"]
        c3.plotly_chart(style(px.bar(d, x="status", y="entries", color="status",
                                     color_discrete_map=CLASSICAL_COLORS,
                                     title="CBOM entries by classical key-strength status")), key="ov_cls")
        q = [(f"{e['id']} · {e['key_size_bits']}-bit", e["quantum_risk"]["logical_qubits_estimate"])
             for e in entries if e.get("quantum_risk", {}).get("logical_qubits_estimate")]
        if q:
            dq = pd.DataFrame(q, columns=["entry", "logical qubits"])
            c4.plotly_chart(style(px.bar(dq, x="entry", y="logical qubits", text="logical qubits",
                                         title="Shor's logical qubits (2n + 3) per entry",
                                         color_discrete_sequence=["#7C4DFF"])), key="ov_q")
    else:
        c3.info("docs/cbom.json not found. Build it on the Pipeline page.")

    st.markdown("#### 🧪 Data quality")
    if len(rsa):
        st.progress(known / len(rsa), text=f"RSA findings with a known key size: {known} of {len(rsa)}")
    unverified = [e for e in entries if e.get("size_status") in ("unknown", "unverified")]
    ov = facts.get("size_overrides", [])
    notes = []
    if len(rsa) and known < len(rsa):
        notes.append(f"{len(rsa) - known} RSA findings have no key size, so no qubit estimate exists for them.")
    if unverified:
        notes.append(f"{len(unverified)} CBOM entries have an unknown or unverified key size.")
    for o in ov:
        if not o.get("confirmed"):
            notes.append(f"Manual override '{o.get('id')}' is NOT confirmed, so it is not applied.")
    if notes:
        for n in notes:
            st.markdown(f'<div class="note">⚠️ {esc(n)}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="note good">✅ All findings have verified key sizes.</div>', unsafe_allow_html=True)
    st.caption("Qubit counts are logical-qubit estimates at toy-to-real sizes. They exclude error correction, "
               "and no quantum computer today can break RSA-1024 or larger.")


# ================================================================ FINDINGS
def page_findings():
    """Filterable findings table, code view and edge-case flags."""
    tf, te = st.tabs(["🔎 All findings", "🕵️ Edge-case flags"])
    with tf:
        c = st.columns([2, 2, 2, 3])
        projects = c[0].multiselect("Project", sorted(df["project"].unique()), default=sorted(df["project"].unique()))
        prims = c[1].multiselect("Primitive", sorted(df["primitive"].unique()), default=sorted(df["primitive"].unique()))
        confs = c[2].multiselect("Confidence", ["high", "medium", "low"], default=["high", "medium", "low"])
        q = c[3].text_input("🔎 Search file, pattern or code")
        f = df[df["project"].isin(projects) & df["primitive"].isin(prims) & df["confidence"].isin(confs)]
        if q:
            hay = (f["file"] + " " + f["pattern_id"] + " " + f["snippet"].fillna("")).str.lower()
            f = f[hay.str.contains(q.lower(), regex=False)]
        st.caption(f"Showing {len(f)} of {len(df)} findings")
        cols = ["project", "where", "primitive", "quantum", "pattern_id", "confidence",
                "key_size", "modulus_bits", "snippet"]
        st.dataframe(f[cols], hide_index=True, height=360)
        st.download_button("⬇️ Download as CSV", f[cols].to_csv(index=False).encode("utf-8"),
                           "findings_filtered.csv", "text/csv")
        if len(f):
            f = f.reset_index(drop=True)
            labels = [f"{r.project} · {r.where} · {r.pattern_id}" for r in f.itertuples()]
            pick = st.selectbox("Inspect one finding", range(len(f)), format_func=lambda i: labels[i])
            r = f.iloc[pick]
            st.markdown(badge(r["primitive"], PRIM_COLORS.get(r["primitive"], "#90A4AE")) +
                        badge(r["confidence"], CONF_COLORS.get(r["confidence"], "#90A4AE")) +
                        badge(r["quantum"], "#B388FF"), unsafe_allow_html=True)
            st.write(r.get("description", ""))
            st.code(str(r["snippet"]), language="python")
            if pd.notna(r["modulus_bits"]):
                st.write(f"Modulus: **{int(r['modulus_bits'])} bits** · basis: {r.get('size_basis')}")
            else:
                st.write("Key size: not visible to the scanner.")
    with te:
        ec = raw.get("edge_cases", {})
        tot = raw.get("edge_case_totals", {})
        kpi_row([("Missing-padding flags", tot.get("padding", 0), "#FF1744"),
                 ("Indirect-usage flags", tot.get("indirect_usage", 0), "#FFAB40")])
        for proj, flags in ec.items():
            with st.expander(f"{proj}", expanded=True):
                for kind, label in (("padding", "Missing padding (textbook RSA)"),
                                    ("indirect_usage", "Crypto imported from another file")):
                    rows = flags.get(kind, [])
                    st.markdown(f"**{label}**: {len(rows)}")
                    if rows:
                        st.dataframe(pd.DataFrame(rows)[["file", "line", "flag", "detail"]], hide_index=True)


# ================================================================ CBOM
def page_cbom():
    """CBOM entries with quantum, classical and padding risk side by side."""
    if not entries:
        st.warning("docs/cbom.json not found. Build it on the Pipeline page.")
        return
    rows = []
    for e in entries:
        q, c, p, r = e["quantum_risk"], e["classical_risk"], e["padding_risk"], e["recommended_pqc"]
        rows.append({"ID": e["id"], "Project": e["project"], "Primitive": e["primitive"],
                     "Size (bits)": e.get("key_size_bits"), "Size status": e.get("size_status"),
                     "Quantum": q.get("impact"), "Logical qubits": q.get("logical_qubits_estimate"),
                     "Classical": c.get("status"), "Padding": p.get("status"),
                     "Recommended PQC": r.get("algorithm")})
    st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("Padding and small-key weaknesses are classical problems, reported separately "
               "from the quantum score.")
    d1, d2 = st.columns(2)
    d1.download_button("⬇️ cbom.json", json.dumps(cbom, indent=2).encode("utf-8"), "cbom.json", "application/json")
    if os.path.isfile(CBOM_MD):
        with open(CBOM_MD, encoding="utf-8-sig") as fh:
            d2.download_button("⬇️ cbom.md", fh.read().encode("utf-8"), "cbom.md", "text/markdown")

    st.markdown("#### Entry details")
    for e in entries:
        q, c, p, r = e["quantum_risk"], e["classical_risk"], e["padding_risk"], e["recommended_pqc"]
        col = CLASSICAL_COLORS.get(c.get("status"), "#90A4AE")
        head = f"{e['id']} · {e['project']} · {e['primitive']} · {e.get('key_size_bits') or 'size unknown'}"
        with st.expander(head):
            st.markdown(badge(q.get("impact", "?"), "#7C4DFF") + badge("classical: " + str(c.get("status")), col)
                        + badge("size: " + str(e.get("size_status")), "#90A4AE"), unsafe_allow_html=True)
            m = st.columns(3)
            m[0].metric("Quantum algorithm", q.get("algorithm", "-"))
            m[1].metric("Logical qubits (est.)", q.get("logical_qubits_estimate") or "-")
            m[2].metric("Recommended", r.get("algorithm", "-"))
            st.markdown(f"**Classical risk:** {c.get('basis', '')}")
            st.markdown(f"**Padding:** {p.get('weakness', p.get('status', ''))}")
            st.markdown(f"**Why {r.get('algorithm')}** ({r.get('standard')}): {r.get('rationale', '')}")
            if q.get("estimate_basis"):
                st.caption(q["estimate_basis"])
            st.markdown("**Where:** " + ", ".join(f"`{x}`" for x in e.get("files", [])))


# ================================================================ CALCULATOR
def page_calculator():
    """Qubit cost for any key size, with the project's own entries marked."""
    kind = st.radio("Algorithm family", ["Public-key (RSA / DH / DSA / ECC) - Shor's",
                                         "Symmetric (AES / SHA) - Grover's"], horizontal=True)
    if kind.startswith("Public"):
        bits = st.slider("Modulus size (bits)", 128, 8192, 2048, step=64)
        q = shor_qubits(bits)
        kpi_row([("Modulus bits", bits, "#00B0FF"), ("Logical qubits (2n+3)", f"{q:,}", "#7C4DFF"),
                 ("Verdict", "Broken by Shor's", "#FF1744")])
        xs = list(range(128, 8193, 64))
        fig = go.Figure(go.Scatter(x=xs, y=[shor_qubits(x) for x in xs], mode="lines",
                                   line=dict(color="#7C4DFF", width=3), name="2n + 3"))
        pts = [(e["key_size_bits"], e["quantum_risk"]["logical_qubits_estimate"], e["id"]) for e in entries
               if e.get("quantum_risk", {}).get("logical_qubits_estimate")]
        if pts:
            fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="markers+text",
                                     text=[p[2] for p in pts], textposition="top center",
                                     marker=dict(size=12, color="#FF4081"), name="Your CBOM entries"))
        fig.add_trace(go.Scatter(x=[bits], y=[q], mode="markers", marker=dict(size=14, color="#FFAB40"),
                                 name="Selected"))
        fig.update_layout(xaxis_title="Modulus size (bits)", yaxis_title="Logical qubits")
        st.plotly_chart(style(fig, 380), key="calc_shor")
        rows = [{"Modulus (bits)": b, "Logical qubits": shor_qubits(b)} for b in (256, 512, 1024, 2048, 3072, 4096)]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.markdown('<div class="note">⚠️ These are <b>logical</b> qubits without error correction. A published '
                    'estimate (Gidney and Ekera, 2021) puts RSA-2048 at about 20 million noisy physical qubits. '
                    'Small moduli (under 1024 bits) are breakable on ordinary computers with no quantum '
                    'computer at all.</div>', unsafe_allow_html=True)
    else:
        bits = st.select_slider("Symmetric key / hash output size (bits)", [64, 80, 112, 128, 160, 192, 224, 256, 384, 512],
                                value=128)
        mod = load_module("qubit_estimator", "notebook/qubit_estimator.py")
        eff = mod.grover_effective_security(bits)
        kpi_row([("Key bits", bits, "#00B0FF"), ("Effective security under Grover's", f"{eff} bits", "#00E5FF")])
        st.write(mod.grover_verdict(bits))
        xs = [64, 80, 112, 128, 160, 192, 224, 256, 384, 512]
        fig = go.Figure([go.Bar(x=[str(x) for x in xs], y=xs, name="Classical", marker_color="#7C4DFF"),
                         go.Bar(x=[str(x) for x in xs], y=[mod.grover_effective_security(x) for x in xs],
                                name="After Grover's", marker_color="#00E5FF")])
        fig.update_layout(barmode="group", xaxis_title="Key size (bits)", yaxis_title="Security (bits)")
        st.plotly_chart(style(fig, 360), key="calc_grover")
        st.caption("Grover's is a quadratic speed-up, not a full break. AES-256 keeps about 128-bit security.")


# ================================================================ SHOR DEMO
def _demo_cases():
    """Case table: N -> (a, counting qubits, work qubits, expected factors, runner name)."""
    return {15: (7, 4, 4, (3, 5), "run_shor_attempts"),
            21: (2, 8, 5, (3, 7), "run_shor_attempts_n21")}


def save_demo(n, shots, successes, factors, env):
    """Write one real run into data/demo_results.json (replaces an earlier run of the same N)."""
    doc = get_json(DEMO) or {"_readme": "Real simulator runs saved from the dashboard.",
                              "environment": env, "cases": [], "recordings": []}
    doc = json.loads(json.dumps(doc))
    doc["environment"] = env
    doc["cases"] = [c for c in doc.get("cases", []) if c.get("N") != n]
    doc["cases"].append({"N": n, "expected_factors": list(factors), "runs": shots, "successes": successes,
                         "backend": "simulator", "notes": "saved from live_dashboard.py"})
    doc["cases"].sort(key=lambda c: c["N"])
    os.makedirs(os.path.dirname(DEMO), exist_ok=True)
    with open(DEMO, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
        fh.write("\n")
    st.cache_data.clear()


def run_circuit(runner_name, shots):
    """Run the Shor circuit in a SEPARATE process and return (bitstrings, error).

    Streamlit runs every rerun in a new thread, and building Qiskit circuits
    repeatedly in fresh threads can crash the whole app. A subprocess keeps
    the dashboard alive whatever the simulator does.
    """
    code = ("import importlib.util, json, sys\n"
            "spec = importlib.util.spec_from_file_location('shors_demo', 'notebook/shors_demo.py')\n"
            "mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)\n"
            "print('RESULT=' + json.dumps(getattr(mod, sys.argv[1])(int(sys.argv[2]))))\n")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable, "-c", code, runner_name, str(int(shots))], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=300, env=env)
    except subprocess.TimeoutExpired:
        return None, "Timed out after 300 s. Try fewer shots."
    for line in reversed((p.stdout or "").splitlines()):
        if line.startswith("RESULT="):
            return json.loads(line[len("RESULT="):]), None
    return None, ((p.stderr or "") + (p.stdout or "")).strip()[-1500:] or f"exit code {p.returncode}"


def page_demo():
    """Run Shor's algorithm on the Aer simulator and explain every step."""
    try:
        demo = load_module("shors_demo", "notebook/shors_demo.py")
        import qiskit
        import qiskit_aer
    except ImportError as exc:
        st.error(f"Qiskit is not installed ({exc}). Run:  pip install qiskit qiskit-aer")
        return
    env = f"Qiskit {qiskit.__version__}, qiskit-aer {qiskit_aer.__version__} (Aer simulator)"
    cases = _demo_cases()
    c = st.columns([1, 3, 1])
    n = c[0].radio("Number to factor (N)", list(cases), horizontal=True)
    shots = c[1].slider("Shots (attempts)", 128, 4096, 1024, step=128)
    a, n_count, n_work, expected, runner_name = cases[n]
    r_true, seq = demo.classical_period(a, n)
    st.markdown(f"**Step 1 - pick a coprime a:** N = {n}, a = {a}, gcd = {math.gcd(a, n)}  \n"
                f"**Step 2 - the secret is the period r** of a^x mod N: "
                f"`{', '.join(map(str, seq))}` repeats every **r = {r_true}**  \n"
                f"**Step 3 - circuit:** {n_count} counting + {n_work} work = **{n_count + n_work} qubits**")
    if st.button(f"▶️ Run Shor's algorithm for N = {n}", type="primary"):
        with st.spinner("Running on the Aer simulator..."):
            t0 = time.time()
            attempts, err = run_circuit(runner_name, shots)
            took = time.time() - t0
        if err:
            st.error("The simulator run failed:\n\n" + err)
            return
        tally = {}
        for b in attempts:
            tally[b] = tally.get(b, 0) + 1
        rows = []
        for b, cnt in sorted(tally.items(), key=lambda kv: -kv[1]):
            phase = int(b, 2) / 2 ** n_count
            r_guess = Fraction(phase).limit_denominator(n).denominator
            fac = demo.factors_from_bitstring(b, a, n, n_count)
            rows.append({"bitstring": b, "count": cnt, "phase": round(phase, 3), "r guess": r_guess,
                         "factors": "x".join(map(str, fac)) if fac else "none", "found": fac == expected})
        st.session_state["demo_run"] = {"n": n, "shots": shots, "rows": rows, "took": took,
                                        "successes": sum(r["count"] for r in rows if r["found"]), "env": env}
    run = st.session_state.get("demo_run")
    if not run or run["n"] != n:
        st.info("Press the button to run the circuit. Shor's algorithm is probabilistic, so every run differs.")
        return
    rows, ok, total = run["rows"], run["successes"], run["shots"]
    kpi_row([("Shots", total, "#00B0FF"), ("Shots that found the factors", ok, "#00E676"),
             ("Success rate", f"{ok / total:.0%}", "#FFAB40"), ("Time (s)", f"{run['took']:.1f}", "#B388FF")])
    d = pd.DataFrame(rows).head(16)
    d["result"] = d["found"].map({True: "found factors", False: "no factors"})
    fig = px.bar(d, x="bitstring", y="count", color="result", title="Measured outcomes (top 16)",
                 color_discrete_map={"found factors": "#00E676", "no factors": "#78909C"})
    st.plotly_chart(style(fig, 330), key="demo_hist")
    st.dataframe(d[["bitstring", "count", "phase", "r guess", "factors"]], hide_index=True)
    win = next((r for r in rows if r["found"]), None)
    if win:
        r = win["r guess"]
        x = pow(a, r // 2, n)
        st.markdown(f"**Step 6 - factors:** measured `{win['bitstring']}` → phase {win['phase']} → r = {r} → "
                    f"x = {a}^({r}/2) mod {n} = {x} → gcd({x - 1}, {n}) = {math.gcd(x - 1, n)}, "
                    f"gcd({x + 1}, {n}) = {math.gcd(x + 1, n)}  →  **{n} = {expected[0]} × {expected[1]}** ✅")
        st.success(f"{n} = {expected[0]} x {expected[1]} (check: {expected[0] * expected[1]})")
    else:
        st.warning("No successful outcome this time. Run again, it is random.")
    st.caption("Toy sizes on a simulator. This shows the algorithm works. It does not show RSA-1024 or "
               "RSA-2048 can be broken today.")
    if st.button("💾 Save this run to data/demo_results.json (replaces an earlier N = %d run)" % n):
        save_demo(n, total, ok, expected, run["env"])
        st.success("Saved. Rebuild the final dashboard so its Demo section shows it.")


# ================================================================ MIGRATION
def _ms(seconds):
    """Seconds as a readable millisecond string."""
    return f"{seconds * 1000:,.1f} ms"


def page_migration():
    """RSA versus ML-KEM-768, run for real, plus the attack that motivates the move."""
    try:
        mig = load_module("migration_demo", "notebook/migration_demo.py")
    except (OSError, ImportError) as exc:
        st.error(f"notebook/migration_demo.py could not be loaded: {exc}")
        return
    missing = []
    if mig.ML_KEM_768 is None:
        missing.append("kyber-py")
    if mig.AESGCM is None:
        missing.append("cryptography")
    if missing:
        st.warning("Missing packages: " + ", ".join(missing) + ".  Run:  pip install " + " ".join(missing))
    st.markdown("The advisor recommends **ML-KEM-768**. This page runs it next to RSA with real code, "
                "so the recommendation is demonstrated and not only written down.")
    c = st.columns([3, 2])
    message = c[0].text_input("Message (short ASCII)", "PQC!", max_chars=7)
    bits = c[1].slider("Textbook RSA key size (bits)", 40, 72, 64, step=8)
    if not message:
        st.info("Type a short message first.")
        return
    if st.button("▶️ Run the comparison", type="primary"):
        with st.spinner("Generating keys, encrypting, attacking..."):
            st.session_state["mig"] = mig.compare(message.encode(), textbook_bits=bits)
    res = st.session_state.get("mig")
    if not res:
        st.info("Press the button to run all three schemes.")
        return

    rows = []
    for r in res.values():
        if "error" in r:
            st.warning(r["error"])
            continue
        rows.append({"Scheme": r["name"], "Public key (B)": r["public_key_bytes"],
                     "Ciphertext (B)": r["ciphertext_bytes"], "Keygen": _ms(r["keygen_s"]),
                     "Encrypt": _ms(r["encrypt_s"]), "Decrypt": _ms(r["decrypt_s"]),
                     "Same input, new ciphertext?": "yes" if r["randomised"] else "NO (deterministic)",
                     "Round trip": "✅" if r["roundtrip_ok"] else "❌", "Quantum status": r["quantum"]})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        d = pd.DataFrame(rows).melt(id_vars="Scheme", value_vars=["Public key (B)", "Ciphertext (B)"],
                                    var_name="what", value_name="bytes")
        st.plotly_chart(style(px.bar(d, x="Scheme", y="bytes", color="what", barmode="group",
                                     title="Size cost of moving to ML-KEM-768 (bytes)",
                                     color_discrete_sequence=["#00B0FF", "#FF4081"]), 320), key="mig_sizes")

    t, m = res.get("textbook", {}), res.get("mlkem", {})
    a, b = st.columns(2)
    if "factors" in t:
        a.markdown("#### 🔓 Attack on textbook RSA")
        a.markdown(f"The attacker has only the **public key** and the ciphertext. They factor n = "
                   f"{t['factors'][0]} × {t['factors'][1]} in **{_ms(t['attack_seconds'])}** and read the "
                   f"message: **{'yes' if t['attack_recovered'] else 'no'}**.")
        a.markdown('<div class="note bad">This demo key is tiny, so a <b>classical</b> attack is enough. '
                   "Against a large modulus the same job is done by Shor's algorithm.</div>", unsafe_allow_html=True)
    if "wrong_key_secret_differs" in m:
        b.markdown("#### 🔐 ML-KEM-768 + AES-256-GCM")
        b.markdown(f"Public key **{m['public_key_bytes']} B**, KEM ciphertext **{m['kem_ciphertext_bytes']} B**, "
                   f"shared secret **{m['shared_secret_bytes']} B**. AES-GCM then encrypts the message. "
                   f"A wrong private key gives a different secret: "
                   f"**{'yes' if m['wrong_key_secret_differs'] else 'NO'}**.")
        b.markdown('<div class="note good">No known quantum attack on ML-KEM (NIST FIPS 203). '
                   "The library used here is educational, so use liboqs or OpenSSL 3.5+ in production.</div>",
                   unsafe_allow_html=True)

    rsa_entries = [e for e in entries if e.get("primitive") == "RSA"]
    if rsa_entries and m.get("public_key_bytes"):
        st.markdown("#### 🧾 What this means for your CBOM")
        rows = [{"Entry": e["id"], "Project": e["project"],
                 "Current": f"RSA-{e['key_size_bits']}" if e.get("key_size_bits") else "RSA (size unknown)",
                 "Padding": e["padding_risk"].get("status"), "Replace with": e["recommended_pqc"]["algorithm"],
                 "New public key (B)": m["public_key_bytes"]} for e in rsa_entries]
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    st.caption("Sizes and timings come from this machine. ML-KEM is slower here because the library is pure Python.")


# ================================================================ PIPELINE
def page_advisor():
    """Layer by layer: which post-quantum technique goes where, with sizes and reasons."""
    recs = adv.load_records(ADVISOR)
    if recs is None:
        st.info("data/pqc_recommendations.json not found or incomplete. "
                "It holds the layer-by-layer advisor records.")
        return
    st.caption("ML-KEM, ML-DSA and AES-GCM are classical algorithms that resist quantum attacks. "
               "They run on ordinary computers and are not quantum circuits. The prototypes use "
               "kyber-py and dilithium-py, which are educational pure-Python libraries and "
               "not production crypto; liboqs-python is the production route.")
    st.dataframe(pd.DataFrame(adv.overview_rows(recs)), hide_index=True)

    chart = pd.DataFrame(adv.size_chart_rows(recs))
    if len(chart):
        st.plotly_chart(style(px.bar(chart, x="layer", y="bytes", text="bytes",
                                     title="Bytes each recommendation adds (keys, ciphertext, tags)",
                                     color_discrete_sequence=["#7C4DFF"])), key="adv_sizes")
        st.caption("A bigger hidden payload is easier to detect, so the steganalysis scripts "
                   "measure it. The hiding layer is not part of the quantum percentage.")

    for r in recs:
        color = adv.status_color(r)
        st.markdown(f'<div class="card">{badge(r["layer"], color)} <b>{esc(r["layer_name"])}</b><br>'
                    f'<span style="color:#aab2e0">Today:</span> {esc(r["today"])}<br>'
                    f'<span style="color:#aab2e0">Use:</span> <b>{esc(r["technique"])}</b> '
                    f'({esc(r["parameter_set"])}, {esc(r["standard"])})<br>'
                    f'<span style="color:#aab2e0">Status:</span> {esc(r["quantum_status"])}<br>'
                    f'<span style="color:#aab2e0">Sizes:</span> {esc(adv.sizes_text(r))}<br><br>'
                    f'<b>Why:</b> {esc(r["rationale"])}<br>'
                    f'<b>Where:</b> {esc(r["where_to_use"])}<br>'
                    f'<b>Trade-offs:</b> {esc(r["trade_offs"])}</div>', unsafe_allow_html=True)


def page_risk():
    """Risk score per project: percentage, band, quantum and classical parts, Z scenarios."""
    scores = rpd.load_scores(RISK)
    if scores is None:
        st.info("outputs/risk_scores.json not found. Run: python -m src.risk_run")
        return
    st.caption("A transparent weighted score from 0 to 100. It is not a probability that someone "
               "attacks the project. Weights " + str(scores.get("weights_version", "?")) +
               " are our choice and live in data/risk_weights.json. Only layer L1 (message "
               "encryption) is scored so far. The quantum part uses logical-qubit estimates "
               "(2n+3), not a simulator run.")
    text, agreed = rpd.assumptions_note(scores)
    st.markdown(f'<div class="note {"good" if agreed else ""}">{esc(text)}</div>', unsafe_allow_html=True)

    rows = rpd.summary_rows(scores)
    for r in rows:
        color = rpd.BAND_COLORS.get(r["band"], "#90A4AE")
        st.markdown(f"#### {esc(r['project'].title())} project")
        kpi_row([("Project score", f"{r['score']}%", color), ("Band", r["band"], color),
                 ("Quantum part", f"{r['quantum']}%", "#7C4DFF"),
                 ("Classical weakness", f"{r['classical']}%", "#00B0FF"),
                 ("Range over Z = 5 to 20", f"{r['z_min']} to {r['z_max']}%", "#FFAB40")])

    c1, c2 = st.columns(2)
    d = pd.DataFrame(rows).melt(id_vars="project", value_vars=["quantum", "classical", "score"],
                                var_name="part", value_name="percent")
    c1.plotly_chart(style(px.bar(d, x="project", y="percent", color="part", barmode="group",
                                 range_y=[0, 100], title="Quantum, classical and overall (central Z)")),
                    key="risk_bar")
    sc = pd.DataFrame(rpd.scenario_rows(scores))
    c2.plotly_chart(style(px.line(sc, x="z", y="overall", color="project", markers=True,
                                  range_y=[0, 100],
                                  title="Overall score by years until a large quantum computer (Z)")),
                    key="risk_z")

    for name, p in scores["projects"].items():
        st.markdown(f"#### {esc(name.title())}: factor breakdown (layer L1)")
        k = p["L1"]["key_in_use"]
        st.caption(f"Key in use: {k['modulus_bits']}-bit ({k['label']}). Construction: "
                   f"{p['L1']['construction']}. Exposure: {p['L1']['exposure']}.")
        fr = pd.DataFrame([{"Factor": a, "Value (0 to 100)": b if b is not None else "n/a", "Meaning": c}
                           for a, b, c in rpd.factor_rows(p)])
        st.dataframe(fr, hide_index=True)
        var = rpd.variant_rows(p)
        if var:
            st.caption("Other key sizes in the code, scored with the same engine (not the layer score):")
            st.dataframe(pd.DataFrame(var), hide_index=True)
        left = ", ".join(p.get("layers_not_scored_yet", []))
        if left:
            st.markdown(f'<div class="note">Layers not scored yet: {esc(left)}.</div>', unsafe_allow_html=True)


def page_before_after():
    """Image project before and after migration, scored by the same engine."""
    data = ba.load(BEFORE_AFTER)
    if data is None:
        st.info("outputs/before_after_image.json not found. Run: python src/before_after.py "
                "--out outputs/before_after_image.json")
        return
    st.caption("Image project, layer L1 (message encryption). Before: textbook RSA, no padding. "
               "After: ML-KEM-768 + AES-256-GCM. Both rows use the same engine and weights "
               + str(data.get("weights_version", "?")) + ". A weighted score, not a probability. "
               "Formulas and weights only; no simulator result. The prototype is educational "
               "code (kyber-py), not production crypto.")
    bits = st.radio("RSA modulus size in the code", ba.size_options(data), horizontal=True,
                    format_func=lambda b: f"{b} bits", key="ba_bits")
    row = ba.row_for(data, bits)
    s = ba.summary(row)
    kpi_row([("Before", f"{s['before']:.1f}%", rpd.BAND_COLORS.get(s["before_band"], "#90A4AE")),
             ("After", f"{s['after']:.1f}%", rpd.BAND_COLORS.get(s["after_band"], "#90A4AE")),
             ("Drop", f"{s['drop']:.1f} points", "#7C4DFF"),
             ("Band", f"{s['before_band']} to {s['after_band']}", "#00B0FF")])

    c1, c2 = st.columns(2)
    parts = pd.DataFrame(ba.parts_rows(row)).melt(id_vars="part", var_name="setup", value_name="percent")
    c1.plotly_chart(style(px.bar(parts, x="part", y="percent", color="setup", barmode="group",
                                 range_y=[0, 100], title="Quantum, classical and overall")),
                    key="ba_parts")
    sc = pd.DataFrame(ba.scenario_rows(row)).melt(id_vars="z", var_name="setup", value_name="overall")
    c2.plotly_chart(style(px.line(sc, x="z", y="overall", color="setup", markers=True,
                                  range_y=[0, 100],
                                  title="Overall score by years until a large quantum computer (Z)")),
                    key="ba_z")

    st.markdown("#### Factor breakdown")
    fr = pd.DataFrame(ba.factor_rows(row))
    for col in ("before", "after"):
        fr[col] = fr[col].map(lambda v: "n/a" if pd.isna(v) else f"{v:.1f}")
    st.dataframe(fr, hide_index=True)
    st.caption("n/a means the factor does not apply to that setup (for example, no RSA modulus "
               "after migration).")

    st.markdown("#### Why the after score is not zero")
    st.dataframe(pd.DataFrame(ba.floor_rows(data)), hide_index=True)
    st.markdown('<div class="note">The hiding layer (LSB embedding) is measured by steganalysis and '
                'is not part of this score. A larger post-quantum payload can be easier to detect; '
                'see the steganalysis results.</div>', unsafe_allow_html=True)

    st.markdown("#### Does the result depend on the weights?")
    st.dataframe(pd.DataFrame(ba.sensitivity_rows(row)), hide_index=True)
    st.caption(f"{data.get('n_draws', '?')} random weight draws per row (seed {data.get('seed', '?')}). "
               "A value of 1.0 means the after score was lower than the before score in every draw.")


def run_cmd(args, timeout):
    """Run a project command and return (exit code, combined output)."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    try:
        p = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, env=env)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"Timed out after {timeout} s."


def page_pipeline():
    """File freshness and one-click pipeline steps."""
    st.markdown("#### 📁 Pipeline files")
    rows = []
    for label, path in (("findings.json (scanner)", FINDINGS), ("cbom.json", CBOM), ("cbom.md", CBOM_MD),
                        ("risk_report.md", os.path.join(ROOT, "docs", "risk_report.md")),
                        ("final_dashboard.md", os.path.join(ROOT, "docs", "final_dashboard.md")),
                        ("demo_results.json", DEMO)):
        ok = os.path.isfile(path)
        rows.append({"File": label, "Exists": "✅" if ok else "❌ missing",
                     "Last modified": time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(path))) if ok else "-"})
    st.dataframe(pd.DataFrame(rows), hide_index=True)

    missing = [os.path.basename(t) for t in TARGETS if not os.path.isdir(t) or not os.listdir(t)]
    if missing:
        st.markdown(f'<div class="note bad">Target repos missing: {esc(", ".join(missing))}. '
                    'Run <code>git submodule update --init</code> before scanning.</div>', unsafe_allow_html=True)
    st.markdown("#### ▶️ Run a step")
    st.caption("These buttons run the real project scripts and overwrite their outputs. "
               "Refresh the page afterwards to see new numbers.")
    steps = {
        "🔍 Scan targets": (["src/run_all.py"], 300, bool(missing)),
        "🧾 Rebuild CBOM": (["src/cbom.py", "outputs/findings.json", "--facts", "data/manual_facts.json",
                             "--json", "docs/cbom.json", "--md", "docs/cbom.md", "--check"], 120, False),
        "🧪 Run tests": (["run_tests.py"], 300, False),
        "🚀 Full pipeline": (["run_pipeline.py"], 900, bool(missing)),
    }
    cols = st.columns(len(steps))
    for col, (label, (args, timeout, disabled)) in zip(cols, steps.items()):
        if col.button(label, disabled=disabled, key="run_" + label):
            with st.spinner(f"Running {' '.join(args)} ..."):
                code, out = run_cmd(args, timeout)
            st.cache_data.clear()
            (st.success if code == 0 else st.error)(f"{label}: exit code {code}")
            tail = "\n".join(out.strip().splitlines()[-40:])
            st.code(tail or "(no output)", language="text")


{"📊 Overview": page_overview, "🔎 Findings": page_findings, "🧾 CBOM and risk": page_cbom,
 "🎯 Risk score": page_risk,
 "🔁 Before and after": page_before_after,
 "🧭 PQC advisor": page_advisor,
 "📈 Qubit calculator": page_calculator, "🎬 Shor's demo (live)": page_demo,
 "🛡️ Migration demo": page_migration, "⚙️ Pipeline": page_pipeline}[page]()
