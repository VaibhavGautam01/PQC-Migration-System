"""
dashboard_app.py - Streamlit dashboard for the PQC Migration Advisor.

Reads outputs/findings.json (made by src/run_all.py) and shows the results
as a live, filterable dashboard. Nothing is hard-coded: re-run the scanner,
refresh the browser, and every number updates.

Run (from the repo root):
    pip install streamlit pandas plotly
    streamlit run src/dashboard_app.py
"""
import json
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "outputs", "findings.json")

# One colour per primitive, reused in every chart so the eye can follow it.
PRIM_COLORS = {"RSA": "#00B0FF", "ECC": "#B388FF", "DSA": "#FF4081",
               "DH": "#1DE9B6", "AES": "#FFAB40", "SHA": "#76FF03"}
CONF_COLORS = {"high": "#FF5252", "medium": "#FFB300", "low": "#90A4AE"}
SHOR = {"RSA", "ECC", "DSA", "DH"}        # fully broken by Shor's algorithm
GROVER = {"AES", "SHA"}                    # strength roughly halved by Grover's

# Edit these as the project moves forward (status: done / wip / planned).
STAGES = [
    ("🔍 Detection", "scanner, extra_patterns, key_size, run_all", "done"),
    ("🕵️ Edge cases", "padding checks, indirect usage", "wip"),
    ("⚛️ Quantum mapping", "primitive to Shor / Grover", "wip"),
    ("📊 Risk and qubit cost", "estimator, risk report, CBOM", "wip"),
    ("🎬 Shor's demo", "Qiskit, N = 15 and 21", "planned"),
]
WEEKS = [
    ("Week 1", "Detection engine v0.4.0 and findings.json v1", "done"),
    ("Week 2", "Validation, unit tests, Shor's demo, merge to main", "wip"),
    ("Week 3", "Risk scoring, qubit cost, CBOM, ML-KEM-768", "planned"),
    ("Week 4", "Final dashboard, report, rehearsal", "planned"),
]
STATUS_STYLE = {"done": ("✅ Done", "#00C853"), "wip": ("🔄 In progress", "#FFAB00"),
                "planned": ("⏳ Planned", "#78909C")}

st.set_page_config(page_title="PQC Migration Advisor", page_icon="🔐", layout="wide")

# ---------------------------------------------------------------- styling
# Forced dark theme so the neon colours look the same on every machine.
st.markdown("""
<style>
.stApp{background:radial-gradient(circle at 15% 0%,#1b1f4a 0%,#0b0e1f 55%,#080a16 100%);color:#eef1fb}
[data-testid="stSidebar"]{background:#0f1330;border-right:1px solid #262d5a}
h1,h2,h3,h4,p,label,span,div{color:#eef1fb}
.hero{background:linear-gradient(120deg,#2979ff,#7c4dff 45%,#ff4081 80%,#ffab40);
 border-radius:20px;padding:26px 30px;margin-bottom:18px;box-shadow:0 10px 40px #2979ff44}
.hero h1{margin:0;font-size:2rem;color:#fff}.hero p{margin:4px 0 0;color:#ffffffdd}
.chip{display:inline-block;background:#ffffff2e;border-radius:99px;padding:3px 12px;font-size:.78rem;margin:10px 6px 0 0;color:#fff}
.kpi{border-radius:16px;padding:16px 18px;background:#141939;border:1px solid #2a3170;border-top:4px solid var(--c)}
.kpi b{display:block;font-size:2rem;color:var(--c)}.kpi span{font-size:.8rem;color:#aab2e0}
.card{background:#141939;border:1px solid #2a3170;border-radius:16px;padding:14px 18px;margin:8px 0}
.row{display:flex;justify-content:space-between;align-items:center;gap:10px}
.badge{border-radius:99px;padding:3px 12px;font-size:.75rem;font-weight:600;color:#0b0e1f}
.note{border-left:4px solid #FFAB00;background:#1a1f45;border-radius:10px;padding:10px 14px;margin:8px 0;font-size:.9rem}
.stTabs [data-baseweb="tab"]{font-weight:600}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------- data
@st.cache_data
def load(path, mtime):
    """Load findings.json. mtime is part of the cache key so a new scan reloads."""
    with open(path, encoding="utf-8") as fh:
        raw = json.load(fh)
    df = pd.DataFrame(raw["findings"])
    for col in ("key_size", "modulus_bits"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["where"] = df["file"] + ":" + df["line"].astype(str)
    df["risk"] = df.apply(risk_label, axis=1)
    return raw, df


def risk_label(row):
    """Classify one finding. Weak RSA-style keys are breakable WITHOUT quantum."""
    if row["primitive"] in SHOR:
        m = row["modulus_bits"]
        if pd.notna(m) and m < 1024:
            return "Classically breakable"
        if pd.notna(m) and m < 2048:
            return "Weak key + Shor"
        return "Quantum: Shor"
    if row["primitive"] in GROVER:
        return "Quantum: Grover"
    return "Other"


RISK_COLORS = {"Classically breakable": "#FF1744", "Weak key + Shor": "#FF9100",
               "Quantum: Shor": "#7C4DFF", "Quantum: Grover": "#00E5FF", "Other": "#90A4AE"}

if not os.path.isfile(DATA_PATH):
    st.error("outputs/findings.json not found. Run: python src/run_all.py")
    st.stop()

raw, df = load(DATA_PATH, os.path.getmtime(DATA_PATH))


def style(fig, h=340):
    """Shared dark look for every plotly chart."""
    fig.update_layout(height=h, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font_color="#dfe4ff", margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=-0.15))
    fig.update_xaxes(gridcolor="#262d5a")
    fig.update_yaxes(gridcolor="#262d5a")
    return fig


# ---------------------------------------------------------------- sidebar
st.sidebar.markdown("## 🎛️ Filters")
projects = st.sidebar.multiselect("Project", sorted(df["project"].unique()),
                                  default=sorted(df["project"].unique()))
prims = st.sidebar.multiselect("Primitive", sorted(df["primitive"].unique()),
                               default=sorted(df["primitive"].unique()))
confs = st.sidebar.multiselect("Confidence", ["high", "medium", "low"],
                               default=["high", "medium", "low"])
only_sized = st.sidebar.checkbox("Only findings with a key size")
search = st.sidebar.text_input("🔎 Search file / pattern / code")
st.sidebar.caption("Source: outputs/findings.json · scanner v" + raw["scanner_version"])

f = df[df["project"].isin(projects) & df["primitive"].isin(prims) & df["confidence"].isin(confs)]
if only_sized:
    f = f[f["key_size"].notna()]
if search:
    hay = (f["file"] + " " + f["pattern_id"] + " " + f["snippet"]).str.lower()
    f = f[hay.str.contains(search.lower(), regex=False)]

# ------------------------------------------------------------------- hero
st.markdown(f"""
<div class="hero"><h1>🔐 PQC Migration Advisor</h1>
<p>Quantum-Vulnerability Testing Pipeline · Detect → Map → Estimate → Migrate</p>
<span class="chip">Scanner v{raw['scanner_version']}</span>
<span class="chip">{raw['total_findings']} findings</span>
<span class="chip">{len(raw['projects'])} projects</span>
<span class="chip">HCST Mathura · AKTU</span></div>""", unsafe_allow_html=True)

kpis = [("Findings shown", len(f), "#00B0FF"), ("Files with crypto", f["file"].nunique(), "#B388FF"),
        ("High confidence", int((f["confidence"] == "high").sum()), "#FF5252"),
        ("Classically breakable", int((f["risk"] == "Classically breakable").sum()), "#FF1744"),
        ("Quantum-vulnerable", int(f["primitive"].isin(SHOR).sum()), "#FFAB40"),
        ("With key size", int(f["key_size"].notna().sum()), "#1DE9B6")]
for col, (label, val, color) in zip(st.columns(len(kpis)), kpis):
    col.markdown(f'<div class="kpi" style="--c:{color}"><b>{val}</b><span>{label}</span></div>',
                 unsafe_allow_html=True)
st.write("")

tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🔑 Key sizes and risk", "📋 Findings", "🧭 Pipeline and progress"])

# ------------------------------------------------------------------ tab 1
with tab1:
    c1, c2 = st.columns(2)
    if f.empty:
        st.info("No findings match the current filters.")
    else:
        d = f["primitive"].value_counts().reset_index()
        d.columns = ["primitive", "count"]
        fig = px.pie(d, names="primitive", values="count", hole=0.55, color="primitive",
                     color_discrete_map=PRIM_COLORS, title="Findings by primitive")
        c1.plotly_chart(style(fig), key="pie")

        d = f.groupby(["project", "primitive"]).size().reset_index(name="count")
        fig = px.bar(d, x="project", y="count", color="primitive", color_discrete_map=PRIM_COLORS,
                     title="Findings by project", barmode="stack")
        c2.plotly_chart(style(fig), key="proj")

        c3, c4 = st.columns(2)
        d = f["pattern_id"].value_counts().head(10).reset_index()
        d.columns = ["pattern", "count"]
        fig = px.bar(d, x="count", y="pattern", orientation="h", title="Top 10 patterns",
                     color="count", color_continuous_scale=["#2979ff", "#7c4dff", "#ff4081"])
        fig.update_layout(coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
        c3.plotly_chart(style(fig), key="pat")

        d = f["confidence"].value_counts().reset_index()
        d.columns = ["confidence", "count"]
        fig = px.bar(d, x="confidence", y="count", color="confidence", color_discrete_map=CONF_COLORS,
                     title="Confidence levels")
        fig.update_layout(showlegend=False)
        c4.plotly_chart(style(fig), key="conf")

# ------------------------------------------------------------------ tab 2
with tab2:
    k = f[f["modulus_bits"].notna() | f["key_size"].notna()].copy()
    k["size"] = k["modulus_bits"].fillna(k["key_size"])
    if k.empty:
        st.info("No findings with a key size under the current filters.")
    else:
        k["label"] = k["project"].str[:14] + " · " + k["where"]
        fig = px.bar(k.sort_values("size"), x="size", y="label", orientation="h", color="risk",
                     color_discrete_map=RISK_COLORS, title="Key / modulus size in bits",
                     hover_data=["pattern_id", "size_basis"])
        fig.add_vline(x=2048, line_dash="dash", line_color="#00E676",
                      annotation_text="2048-bit minimum", annotation_font_color="#00E676")
        st.plotly_chart(style(fig, h=max(320, 34 * len(k))), key="keys")
        st.dataframe(k[["project", "where", "pattern_id", "key_size", "modulus_bits", "risk", "size_basis"]],
                     hide_index=True)
    st.markdown("""
<div class="note">⚠️ <b>Two kinds of risk.</b> <b>Classical:</b> a modulus under 1024 bits can be factored on an
ordinary computer today. <b>Quantum:</b> every RSA / ECC / DSA / DH key falls to Shor's algorithm, whatever its size.
AES and SHA lose about half their strength to Grover's algorithm.</div>
<div class="note">📝 <b>Manual notes.</b> Part1 real use is <code>generate_keypair(bits=128)</code>, a 256-bit modulus;
the 256 / 512 in <code>rsa_utils.py</code> is only a default. <code>r_channel_stego.py</code> uses n &lt; 256.
Steganography lets the user pick 1024 / 2048 / 3072 bits in the UI.</div>""", unsafe_allow_html=True)

# ------------------------------------------------------------------ tab 3
with tab3:
    st.caption(f"{len(f)} of {len(df)} findings")
    show = f[["project", "where", "primitive", "pattern_id", "confidence", "key_size",
              "modulus_bits", "risk", "snippet"]]
    st.dataframe(show, hide_index=True)
    st.download_button("⬇️ Download filtered findings (CSV)", show.to_csv(index=False),
                       file_name="findings_filtered.csv", mime="text/csv")

# ------------------------------------------------------------------ tab 4
with tab4:
    def status_rows(items):
        for name, desc, status in items:
            label, color = STATUS_STYLE[status]
            st.markdown(f'<div class="card"><div class="row"><div><b>{name}</b><br>'
                        f'<span style="color:#aab2e0;font-size:.85rem">{desc}</span></div>'
                        f'<span class="badge" style="background:{color}">{label}</span></div></div>',
                        unsafe_allow_html=True)

    a, b = st.columns(2)
    with a:
        st.subheader("Pipeline stages")
        status_rows(STAGES)
    with b:
        st.subheader("4-week sprint")
        status_rows(WEEKS)
        done = sum(1 for w in WEEKS if w[2] == "done")
        st.progress(done / len(WEEKS), text=f"Sprint progress: {done} of {len(WEEKS)} weeks complete")

st.caption("Built with ❤️ and a healthy fear of quantum computers · HCST Mathura · AKTU")
