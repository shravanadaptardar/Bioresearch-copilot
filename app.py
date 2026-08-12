import streamlit as st
from orchestrator import run_pipeline
from report_pdf import generate_pdf

st.set_page_config(
    page_title="BioResearch Copilot",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0d1117; color: #e6edf3; }
.hero { text-align: center; padding: 3rem 1rem 2rem; }
.hero h1 {
    font-size: 2.4rem; font-weight: 600;
    background: linear-gradient(135deg, #58a6ff 0%, #79c0ff 50%, #a5d6ff 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.5rem;
}
.hero p { color: #8b949e; font-size: 1.05rem; font-weight: 300; }
.section-card {
    background: #161b22; border: 1px solid #21262d;
    border-radius: 12px; padding: 1.4rem 1.6rem; margin-bottom: 1.2rem;
}
.section-title {
    font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #58a6ff; margin-bottom: 1rem;
}
.paper-item { border-left: 2px solid #21262d; padding: 0.6rem 0 0.6rem 1rem; margin-bottom: 0.8rem; }
.paper-title { font-weight: 500; color: #79c0ff; margin-bottom: 0.2rem; }
.paper-meta { font-size: 0.78rem; color: #6e7681; }
.dataset-chip {
    display: inline-block; background: #1f2d3d; border: 1px solid #1f6feb;
    color: #79c0ff; border-radius: 6px; padding: 0.3rem 0.7rem;
    font-size: 0.82rem; font-family: 'JetBrains Mono', monospace; margin: 0.2rem;
}
.tool-chip {
    display: inline-block; background: #1a2a1a; border: 1px solid #2ea043;
    color: #56d364; border-radius: 6px; padding: 0.3rem 0.7rem;
    font-size: 0.82rem; margin: 0.2rem;
}
.step-item { display: flex; gap: 1rem; margin-bottom: 0.9rem; align-items: flex-start; }
.step-num {
    background: #1f6feb; color: white; border-radius: 50%;
    width: 24px; height: 24px; min-width: 24px;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 600; margin-top: 1px;
}
.step-text { color: #c9d1d9; font-size: 0.9rem; line-height: 1.5; }
.step-tool { color: #6e7681; font-size: 0.8rem; margin-top: 0.15rem; }
.plan-badge {
    display: inline-block; background: #2d2a1a; border: 1px solid #bb8009;
    color: #e3b341; border-radius: 6px; padding: 0.2rem 0.6rem;
    font-size: 0.78rem; margin: 0.2rem;
}
.stTextArea textarea {
    background: #161b22 !important; border: 1px solid #30363d !important;
    color: #e6edf3 !important; border-radius: 10px !important; font-size: 0.95rem !important;
}
.stButton button {
    background: linear-gradient(135deg, #1f6feb, #388bfd) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    font-weight: 500 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <h1>🧬 BioResearch Copilot</h1>
    <p>Your junior computational biologist — literature · datasets · workflows · code</p>
</div>
""", unsafe_allow_html=True)

# ── Example queries ───────────────────────────────────────────────────────────
examples = [
    "I have macrophage markers: CD68, CD163, MRC1",
    "How do I integrate scRNA-seq data from 3 batches with Harmony?",
    "Find datasets for glioblastoma single-cell studies",
    "What's the difference between Leiden and Louvain clustering?",
]
st.markdown("<div style='text-align:center;margin-bottom:0.5rem;color:#6e7681;font-size:0.82rem'>Try an example</div>", unsafe_allow_html=True)
cols = st.columns(len(examples))
for i, ex in enumerate(examples):
    if cols[i].button(ex[:35] + "…" if len(ex) > 35 else ex, key=f"ex_{i}"):
        st.session_state["main_query"] = ex
        st.rerun()

# ── Input ─────────────────────────────────────────────────────────────────────
query = st.text_area("", placeholder="Describe your research question, genes of interest, or analysis goal…",
    height=100, key="main_query", label_visibility="collapsed")

col_run, col_clear, col_cache = st.columns([1, 2, 2])
run_btn   = col_run.button("Analyse →", type="primary")
clear_btn = col_clear.button("Clear")
if col_cache.button("🗑️ Clear cache"):
    from cache import clear_cache
    n = clear_cache()
    st.toast(f"Cleared {n} cached result(s)")
if clear_btn:
    st.session_state["main_query"] = ""
    st.rerun()

# ── Pipeline ──────────────────────────────────────────────────────────────────
if run_btn and query.strip():
    with st.spinner("Running agents — this takes ~15 seconds…"):
        result = run_pipeline(query.strip())   # fully sync now
    st.session_state["last_result"] = result
    st.session_state["last_query"]  = query.strip()
    st.session_state.pop("pdf_bytes", None)
    st.session_state.pop("pdf_for_query", None)
elif run_btn:
    st.warning("Please enter a research question first.")

# Render from session_state so the PDF download button's own rerun
# doesn't wipe the results off the page.
if "last_result" in st.session_state:
    result = st.session_state["last_result"]
    q      = st.session_state["last_query"]

    if result.get("_from_cache"):
        st.caption("⚡ Loaded from cache — no API tokens used")

    # ── Plan badges ───────────────────────────────────────────────────────────
    plan = result.get("plan", {})
    if plan:
        badges = ""
        if plan.get("domain"):
            badges += f'<span class="plan-badge">🏷 {plan["domain"]}</span>'
        for g in (plan.get("genes") or [])[:6]:
            badges += f'<span class="plan-badge">🧪 {g}</span>'
        if plan.get("disease_context"):
            badges += f'<span class="plan-badge">🔬 {plan["disease_context"]}</span>'
        st.markdown(f'<div style="margin-bottom:1.2rem">{badges}</div>', unsafe_allow_html=True)

    # ── Literature ────────────────────────────────────────────────────────────
    papers = result.get("literature", [])
    if papers:
        items = ""
        for p in papers:
            pmid_link = (f'· <a href="https://pubmed.ncbi.nlm.nih.gov/{p["pmid"]}/" '
                         f'target="_blank" style="color:#58a6ff">PubMed ↗</a>'
                         if p.get("pmid") else "")
            items += f"""
            <div class="paper-item">
                <div class="paper-title">{p.get('title','')}</div>
                <div style="color:#c9d1d9;font-size:0.87rem;margin:0.25rem 0">{p.get('summary','')}</div>
                <div class="paper-meta">{p.get('authors','')} · {p.get('journal','')} {p.get('year','')} {pmid_link}</div>
            </div>"""
        st.markdown(f'<div class="section-card"><div class="section-title">📄 Literature</div>{items}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-card"><div class="section-title">📄 Literature</div>'
                    '<div style="color:#6e7681;font-size:0.9rem">No papers found — PubMed may be slow. Try again.</div></div>',
                    unsafe_allow_html=True)

    # ── Datasets ──────────────────────────────────────────────────────────────
    datasets = result.get("datasets", [])
    if datasets:
        chips = "".join(
            f'<a href="https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={d["accession"]}" '
            f'target="_blank" style="text-decoration:none">'
            f'<span class="dataset-chip">{d["accession"]} · {d.get("samples","?")} samples'
            f'{(" · " + d["gdstype"]) if d.get("gdstype") else ""}</span></a>'
            for d in datasets
        )
        note = result.get("dataset_note","")
        st.markdown(f'<div class="section-card"><div class="section-title">🗄 Relevant Datasets (GEO)</div>{chips}'
                    f'{"<div style=\'color:#8b949e;font-size:0.85rem;margin-top:0.8rem\'>"+note+"</div>" if note else ""}</div>',
                    unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-card"><div class="section-title">🗄 Relevant Datasets (GEO)</div>'
                    '<div style="color:#6e7681;font-size:0.9rem">No datasets found — GEO may be slow. Try again.</div></div>',
                    unsafe_allow_html=True)

    # ── Workflow ──────────────────────────────────────────────────────────────
    workflow = result.get("workflow", [])
    if workflow:
        steps = "".join(f"""
        <div class="step-item">
            <div class="step-num">{i}</div>
            <div><div class="step-text">{s.get('step','')}</div>
            <div class="step-tool">🔧 {s.get('tool','')}</div></div>
        </div>""" for i, s in enumerate(workflow, 1))
        st.markdown(f'<div class="section-card"><div class="section-title">🔁 Suggested Workflow</div>{steps}</div>', unsafe_allow_html=True)

    # ── Tools + Markers ───────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    tools = result.get("tools", [])
    if tools:
        chips = "".join(f'<span class="tool-chip">{t}</span>' for t in tools)
        col1.markdown(f'<div class="section-card"><div class="section-title">🛠 Recommended Tools</div>{chips}</div>', unsafe_allow_html=True)

    marker_interp = result.get("marker_interpretation","")
    if marker_interp:
        col2.markdown(f'<div class="section-card"><div class="section-title">🔍 Marker Interpretation</div>'
                      f'<div style="color:#c9d1d9;font-size:0.9rem;line-height:1.6">{marker_interp}</div></div>', unsafe_allow_html=True)

    # ── Experimental notes ────────────────────────────────────────────────────
    exp_notes = result.get("experimental_notes","")
    if exp_notes:
        st.markdown(f'<div class="section-card"><div class="section-title">⚗️ Experimental Considerations</div>'
                    f'<div style="color:#c9d1d9;font-size:0.9rem;line-height:1.6">{exp_notes}</div></div>', unsafe_allow_html=True)

    # ── Code ──────────────────────────────────────────────────────────────────
    code = result.get("code_template","")
    if code:
        st.markdown('<div class="section-card"><div class="section-title">💻 Python / Scanpy Code Template</div></div>', unsafe_allow_html=True)
        st.code(code, language="python")

    # ── PDF Download ──────────────────────────────────────────────────────────
    st.markdown("---")
    if "pdf_bytes" not in st.session_state or st.session_state.get("pdf_for_query") != q:
        if st.button("⬇️ Generate PDF Report"):
            with st.spinner("Generating PDF…"):
                st.session_state["pdf_bytes"]     = generate_pdf(q, result)
                st.session_state["pdf_for_query"] = q
            st.rerun()
    else:
        st.download_button(
            label="📄 Download PDF Report",
            data=st.session_state["pdf_bytes"],
            file_name="bioresearch_report.pdf",
            mime="application/pdf",
        )
