"""
App Review Analytics Platform
Main entry point — handles file upload, column mapping, and LLM processing.
"""

import streamlit as st
import pandas as pd

from utils.ui_components import apply_custom_css, render_page_header, render_kpi_row, render_download_button
from utils.data_processing import (
    auto_map_columns, validate_mapping, apply_column_mapping,
    preprocess_dataframe, get_processing_stats, CANONICAL_COLUMNS,
)
from utils.llm_pipeline import process_reviews_with_llm, estimate_cost, DEFAULT_MODEL

# ─── Page Config ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Review Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_custom_css()

# ─── Session State Init ─────────────────────────────────────────────────────────

for key in ["raw_df", "processed_df", "enriched_df", "column_mapping", "llm_cache", "upload_key"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "llm_cache" else {}
if "upload_key" not in st.session_state or st.session_state["upload_key"] is None:
    st.session_state["upload_key"] = 0

# ─── Header ──────────────────────────────────────────────────────────────────────

render_page_header(
    "📊 App Review Analytics",
    "Upload your app reviews to get AI-powered insights, trend analysis, and actionable product intelligence.",
)

# ─── Check if data already loaded ────────────────────────────────────────────────

if st.session_state["enriched_df"] is not None:
    st.success(f"✅ **Dataset loaded** — {len(st.session_state['enriched_df']):,} reviews ready for analysis. Use the sidebar pages to explore.")
    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    with col1:
        render_download_button(
            st.session_state["enriched_df"],
            filename="enriched_reviews.csv",
            label="📥 Download Enriched Dataset",
        )
    with col2:
        if st.button("🔄 Upload New File", type="secondary"):
            for key in ["raw_df", "processed_df", "enriched_df", "column_mapping"]:
                st.session_state[key] = None
            st.session_state["upload_key"] += 1
            st.rerun()

    # Show quick stats
    stats = get_processing_stats(st.session_state["enriched_df"])
    st.markdown("### Quick Stats")
    render_kpi_row([
        {"value": f"{stats['total_reviews']:,}", "label": "Total Reviews"},
        {"value": f"{stats['avg_rating']}★", "label": "Avg Rating"},
        {"value": f"{stats['meaningful_count']:,}", "label": "LLM-Analyzed"},
        {"value": f"{stats.get('unique_versions', 'N/A')}", "label": "Versions"},
        {"value": f"{stats.get('unique_devices', 'N/A')}", "label": "Devices"},
    ])
    st.stop()


# ─── File Upload ─────────────────────────────────────────────────────────────────

st.markdown("### 📁 Upload Dataset")
st.caption("Upload a CSV or Excel file containing app reviews. The file should have at least a star rating column.")

uploaded_file = st.file_uploader(
    "Choose a file",
    type=["csv", "xlsx", "xls"],
    key=f"file_uploader_{st.session_state.get('upload_key', 0)}",
    help="Supported formats: CSV, Excel (.xlsx, .xls)",
)

if uploaded_file is None:
    # Show placeholder
    st.markdown("""
    <div style="
        border: 2px dashed rgba(108,99,255,0.3);
        border-radius: 16px;
        padding: 3rem 2rem;
        text-align: center;
        margin: 2rem 0;
    ">
        <div style="font-size: 3rem; margin-bottom: 0.75rem;">📄</div>
        <div style="font-size: 1.1rem; color: #9CA3AF; margin-bottom: 0.5rem;">
            Drag & drop your review file here
        </div>
        <div style="font-size: 0.85rem; color: #6B7280;">
            Expected columns: Review Text, Star Rating, Review Date, App Version, Device, Language
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ─── Read File ───────────────────────────────────────────────────────────────────

try:
    if uploaded_file.name.endswith(".csv"):
        raw_df = pd.read_csv(uploaded_file)
    else:
        raw_df = pd.read_excel(uploaded_file)
    st.session_state["raw_df"] = raw_df
    st.success(f"✅ Loaded **{len(raw_df):,}** rows with **{len(raw_df.columns)}** columns")
except Exception as e:
    st.error(f"❌ Error reading file: {e}")
    st.stop()

# ─── Column Mapping ──────────────────────────────────────────────────────────────

st.markdown("### 🔗 Column Mapping")

auto_mapping = auto_map_columns(list(raw_df.columns))
is_valid, missing = validate_mapping(auto_mapping)

# Show auto-detected mapping
mapped_count = sum(1 for v in auto_mapping.values() if v is not None)
total_canonical = len(auto_mapping)
st.info(f"Auto-detected **{mapped_count}/{total_canonical}** columns. Adjust if needed:")

# Let user adjust mapping
with st.expander("📋 Column Mapping", expanded=True):
    confirmed_mapping = {}
    available_cols = ["— Not Available —"] + list(raw_df.columns)

    col1, col2 = st.columns(2)
    items = list(CANONICAL_COLUMNS.keys())

    for i, canonical in enumerate(items):
        target_col = col1 if i < len(items) // 2 + 1 else col2
        with target_col:
            auto_val = auto_mapping.get(canonical)
            default_idx = available_cols.index(auto_val) if auto_val in available_cols else 0
            selected = st.selectbox(
                f"{canonical.replace('_', ' ').title()}",
                available_cols,
                index=default_idx,
                key=f"map_{canonical}",
            )
            confirmed_mapping[canonical] = selected if selected != "— Not Available —" else None

# Validate
is_valid, missing = validate_mapping(confirmed_mapping)
if not is_valid:
    st.error(f"❌ Required columns missing: **{', '.join(missing)}**. Please map them above.")
    st.stop()

st.session_state["column_mapping"] = confirmed_mapping

# ─── Process Data ────────────────────────────────────────────────────────────────

if st.button("⚙️ Process & Analyze", type="primary", use_container_width=True):
    with st.spinner("Processing data..."):
        mapped_df = apply_column_mapping(raw_df.copy(), confirmed_mapping)
        processed_df = preprocess_dataframe(mapped_df)
        st.session_state["processed_df"] = processed_df
    st.rerun()

# ─── Show Processing Stats & LLM Section (persisted via session state) ───────────

if st.session_state.get("processed_df") is None:
    st.stop()

processed_df = st.session_state["processed_df"]
stats = get_processing_stats(processed_df)

st.markdown("### 📊 Data Overview")
render_kpi_row([
    {"value": f"{stats['total_reviews']:,}", "label": "Total Reviews"},
    {"value": f"{stats['avg_rating']}★", "label": "Avg Rating"},
    {"value": f"{stats['meaningful_count']:,}", "label": "Meaningful Reviews"},
    {"value": f"{stats['short_count'] + stats['noise_count']:,}", "label": "Short / Noise"},
    {"value": f"{stats['empty_count']:,}", "label": "No Text"},
])

st.markdown("---")

# ── LLM Enrichment ──
st.markdown("### 🤖 LLM Enrichment")
meaningful_count = stats["meaningful_count"]
cost_info = estimate_cost(meaningful_count)

st.markdown(f"""
**{meaningful_count}** meaningful reviews will be analyzed by the AI model.

- **Model:** `{cost_info['model']}`
- **Batches:** {cost_info['total_batches']}
- **Estimated Cost:** ${cost_info['estimated_cost_usd']:.4f}
""")

# API Key
api_key = st.text_input(
    "🔑 API Key",
    type="password",
    value="",
    placeholder="Enter your API key...",
    help="Your API key is not stored. Enter it each session.",
)

# Model Selection
model = st.selectbox(
    "Model",
    [
        "llama-3.1-8b-instant",
        "llama-3.3-70b-versatile",
        # "gpt-4o-mini",
        # "gpt-4o",
        # "gpt-3.5-turbo",
        # "grok-3-beta",
        # "grok-3-mini-beta",
    ],
    index=0,
)

col_llm, col_skip = st.columns(2)

with col_llm:
    run_llm = st.button(
        "🚀 Run AI Analysis",
        type="primary",
        use_container_width=True
    )

with col_skip:
    skip_llm = st.button(
        "⏭️ Skip AI (Use Defaults)",
        type="secondary",
        use_container_width=True
    )

# ── Run LLM ──
if run_llm:

    if not api_key:
        st.error("Please enter your API key.")

    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def update_progress(pct, msg):
            progress_bar.progress(pct)
            status_text.text(msg)

        with st.spinner("Analyzing reviews with AI..."):

            enriched_df = process_reviews_with_llm(
                processed_df,
                api_key,
                model=model,
                progress_callback=update_progress,
            )

            st.session_state["enriched_df"] = enriched_df

        progress_bar.progress(1.0)
        status_text.text("✅ Analysis complete!")

        st.balloons()
        st.rerun()

# ── Skip LLM ──
if skip_llm:

    with st.spinner("Applying default classifications..."):

        from utils.llm_pipeline import (
            LLM_COLUMNS,
            _get_default_llm_fields
        )

        skip_df = processed_df.copy()

        for col in LLM_COLUMNS:
            skip_df[col] = None

        for idx in skip_df.index:

            rating = (
                skip_df.loc[idx, "star_rating"]
                if "star_rating" in skip_df.columns
                else 3
            )

            defaults = _get_default_llm_fields(rating)

            for col, val in defaults.items():
                skip_df.at[idx, col] = val

        st.session_state["enriched_df"] = skip_df

    st.rerun()

