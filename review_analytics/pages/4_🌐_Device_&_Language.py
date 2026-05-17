"""
Device & Language Analysis Page
Rating and complaint analysis segmented by device and language.
"""

import streamlit as st
import pandas as pd

from utils.ui_components import (
    apply_custom_css, check_data_ready, render_page_header,
    render_section_header, render_sidebar_filters,
)
from utils.visualizations import (
    grouped_bar_chart, stacked_bar_chart, COLORS,
)

st.set_page_config(page_title="Device & Language", page_icon="🌐", layout="wide")
apply_custom_css()

df = check_data_ready()
df = render_sidebar_filters(df)

render_page_header("🌐 Device & Language Analysis", "Identify platform-specific issues and regional pain points")

has_device = "device" in df.columns
has_language = "reviewer_language" in df.columns

if not has_device and not has_language:
    st.warning("No device or language data available.")
    st.stop()

# ─── Device Analysis ────────────────────────────────────────────────────────────

if has_device:
    device_df = df[df["device"] != "Unknown"].copy()

    if len(device_df) > 0:
        st.markdown("## 📱 Device Analysis")

        top_n_device = st.slider("Top N devices", 5, 30, 15, key="device_n")

        # Aggregate
        device_stats = device_df.groupby("device").agg(
            count=("device", "size"),
            avg_rating=("star_rating", "mean") if "star_rating" in device_df.columns else ("device", "size"),
        ).reset_index()

        if "review_type" in device_df.columns:
            complaint_pct = device_df.groupby("device")["review_type"].apply(
                lambda x: round((x == "Complaint").mean() * 100, 1)
            ).reset_index(name="complaint_pct")
            device_stats = device_stats.merge(complaint_pct, on="device", how="left")

        if "star_rating" in device_df.columns:
            device_stats["avg_rating"] = device_stats["avg_rating"].round(2)

        # Filter to top N by count
        device_stats = device_stats.sort_values("count", ascending=False).head(top_n_device)

        col1, col2 = st.columns(2)

        with col1:
            render_section_header("Average Rating by Device")
            fig = grouped_bar_chart(device_stats, "device", "avg_rating", title="",
                                     color=COLORS["primary"], horizontal=True)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if "complaint_pct" in device_stats.columns:
                render_section_header("Complaint % by Device")
                fig = grouped_bar_chart(device_stats, "device", "complaint_pct", title="",
                                         color=COLORS["danger"], horizontal=True)
                st.plotly_chart(fig, use_container_width=True)

        # Topic breakdown by device
        if "topic" in device_df.columns:
            st.markdown("---")
            render_section_header("Topic Breakdown by Device")
            fig = stacked_bar_chart(device_df, "device", "topic", title="", top_n=top_n_device)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

# ─── Language Analysis ───────────────────────────────────────────────────────────

if has_language:
    lang_df = df[df["reviewer_language"] != "Unknown"].copy()

    if len(lang_df) > 0:
        st.markdown("## 🗣️ Language Analysis")

        # Aggregate
        lang_stats = lang_df.groupby("reviewer_language").agg(
            count=("reviewer_language", "size"),
            avg_rating=("star_rating", "mean") if "star_rating" in lang_df.columns else ("reviewer_language", "size"),
        ).reset_index()

        if "review_type" in lang_df.columns:
            complaint_pct = lang_df.groupby("reviewer_language")["review_type"].apply(
                lambda x: round((x == "Complaint").mean() * 100, 1)
            ).reset_index(name="complaint_pct")
            lang_stats = lang_stats.merge(complaint_pct, on="reviewer_language", how="left")

        if "star_rating" in lang_df.columns:
            lang_stats["avg_rating"] = lang_stats["avg_rating"].round(2)

        lang_stats = lang_stats.sort_values("count", ascending=False)

        col1, col2 = st.columns(2)

        with col1:
            render_section_header("Average Rating by Language")
            fig = grouped_bar_chart(lang_stats, "reviewer_language", "avg_rating", title="",
                                     color=COLORS["info"], horizontal=True)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if "complaint_pct" in lang_stats.columns:
                render_section_header("Complaint % by Language")
                fig = grouped_bar_chart(lang_stats, "reviewer_language", "complaint_pct", title="",
                                         color=COLORS["danger"], horizontal=True)
                st.plotly_chart(fig, use_container_width=True)

        # Topic breakdown by language
        if "topic" in lang_df.columns:
            st.markdown("---")
            render_section_header("Topic Breakdown by Language")
            fig = stacked_bar_chart(lang_df, "reviewer_language", "topic", title="")
            st.plotly_chart(fig, use_container_width=True)

        # Summary table
        st.markdown("---")
        render_section_header("Language Summary")
        display_stats = lang_stats.copy()
        display_stats.columns = ["Language", "Reviews", "Avg Rating"] + (
            ["Complaint %"] if "complaint_pct" in lang_stats.columns else []
        )
        st.dataframe(display_stats, use_container_width=True, hide_index=True)
