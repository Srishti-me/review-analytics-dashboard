"""
Topic Analysis Page
Top complaint topics, topic trends, topic × sentiment/severity matrices, subtopics.
"""

import streamlit as st
import pandas as pd

from utils.ui_components import (
    apply_custom_css, check_data_ready, render_page_header,
    render_kpi_row, render_section_header, render_sidebar_filters,
)
from utils.visualizations import (
    horizontal_bar_chart, topic_trend_chart, heatmap_chart,
    donut_chart, COLORS, SEVERITY_COLORS, CHART_PALETTE,
)

st.set_page_config(page_title="Topic Analysis", page_icon="🏷️", layout="wide")
apply_custom_css()

df = check_data_ready()
df = render_sidebar_filters(df)

render_page_header("🏷️ Topic Analysis", "Understand what users are talking about and which issues dominate")

# ─── Checks ──────────────────────────────────────────────────────────────────────

if "topic" not in df.columns or df["topic"].isna().all():
    st.warning("Topic data not available. Please run LLM analysis first.")
    st.stop()

# Filter to meaningful (LLM-analyzed) reviews for topic analysis
topic_df = df[df["topic"].notna() & (df["topic"] != "N/A")].copy()

# ─── KPIs ────────────────────────────────────────────────────────────────────────

unique_topics = topic_df["topic"].nunique()
top_complaint_topic = "N/A"
most_severe_topic = "N/A"

complaints = topic_df[topic_df["review_type"] == "Complaint"]
if len(complaints) > 0:
    top_complaint_topic = complaints["topic"].value_counts().index[0]

high_sev = topic_df[topic_df["severity"] == "High"]
if len(high_sev) > 0:
    most_severe_topic = high_sev["topic"].value_counts().index[0]

render_kpi_row([
    {"value": f"{unique_topics}", "label": "Unique Topics"},
    {"value": top_complaint_topic, "label": "Top Complaint Topic"},
    {"value": most_severe_topic, "label": "Most Severe Topic"},
    {"value": f"{len(complaints):,}", "label": "Total Complaints"},
])

st.markdown("---")

# ─── Top Complaint Topics ───────────────────────────────────────────────────────

col1, col2 = st.columns(2)

with col1:
    render_section_header("Top Complaint Topics")
    if len(complaints) > 0:
        fig = horizontal_bar_chart(complaints, "topic", title="", top_n=10, color=COLORS["danger"])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No complaints found in the filtered data.")

with col2:
    render_section_header("Topic Distribution (All Reviews)")
    fig = donut_chart(topic_df, "topic", title="")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ─── Topic Trends Over Time ─────────────────────────────────────────────────────

render_section_header("Topic Trends Over Time")
if "review_date_only" in topic_df.columns:
    top_n = st.slider("Number of topics to show", 3, 10, 6)
    fig = topic_trend_chart(topic_df, top_n=top_n, title="")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No date column available for trend analysis.")

st.markdown("---")

# ─── Heatmaps ───────────────────────────────────────────────────────────────────

col1, col2 = st.columns(2)

with col1:
    render_section_header("Topic × Sentiment")
    if "sentiment" in topic_df.columns:
        fig = heatmap_chart(topic_df, "sentiment", "topic", title="")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    render_section_header("Topic × Severity")
    if "severity" in topic_df.columns:
        fig = heatmap_chart(topic_df, "severity", "topic", title="")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ─── Most Common Subtopics ──────────────────────────────────────────────────────

render_section_header("Most Common Subtopics")
if "subtopic" in topic_df.columns:
    subtopic_df = topic_df[topic_df["subtopic"].notna() & (topic_df["subtopic"] != "N/A")]
    if len(subtopic_df) > 0:
        fig = horizontal_bar_chart(subtopic_df, "subtopic", title="", top_n=15, color=COLORS["secondary"])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No subtopic data available.")

# ─── Topic Detail Table ─────────────────────────────────────────────────────────

st.markdown("---")
render_section_header("Topic Summary Table")

if len(topic_df) > 0:
    summary = topic_df.groupby("topic").agg(
        count=("topic", "size"),
        avg_rating=("star_rating", "mean") if "star_rating" in topic_df.columns else ("topic", "size"),
        high_severity=("severity", lambda x: (x == "High").sum()) if "severity" in topic_df.columns else ("topic", "size"),
        negative_pct=("sentiment", lambda x: round((x == "Negative").mean() * 100, 1)) if "sentiment" in topic_df.columns else ("topic", "size"),
    ).reset_index()

    if "star_rating" in topic_df.columns:
        summary["avg_rating"] = summary["avg_rating"].round(2)

    summary = summary.sort_values("count", ascending=False)
    summary.columns = ["Topic", "Count", "Avg Rating", "High Severity", "Negative %"]
    st.dataframe(summary, use_container_width=True, hide_index=True)
