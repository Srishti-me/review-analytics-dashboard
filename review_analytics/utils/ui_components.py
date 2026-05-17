"""
UI Components Module
Reusable Streamlit UI elements: KPI cards, sidebar filters, CSS, download buttons.
"""

import streamlit as st
import pandas as pd
from io import BytesIO


# ─── Custom CSS ──────────────────────────────────────────────────────────────────

def apply_custom_css():
    st.markdown("""
    <style>
    /* ── Import Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Global ── */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* ── KPI Cards ── */
    .kpi-card {
        background: linear-gradient(135deg, rgba(108,99,255,0.12) 0%, rgba(167,139,250,0.08) 100%);
        border: 1px solid rgba(108,99,255,0.2);
        border-radius: 16px;
        padding: 1.25rem 1.5rem;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(108,99,255,0.15);
    }
    .kpi-value {
        font-size: 2rem;
        font-weight: 700;
        color: #FAFAFA;
        margin: 0;
        line-height: 1.2;
    }
    .kpi-label {
        font-size: 0.8rem;
        font-weight: 500;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.35rem;
    }
    .kpi-delta {
        font-size: 0.85rem;
        font-weight: 600;
        margin-top: 0.25rem;
    }
    .kpi-delta.positive { color: #10B981; }
    .kpi-delta.negative { color: #EF4444; }
    .kpi-delta.neutral { color: #6B7280; }

    /* ── Severity Badges ── */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .badge-high { background: rgba(239,68,68,0.2); color: #EF4444; }
    .badge-medium { background: rgba(245,158,11,0.2); color: #F59E0B; }
    .badge-low { background: rgba(16,185,129,0.2); color: #10B981; }
    .badge-positive { background: rgba(16,185,129,0.2); color: #10B981; }
    .badge-negative { background: rgba(239,68,68,0.2); color: #EF4444; }
    .badge-neutral { background: rgba(107,114,128,0.2); color: #9CA3AF; }

    /* ── Section Headers ── */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #A78BFA;
        margin: 1.5rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(167,139,250,0.2);
    }

    /* ── Review Card ── */
    .review-card {
        background: rgba(26,29,41,0.6);
        border: 1px solid rgba(108,99,255,0.15);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 0.75rem;
    }
    .review-text {
        font-size: 0.9rem;
        color: #D1D5DB;
        line-height: 1.6;
        margin-bottom: 0.5rem;
    }
    .review-meta {
        display: flex;
        gap: 0.75rem;
        flex-wrap: wrap;
        align-items: center;
    }

    /* ── Page Title ── */
    .page-title {
        font-size: 1.75rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6C63FF 0%, #A78BFA 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.25rem;
    }
    .page-subtitle {
        font-size: 0.9rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }

    /* ── Streamlit Overrides ── */
    .stMetric { background: transparent; }
    div[data-testid="stMetricValue"] { font-size: 1.5rem; }

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0E1117 0%, #141722 100%);
    }
    section[data-testid="stSidebar"] .stSelectbox label,
    section[data-testid="stSidebar"] .stMultiSelect label {
        font-size: 0.8rem;
        font-weight: 500;
        color: #9CA3AF;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] { gap: 0.5rem; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 0.5rem 1.25rem;
        font-weight: 500;
    }

    /* ── Divider ── */
    hr { border-color: rgba(108,99,255,0.15) !important; }
    </style>
    """, unsafe_allow_html=True)


# ─── KPI Cards ───────────────────────────────────────────────────────────────────

def render_kpi_card(value, label, delta=None, delta_type="neutral"):
    delta_html = ""
    if delta is not None:
        delta_html = f'<div class="kpi-delta {delta_type}">{delta}</div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
        {delta_html}
    </div>
    """


def render_kpi_row(metrics: list[dict], columns=None):
    """Render a row of KPI cards. Each metric: {value, label, delta?, delta_type?}"""
    if columns is None:
        columns = st.columns(len(metrics))
    for col, m in zip(columns, metrics):
        with col:
            st.markdown(
                render_kpi_card(
                    m["value"], m["label"],
                    m.get("delta"), m.get("delta_type", "neutral"),
                ),
                unsafe_allow_html=True,
            )


# ─── Page Header ─────────────────────────────────────────────────────────────────

def render_page_header(title, subtitle=""):
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="page-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def render_section_header(title):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


# ─── Severity Badge ─────────────────────────────────────────────────────────────

def severity_badge(severity):
    cls = severity.lower() if severity else "low"
    return f'<span class="badge badge-{cls}">{severity}</span>'


def sentiment_badge(sentiment):
    cls = sentiment.lower() if sentiment else "neutral"
    return f'<span class="badge badge-{cls}">{sentiment}</span>'


# ─── Sidebar Filters ────────────────────────────────────────────────────────────

def render_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    """Render sidebar filters and return filtered DataFrame."""
    with st.sidebar:
        st.markdown("### 🎛️ Filters")
        filtered = df.copy()

        # Date range
        if "review_date" in df.columns:
            date_col = df["review_date"].dropna()
            if len(date_col) > 0:
                min_date = date_col.min().date()
                max_date = date_col.max().date()
                date_range = st.date_input(
                    "Date Range", value=(min_date, max_date),
                    min_value=min_date, max_value=max_date,
                )
                if len(date_range) == 2:
                    start, end = date_range
                    filtered = filtered[
                        (filtered["review_date"].dt.date >= start) &
                        (filtered["review_date"].dt.date <= end)
                    ]

        # Star Rating
        if "star_rating" in df.columns:
            ratings = sorted(df["star_rating"].dropna().unique(), key=str)
            selected_ratings = st.multiselect("Star Rating", ratings, default=ratings)
            if selected_ratings:
                filtered = filtered[filtered["star_rating"].isin(selected_ratings)]

        # App Version
        if "app_version" in df.columns:
            versions = sorted(df["app_version"].dropna().unique(), key=str)
            selected_versions = st.multiselect("App Version", versions)
            if selected_versions:
                filtered = filtered[filtered["app_version"].isin(selected_versions)]

        # Device
        if "device" in df.columns:
            devices = sorted(df["device"].dropna().unique(), key=str)
            selected_devices = st.multiselect("Device", devices)
            if selected_devices:
                filtered = filtered[filtered["device"].isin(selected_devices)]

        # Language
        if "reviewer_language" in df.columns:
            langs = sorted(df["reviewer_language"].dropna().unique(), key=str)
            selected_langs = st.multiselect("Language", langs)
            if selected_langs:
                filtered = filtered[filtered["reviewer_language"].isin(selected_langs)]

        # Topic (LLM-enriched)
        if "topic" in df.columns:
            topics = sorted(df["topic"].dropna().unique(), key=str)
            selected_topics = st.multiselect("Topic", topics)
            if selected_topics:
                filtered = filtered[filtered["topic"].isin(selected_topics)]

        # Severity
        if "severity" in df.columns:
            sevs = ["High", "Medium", "Low"]
            selected_sevs = st.multiselect("Severity", sevs)
            if selected_sevs:
                filtered = filtered[filtered["severity"].isin(selected_sevs)]

        # Review Type
        if "review_type" in df.columns:
            types = sorted(df["review_type"].dropna().unique(), key=str)
            selected_types = st.multiselect("Review Type", types)
            if selected_types:
                filtered = filtered[filtered["review_type"].isin(selected_types)]

        # Sentiment
        if "sentiment" in df.columns:
            sents = ["Positive", "Neutral", "Negative"]
            selected_sents = st.multiselect("Sentiment", sents)
            if selected_sents:
                filtered = filtered[filtered["sentiment"].isin(selected_sents)]

        st.markdown("---")
        st.caption(f"Showing **{len(filtered):,}** of **{len(df):,}** reviews")

    return filtered


# ─── Download Button ─────────────────────────────────────────────────────────────

def render_download_button(df: pd.DataFrame, filename="reviews.csv", label="📥 Download CSV"):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label=label, data=csv, file_name=filename, mime="text/csv")


# ─── Data Check ──────────────────────────────────────────────────────────────────

def check_data_ready():
    """Check if enriched data is available in session state. Show message if not."""
    if "enriched_df" not in st.session_state or st.session_state["enriched_df"] is None:
        st.warning("⚠️ No data loaded. Please upload a file on the **Home** page first.")
        st.stop()
    return st.session_state["enriched_df"]
