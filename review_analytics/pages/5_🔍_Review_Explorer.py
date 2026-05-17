"""
Review Explorer Page
Searchable, filterable review table with detailed view and export.
"""

import streamlit as st
import pandas as pd

from utils.ui_components import (
    apply_custom_css, check_data_ready, render_page_header,
    render_section_header, render_sidebar_filters, render_download_button,
    severity_badge, sentiment_badge,
)

st.set_page_config(page_title="Review Explorer", page_icon="🔍", layout="wide")
apply_custom_css()

df = check_data_ready()
df = render_sidebar_filters(df)

render_page_header("🔍 Review Explorer", "Search, filter, and explore individual reviews in detail")

# ─── Search Bar ──────────────────────────────────────────────────────────────────

search_query = st.text_input(
    "🔎 Search reviews",
    placeholder="Type to search in review text, summary, or topic...",
    help="Search across review text, summary, and topic fields.",
)

if search_query:
    query_lower = search_query.lower()
    mask = pd.Series(False, index=df.index)
    for col in ["review_text", "cleaned_review_text", "summary", "topic", "subtopic"]:
        if col in df.columns:
            mask |= df[col].astype(str).str.lower().str.contains(query_lower, na=False)
    df = df[mask]

# ─── Quick Stats ─────────────────────────────────────────────────────────────────

total = len(df)
st.markdown(f"**{total:,}** reviews match your filters" + (f" and search for *\"{search_query}\"*" if search_query else ""))

if total == 0:
    st.info("No reviews match the current filters. Try adjusting your criteria.")
    st.stop()

st.markdown("---")

# ─── Download Filtered Reviews ───────────────────────────────────────────────────

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    render_download_button(df, "filtered_reviews.csv", "📥 Download Filtered Reviews")
with col2:
    view_mode = st.radio("View", ["Table", "Cards"], horizontal=True, label_visibility="collapsed")

# ─── Display Columns ────────────────────────────────────────────────────────────

display_cols = []
col_labels = {}

# Build display columns dynamically based on what's available
col_mapping = {
    "star_rating": "Rating",
    "review_text": "Review",
    "summary": "Summary",
    "topic": "Topic",
    "subtopic": "Subtopic",
    "severity": "Severity",
    "sentiment": "Sentiment",
    "review_type": "Type",
    "affected_area": "Area",
    "actionability": "Actionable",
    "app_version": "Version",
    "device": "Device",
    "reviewer_language": "Language",
    "review_date_only": "Date",
}

for col, label in col_mapping.items():
    if col in df.columns:
        display_cols.append(col)
        col_labels[col] = label

# ─── Table View ──────────────────────────────────────────────────────────────────

if view_mode == "Table":
    # Pagination
    page_size = st.selectbox("Rows per page", [25, 50, 100], index=0)
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total)

    st.caption(f"Showing {start_idx + 1}–{end_idx} of {total:,} reviews (Page {page}/{total_pages})")

    page_df = df.iloc[start_idx:end_idx][display_cols].copy()
    page_df.columns = [col_labels.get(c, c) for c in page_df.columns]

    # Truncate long review text for table display
    if "Review" in page_df.columns:
        page_df["Review"] = page_df["Review"].astype(str).apply(
            lambda x: x[:120] + "..." if len(x) > 120 else x
        )

    st.dataframe(
        page_df,
        use_container_width=True,
        hide_index=True,
        height=min(800, page_size * 38 + 50),
    )

# ─── Card View ───────────────────────────────────────────────────────────────────

else:
    # Card view with expandable details
    page_size = 20
    total_pages = max(1, (total + page_size - 1) // page_size)
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)

    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total)

    st.caption(f"Showing {start_idx + 1}–{end_idx} of {total:,} reviews (Page {page}/{total_pages})")

    for i in range(start_idx, end_idx):
        row = df.iloc[i]

        # Build header
        rating = row.get("star_rating", "?")
        stars = "★" * int(rating) + "☆" * (5 - int(rating)) if isinstance(rating, (int, float)) else "?"
        rating_color = {1: "#EF4444", 2: "#F97316", 3: "#F59E0B", 4: "#10B981", 5: "#059669"}.get(int(rating), "#6B7280")

        review_text = str(row.get("review_text", "No text"))
        summary_text = str(row.get("summary", ""))
        topic_text = str(row.get("topic", "N/A"))
        severity_text = str(row.get("severity", ""))
        sentiment_text = str(row.get("sentiment", ""))

        # Build badge row
        badges = []
        if severity_text and severity_text != "None":
            sev_cls = severity_text.lower()
            badges.append(f'<span class="badge badge-{sev_cls}">{severity_text}</span>')
        if sentiment_text and sentiment_text != "None":
            sent_cls = sentiment_text.lower()
            badges.append(f'<span class="badge badge-{sent_cls}">{sentiment_text}</span>')

        review_type = str(row.get("review_type", ""))
        if review_type and review_type != "None":
            badges.append(f'<span class="badge" style="background:rgba(108,99,255,0.2);color:#A78BFA;">{review_type}</span>')

        badge_html = " ".join(badges)

        # Meta info
        meta_parts = []
        if "app_version" in row.index and pd.notna(row["app_version"]):
            meta_parts.append(f"v{row['app_version']}")
        if "device" in row.index and pd.notna(row["device"]):
            meta_parts.append(str(row["device"]))
        if "review_date_only" in row.index and pd.notna(row["review_date_only"]):
            meta_parts.append(str(row["review_date_only"]))
        meta_html = " · ".join(meta_parts)

        st.markdown(f"""
        <div class="review-card">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                <span style="color:{rating_color};font-weight:700;font-size:1.1rem;">{stars}</span>
                <div>{badge_html}</div>
            </div>
            <div class="review-text">"{review_text}"</div>
            {f'<div style="color:#A78BFA;font-size:0.85rem;margin-bottom:0.4rem;">💡 {summary_text}</div>' if summary_text and summary_text != "None" and summary_text != "No summary" else ""}
            <div class="review-meta">
                <span style="color:#6C63FF;font-weight:500;">📂 {topic_text}</span>
                <span style="color:#6B7280;font-size:0.8rem;">{meta_html}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Expandable detail
        subtopic = str(row.get("subtopic", "N/A"))
        area = str(row.get("affected_area", "N/A"))
        actionable = str(row.get("actionability", "N/A"))

        with st.expander("View details", expanded=False):
            dc1, dc2, dc3, dc4 = st.columns(4)
            dc1.markdown(f"**Subtopic:** {subtopic}")
            dc2.markdown(f"**Area:** {area}")
            dc3.markdown(f"**Actionable:** {actionable}")
            dc4.markdown(f"**Language:** {row.get('reviewer_language', 'N/A')}")
