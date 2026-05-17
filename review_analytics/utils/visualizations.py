"""
Visualization Module
Reusable Plotly chart builders with consistent dark-mode-friendly styling.
"""

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# ─── Color Palette ───────────────────────────────────────────────────────────────

COLORS = {
    "primary": "#6C63FF",
    "secondary": "#A78BFA",
    "accent": "#F59E0B",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "info": "#3B82F6",
    "muted": "#6B7280",
}

RATING_COLORS = {1: "#EF4444", 2: "#F97316", 3: "#F59E0B", 4: "#10B981", 5: "#059669"}

SENTIMENT_COLORS = {"Positive": "#10B981", "Neutral": "#6B7280", "Negative": "#EF4444"}

SEVERITY_COLORS = {"High": "#EF4444", "Medium": "#F59E0B", "Low": "#10B981"}

REVIEW_TYPE_COLORS = {
    "Complaint": "#EF4444", "Praise": "#10B981", "Feature Request": "#3B82F6",
    "Question / Confusion": "#F59E0B", "Noise / Irrelevant": "#6B7280",
}

CHART_PALETTE = ["#6C63FF", "#A78BFA", "#3B82F6", "#10B981", "#F59E0B",
                 "#EF4444", "#EC4899", "#8B5CF6", "#14B8A6", "#F97316",
                 "#06B6D4", "#84CC16"]

LAYOUT_DEFAULTS = dict(
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color="#FAFAFA"),
    margin=dict(l=20, r=20, t=40, b=20),
    hoverlabel=dict(bgcolor="#1A1D29", font_size=13, font_family="Inter, sans-serif"),
    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
)


def _apply_layout(fig, title="", height=400):
    fig.update_layout(**LAYOUT_DEFAULTS, title=dict(text=title, font_size=16, x=0.01), height=height)
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.06)")
    return fig


# ─── Chart Builders ──────────────────────────────────────────────────────────────

def rating_distribution_chart(df, title="Rating Distribution"):
    if "star_rating" not in df.columns:
        return go.Figure()
    counts = df["star_rating"].value_counts().sort_index()
    colors = [RATING_COLORS.get(r, COLORS["muted"]) for r in counts.index]
    fig = go.Figure(go.Bar(
        x=counts.values, y=[f"{r}★" for r in counts.index],
        orientation="h", marker_color=colors,
        text=counts.values, textposition="auto",
        hovertemplate="Rating: %{y}<br>Count: %{x}<extra></extra>",
    ))
    return _apply_layout(fig, title, 300)


def trend_line_chart(df, date_col="review_date_only", title="Review Trend", agg="W"):
    if date_col not in df.columns:
        return go.Figure()
    df_c = df.copy()
    df_c[date_col] = pd.to_datetime(df_c[date_col])
    grouped = df_c.set_index(date_col).resample(agg).size().reset_index(name="count")
    fig = go.Figure(go.Scatter(
        x=grouped[date_col], y=grouped["count"],
        mode="lines+markers", line=dict(color=COLORS["primary"], width=2.5),
        marker=dict(size=6), fill="tozeroy",
        fillcolor="rgba(108,99,255,0.15)",
        hovertemplate="Date: %{x|%b %d, %Y}<br>Reviews: %{y}<extra></extra>",
    ))
    return _apply_layout(fig, title, 350)


def donut_chart(df, col, title="", colors=None):
    if col not in df.columns:
        return go.Figure()
    counts = df[col].value_counts()
    c = colors or {k: CHART_PALETTE[i % len(CHART_PALETTE)] for i, k in enumerate(counts.index)}
    fig = go.Figure(go.Pie(
        labels=counts.index, values=counts.values,
        hole=0.55, marker_colors=[c.get(k, COLORS["muted"]) for k in counts.index],
        textinfo="label+percent", textfont_size=12,
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    return _apply_layout(fig, title, 350)


def horizontal_bar_chart(df, col, title="", top_n=10, color=None):
    if col not in df.columns:
        return go.Figure()
    counts = df[col].value_counts().head(top_n).sort_values()
    fig = go.Figure(go.Bar(
        x=counts.values, y=counts.index, orientation="h",
        marker_color=color or COLORS["primary"],
        text=counts.values, textposition="auto",
        hovertemplate="%{y}: %{x}<extra></extra>",
    ))
    h = max(300, len(counts) * 35 + 80)
    return _apply_layout(fig, title, h)


def heatmap_chart(df, x_col, y_col, title=""):
    if x_col not in df.columns or y_col not in df.columns:
        return go.Figure()
    ct = pd.crosstab(df[y_col], df[x_col])
    fig = go.Figure(go.Heatmap(
        z=ct.values, x=ct.columns.tolist(), y=ct.index.tolist(),
        colorscale=[[0, "#1A1D29"], [0.5, "#6C63FF"], [1, "#A78BFA"]],
        hovertemplate="%{y} × %{x}: %{z}<extra></extra>",
    ))
    h = max(350, len(ct.index) * 30 + 100)
    return _apply_layout(fig, title, h)


def grouped_bar_chart(data, x_col, y_col, title="", color=None, horizontal=False):
    """Bar chart from pre-aggregated data (DataFrame with x_col, y_col)."""
    if horizontal:
        data_sorted = data.sort_values(y_col, ascending=True)
        fig = go.Figure(go.Bar(
            x=data_sorted[y_col], y=data_sorted[x_col], orientation="h",
            marker_color=color or COLORS["primary"],
            text=[f"{v:.2f}" if isinstance(v, float) else str(v) for v in data_sorted[y_col]],
            textposition="auto",
            hovertemplate="%{y}: %{x:.2f}<extra></extra>",
        ))
        h = max(300, len(data_sorted) * 35 + 80)
    else:
        data_sorted = data.sort_values(x_col)
        fig = go.Figure(go.Bar(
            x=data_sorted[x_col], y=data_sorted[y_col],
            marker_color=color or COLORS["primary"],
            text=[f"{v:.1f}" if isinstance(v, float) else str(v) for v in data_sorted[y_col]],
            textposition="auto",
            hovertemplate="%{x}: %{y:.2f}<extra></extra>",
        ))
        h = 400
    return _apply_layout(fig, title, h)


def stacked_bar_chart(df, group_col, stack_col, title="", top_n=10):
    if group_col not in df.columns or stack_col not in df.columns:
        return go.Figure()
    top_groups = df[group_col].value_counts().head(top_n).index
    filtered = df[df[group_col].isin(top_groups)]
    ct = pd.crosstab(filtered[group_col], filtered[stack_col])
    fig = go.Figure()
    for i, col in enumerate(ct.columns):
        fig.add_trace(go.Bar(
            name=str(col), x=ct.index.tolist(), y=ct[col].values,
            marker_color=CHART_PALETTE[i % len(CHART_PALETTE)],
            hovertemplate=f"{col}: " + "%{y}<extra></extra>",
        ))
    fig.update_layout(barmode="stack")
    return _apply_layout(fig, title, 450)


def topic_trend_chart(df, topic_col="topic", date_col="review_date_only", title="Topic Trends", top_n=6):
    if topic_col not in df.columns or date_col not in df.columns:
        return go.Figure()
    top_topics = df[topic_col].value_counts().head(top_n).index
    filtered = df[df[topic_col].isin(top_topics)].copy()
    filtered[date_col] = pd.to_datetime(filtered[date_col])
    fig = go.Figure()
    for i, topic in enumerate(top_topics):
        topic_df = filtered[filtered[topic_col] == topic]
        grouped = topic_df.set_index(date_col).resample("W").size().reset_index(name="count")
        fig.add_trace(go.Scatter(
            x=grouped[date_col], y=grouped["count"], name=str(topic),
            mode="lines+markers", line=dict(color=CHART_PALETTE[i % len(CHART_PALETTE)], width=2),
            marker=dict(size=5),
            hovertemplate=f"{topic}<br>Date: %{{x|%b %d}}<br>Count: %{{y}}<extra></extra>",
        ))
    return _apply_layout(fig, title, 400)


def version_comparison_chart(data, version_col, metric_col, title="", color=None, fmt=".2f"):
    """Bar chart for version metrics. data should be a pre-aggregated DataFrame."""
    data_sorted = data.sort_values(version_col)
    fig = go.Figure(go.Bar(
        x=data_sorted[version_col], y=data_sorted[metric_col],
        marker_color=color or COLORS["primary"],
        text=[f"{v:{fmt}}" for v in data_sorted[metric_col]],
        textposition="auto",
        hovertemplate="%{x}: %{y:" + fmt + "}<extra></extra>",
    ))
    return _apply_layout(fig, title, 400)
