"""
Version Analysis Page
Average rating, complaint %, high severity %, review volume, top issue per version.
"""

import streamlit as st
import pandas as pd

from utils.ui_components import (
    apply_custom_css, check_data_ready, render_page_header,
    render_kpi_row, render_section_header, render_sidebar_filters,
)
from utils.visualizations import version_comparison_chart, stacked_bar_chart, COLORS

st.set_page_config(page_title="Version Analysis", page_icon="📱", layout="wide")
apply_custom_css()

df = check_data_ready()
df = render_sidebar_filters(df)

render_page_header("📱 Version Analysis", "Evaluate release quality and identify problematic versions")

if "app_version" not in df.columns:
    st.warning("No app version data available.")
    st.stop()

# Filter out Unknown versions for cleaner analysis
version_df = df[df["app_version"] != "Unknown"].copy()

if len(version_df) == 0:
    st.warning("No version data available after filtering.")
    st.stop()

# ─── Aggregate Metrics ───────────────────────────────────────────────────────────

version_stats = version_df.groupby("app_version").agg(
    count=("app_version", "size"),
    avg_rating=("star_rating", "mean") if "star_rating" in version_df.columns else ("app_version", "size"),
).reset_index()

if "review_type" in version_df.columns:
    complaint_pct = version_df.groupby("app_version")["review_type"].apply(
        lambda x: round((x == "Complaint").mean() * 100, 1)
    ).reset_index(name="complaint_pct")
    version_stats = version_stats.merge(complaint_pct, on="app_version", how="left")

if "severity" in version_df.columns:
    high_sev_pct = version_df.groupby("app_version")["severity"].apply(
        lambda x: round((x == "High").mean() * 100, 1)
    ).reset_index(name="high_sev_pct")
    version_stats = version_stats.merge(high_sev_pct, on="app_version", how="left")

if "star_rating" in version_df.columns:
    version_stats["avg_rating"] = version_stats["avg_rating"].round(2)

# Sort by count descending to show most reviewed versions
version_stats = version_stats.sort_values("count", ascending=False)

# ─── KPIs ────────────────────────────────────────────────────────────────────────

total_versions = version_stats["app_version"].nunique()
worst_version = version_stats.loc[version_stats["avg_rating"].idxmin(), "app_version"] if "avg_rating" in version_stats.columns and len(version_stats) > 0 else "N/A"
most_reviewed = version_stats.loc[version_stats["count"].idxmax(), "app_version"] if len(version_stats) > 0 else "N/A"

metrics = [
    {"value": f"{total_versions}", "label": "Versions Analyzed"},
    {"value": worst_version, "label": "Lowest Rated Version"},
    {"value": most_reviewed, "label": "Most Reviewed Version"},
]

if "complaint_pct" in version_stats.columns:
    most_complained = version_stats.loc[version_stats["complaint_pct"].idxmax(), "app_version"] if len(version_stats) > 0 else "N/A"
    metrics.append({"value": most_complained, "label": "Most Complained Version"})

render_kpi_row(metrics)

st.markdown("---")

# ─── Charts ──────────────────────────────────────────────────────────────────────

# Top N filter
top_n = st.slider("Show top N versions (by review count)", 5, min(30, len(version_stats)), min(15, len(version_stats)))
top_versions = version_stats.head(top_n)

col1, col2 = st.columns(2)

with col1:
    render_section_header("Average Rating by Version")
    if "avg_rating" in top_versions.columns:
        fig = version_comparison_chart(top_versions, "app_version", "avg_rating", title="", color=COLORS["primary"])
        st.plotly_chart(fig, use_container_width=True)

with col2:
    render_section_header("Review Volume by Version")
    fig = version_comparison_chart(top_versions, "app_version", "count", title="", color=COLORS["info"], fmt="d")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    render_section_header("Complaint % by Version")
    if "complaint_pct" in top_versions.columns:
        fig = version_comparison_chart(top_versions, "app_version", "complaint_pct", title="", color=COLORS["danger"], fmt=".1f")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    render_section_header("High Severity % by Version")
    if "high_sev_pct" in top_versions.columns:
        fig = version_comparison_chart(top_versions, "app_version", "high_sev_pct", title="", color=COLORS["warning"], fmt=".1f")
        st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ─── Top Issue Per Version ───────────────────────────────────────────────────────

render_section_header("Top Issue Per Version")

if "topic" in version_df.columns:
    complaints = version_df[version_df["review_type"] == "Complaint"] if "review_type" in version_df.columns else version_df[version_df["star_rating"] <= 2]

    if len(complaints) > 0:
        top_issue = complaints.groupby("app_version")["topic"].agg(
            lambda x: x.value_counts().index[0] if len(x) > 0 else "N/A"
        ).reset_index(name="top_issue")

        top_issue = top_issue.merge(
            version_stats[["app_version", "count", "avg_rating"]],
            on="app_version", how="left",
        )
        top_issue = top_issue.sort_values("count", ascending=False).head(top_n)
        top_issue.columns = ["Version", "Top Issue", "Reviews", "Avg Rating"]
        st.dataframe(top_issue, use_container_width=True, hide_index=True)
    else:
        st.info("No complaint data available.")

# ─── Topic by Version Stacked ───────────────────────────────────────────────────

st.markdown("---")
render_section_header("Topic Breakdown by Version")

if "topic" in version_df.columns:
    fig = stacked_bar_chart(version_df, "app_version", "topic", title="", top_n=top_n)
    st.plotly_chart(fig, use_container_width=True)
