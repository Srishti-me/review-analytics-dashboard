"""
Executive Overview Page
KPIs, rating distribution, trends, complaint ratios, and silent dissatisfaction.
"""

import streamlit as st
import pandas as pd

from utils.ui_components import (
    apply_custom_css, check_data_ready, render_page_header,
    render_kpi_row, render_section_header, render_sidebar_filters,
)
from utils.visualizations import (
    rating_distribution_chart, trend_line_chart, donut_chart,
    SENTIMENT_COLORS, REVIEW_TYPE_COLORS,
)

st.set_page_config(page_title="Executive Overview", page_icon="📊", layout="wide")
apply_custom_css()

df = check_data_ready()
df = render_sidebar_filters(df)

render_page_header("📊 Executive Overview", "High-level health metrics and trends for your app reviews")

# ─── KPIs ────────────────────────────────────────────────────────────────────────

total = len(df)
avg_rating = round(df["star_rating"].mean(), 2) if "star_rating" in df.columns and total > 0 else 0

neg_count = len(df[df["sentiment"] == "Negative"]) if "sentiment" in df.columns else 0
neg_pct = round(neg_count / total * 100, 1) if total > 0 else 0

high_sev = len(df[df["severity"] == "High"]) if "severity" in df.columns else 0
high_sev_pct = round(high_sev / total * 100, 1) if total > 0 else 0

complaint_count = len(df[df["review_type"] == "Complaint"]) if "review_type" in df.columns else 0
praise_count = len(df[df["review_type"] == "Praise"]) if "review_type" in df.columns else 0

silent_dissatisfaction = 0
if "star_rating" in df.columns and "has_text_review" in df.columns:
    silent_dissatisfaction = len(df[(df["star_rating"] == 1) & (~df["has_text_review"])])

render_kpi_row([
    {"value": f"{total:,}", "label": "Total Reviews"},
    {"value": f"{avg_rating}★", "label": "Average Rating",
     "delta": "⚠️ Below 3.5" if avg_rating < 3.5 else "✓ Healthy" if avg_rating >= 4.0 else "",
     "delta_type": "negative" if avg_rating < 3.5 else "positive" if avg_rating >= 4.0 else "neutral"},
    {"value": f"{neg_pct}%", "label": "Negative Reviews",
     "delta_type": "negative" if neg_pct > 30 else "neutral"},
    {"value": f"{high_sev_pct}%", "label": "High Severity",
     "delta_type": "negative" if high_sev_pct > 20 else "neutral"},
    {"value": f"{silent_dissatisfaction}", "label": "Silent Dissatisfaction",
     "delta": "1★ without text", "delta_type": "negative" if silent_dissatisfaction > 0 else "neutral"},
])

st.markdown("---")

# ─── Row 2: Rating Distribution + Complaint vs Praise ───────────────────────────

col1, col2 = st.columns(2)

with col1:
    render_section_header("Rating Distribution")
    fig = rating_distribution_chart(df)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    render_section_header("Review Type Breakdown")
    if "review_type" in df.columns:
        fig = donut_chart(df, "review_type", colors=REVIEW_TYPE_COLORS)
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ─── Row 3: Review Trend Over Time ──────────────────────────────────────────────

render_section_header("Review Trend Over Time")

if "review_date_only" in df.columns:
    agg_option = st.radio("Aggregate by", ["Daily", "Weekly", "Monthly"], index=1, horizontal=True)
    agg_map = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}
    fig = trend_line_chart(df, agg=agg_map[agg_option], title="")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No date column available for trend analysis.")

st.markdown("---")

# ─── Row 4: Sentiment + Complaint/Praise Ratio ──────────────────────────────────

col1, col2 = st.columns(2)

with col1:
    render_section_header("Sentiment Distribution")
    if "sentiment" in df.columns:
        fig = donut_chart(df, "sentiment", colors=SENTIMENT_COLORS)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    render_section_header("Key Ratios")
    if total > 0:
        ratio = round(complaint_count / praise_count, 2) if praise_count > 0 else "∞"
        has_text_pct = round(df["has_text_review"].mean() * 100, 1) if "has_text_review" in df.columns else 0

        render_kpi_row([
            {"value": f"{ratio}", "label": "Complaint:Praise Ratio",
             "delta_type": "negative" if isinstance(ratio, (int, float)) and ratio > 1 else "positive"},
            {"value": f"{has_text_pct}%", "label": "Reviews With Text"},
        ])

        # Rating breakdown mini-table
        if "star_rating" in df.columns:
            st.markdown("")
            rating_dist = df["star_rating"].value_counts().sort_index()
            for star in range(5, 0, -1):
                count = rating_dist.get(star, 0)
                pct = round(count / total * 100, 1)
                bar_width = int(pct * 2)
                color = {"5": "#059669", "4": "#10B981", "3": "#F59E0B", "2": "#F97316", "1": "#EF4444"}[str(star)]
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
                    f'<span style="width:30px;text-align:right;font-weight:600;">{star}★</span>'
                    f'<div style="background:{color};height:18px;width:{bar_width}%;border-radius:4px;min-width:4px;"></div>'
                    f'<span style="color:#9CA3AF;font-size:0.85rem;">{count:,} ({pct}%)</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
