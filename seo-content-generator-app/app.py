"""
SEO Content Generator - Web App
--------------------------------
A no-code interface for the AI content generation pipeline.
Anyone can: enter a keyword, paste secondary keywords, upload their
Ahrefs/SEMrush exports, and get a content brief + full draft + SEO report -
no code, no terminal, no Colab required.

Run locally:
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key_here
    streamlit run app.py

Deploy for others to use (free, no server management):
    1. Push this folder to a GitHub repo.
    2. Go to share.streamlit.io, sign in with GitHub.
    3. Point it at this repo and app.py.
    4. Add ANTHROPIC_API_KEY under the app's Secrets settings.
    5. Share the resulting URL with your team.
"""

import os
import json
import streamlit as st
from anthropic import Anthropic

from core import generate_brief, generate_draft, check_seo, build_competitor_notes

st.set_page_config(page_title="SEO Content Generator", page_icon="📝", layout="wide")

st.title("📝 SEO Content Generator")
st.caption("Turn a keyword and your SERP research into a content brief, draft, and SEO report.")

# ---------------------------------------------------------------------------
# API key handling — supports Streamlit Secrets (for deployed apps) or a
# manual input (for local/first-time use), never hardcoded.
# ---------------------------------------------------------------------------

try:
    api_key = st.secrets.get("ANTHROPIC_API_KEY", None)
except Exception:
    api_key = None
if not api_key:
    api_key = os.environ.get("ANTHROPIC_API_KEY")

with st.sidebar:
    st.header("Settings")
    if not api_key:
        api_key = st.text_input("Anthropic API key", type="password", help="Get one at console.anthropic.com")
    else:
        st.success("API key loaded ✓")

    tone = st.selectbox(
        "Tone",
        ["friendly expert", "professional/formal", "conversational", "authoritative/technical"],
        index=0,
    )

# ---------------------------------------------------------------------------
# Main input form
# ---------------------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    keyword = st.text_input("Primary keyword", placeholder="e.g. houston car accident lawyer")
    secondary_raw = st.text_area(
        "Secondary keywords (comma-separated, optional)",
        placeholder="e.g. car accident attorney, personal injury lawyer houston",
        height=100,
    )

with col2:
    st.markdown("**Upload your research (optional but recommended)**")
    serp_file = st.file_uploader("SERP overview export", type=["csv"], key="serp")
    gap_file = st.file_uploader("Content gap export", type=["csv"], key="gap")
    kw_compare_file = st.file_uploader("Keyword explorer comparison export", type=["csv"], key="kwcompare")

st.divider()

brief_only = st.checkbox("Generate brief only (skip full draft)", value=False)
run_button = st.button("Generate", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------

if run_button:
    if not api_key:
        st.error("Please provide an Anthropic API key in the sidebar.")
        st.stop()
    if not keyword:
        st.error("Please enter a primary keyword.")
        st.stop()

    client = Anthropic(api_key=api_key)

    secondary_keywords = [k.strip() for k in secondary_raw.split(",") if k.strip()] if secondary_raw else []

    uploaded_files = {
        "SERP Overview": serp_file.read() if serp_file else None,
        "Content Gap": gap_file.read() if gap_file else None,
        "Keyword Explorer Comparison": kw_compare_file.read() if kw_compare_file else None,
    }

    with st.spinner("Processing uploaded files..."):
        competitor_notes = build_competitor_notes(uploaded_files)

    with st.spinner("Generating content brief..."):
        try:
            brief = generate_brief(client, keyword, competitor_notes, tone, secondary_keywords)
        except Exception as e:
            st.error(f"Failed to generate brief: {e}")
            st.stop()

    st.success("Brief generated")
    with st.expander("📋 Content brief", expanded=True):
        st.json(json.loads(json.dumps(brief.__dict__)))
        st.download_button(
            "Download brief (JSON)",
            data=json.dumps(brief.__dict__, indent=2),
            file_name=f"{keyword.replace(' ', '_')}_brief.json",
            mime="application/json",
        )

    if brief_only:
        st.stop()

    with st.spinner("Writing full draft (this can take 30-60 seconds)..."):
        try:
            draft = generate_draft(client, brief)
        except Exception as e:
            st.error(f"Failed to generate draft: {e}")
            st.stop()

    with st.spinner("Running SEO checks..."):
        seo_results = check_seo(draft, brief)

    st.success("Draft generated")

    tab1, tab2 = st.tabs(["📄 Draft", "✅ SEO Report"])

    with tab1:
        st.markdown(draft)
        st.download_button(
            "Download draft (Markdown)",
            data=draft,
            file_name=f"{keyword.replace(' ', '_')}_draft.md",
            mime="text/markdown",
        )

    with tab2:
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Word count", seo_results["word_count"], f"target: {seo_results['target_word_count']}")
        col_b.metric("Keyword density", f"{seo_results['keyword_density_pct']}%", "healthy: 0.5-2.5%")
        col_c.metric("Headers", f"{seo_results['h2_count']} H2 / {seo_results['h3_count']} H3")

        st.markdown("**Checklist**")
        checks = [
            ("Word count within 10% of target", seo_results["word_count_within_10pct"]),
            ("Keyword density in healthy range", seo_results["keyword_density_healthy"]),
            ("Has H1 title", seo_results["has_h1"]),
            ("Keyword appears in first 100 words", seo_results["keyword_in_first_100_words"]),
            ("Title under 60 characters", seo_results["title_length_ok"]),
            ("Meta description under 155 characters", seo_results["meta_description_length_ok"]),
        ]
        for label, passed in checks:
            st.write(("✅ " if passed else "⚠️ ") + label)

        st.download_button(
            "Download SEO report (JSON)",
            data=json.dumps(seo_results, indent=2),
            file_name=f"{keyword.replace(' ', '_')}_seo_report.json",
            mime="application/json",
        )