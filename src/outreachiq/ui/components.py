"""Reusable UI components for OutreachIQ pages."""
from __future__ import annotations

import streamlit as st

from ..data.duplicates import detect
from ..data.insights import load_cleaned
from ..data.validation import validate
from .theme import apply_theme

CHART_COLORS = ["#426F52", "#7FA68A", "#B7D3BE", "#D2E3D5", "#E6F0E7"]


def page_header(title: str, subtitle: str | None = None) -> None:
    """Render a consistent page header: applies theme, then title + subtitle + divider."""
    apply_theme()
    st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.divider()


def style_plotly_fig(fig):
    """Apply the OutreachIQ chart template: white bg, Inter font, sage palette."""
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="Inter, 'Segoe UI', sans-serif",
        font_color="#1F2A22",
        margin=dict(l=8, r=8, t=36, b=8),
        showlegend=False,
        title_font_size=14,
        title_font_color="#6B7A70",
    )
    fig.update_xaxes(
        gridcolor="#E6F0E7", linecolor="#DDE7DF", zerolinecolor="#E6F0E7",
        tickfont_size=11,
    )
    fig.update_yaxes(
        gridcolor="#E6F0E7", linecolor="#DDE7DF", zerolinecolor="#E6F0E7",
        tickfont_size=11,
    )
    # Apply consistent styling to all traces (opacity at trace level, not marker)
    fig.update_traces(
        marker_line_width=0,
        opacity=0.9,
        selector=dict(type="bar"),
    )
    fig.update_traces(
        marker_line_width=0,
        selector=dict(type="scatter"),
    )
    return fig


def load_contacts():
    """Load cleaned contacts for dashboard/explorer.

    Prefers the in-memory cleaned dataset (st.session_state['contacts_clean'],
    which retains all validation flags), then falls back to
    data/processed/contacts_clean.csv. Ensures flag columns exist. Returns None
    if there is nothing to show.
    """
    cleaned = st.session_state.get("contacts_clean")
    if cleaned is not None and len(cleaned) > 0:
        df = cleaned.copy()
    else:
        df = load_cleaned()
    if df is None or len(df) == 0:
        return None
    if "email_valid" not in df.columns:
        df = validate(df)
    if "is_duplicate" not in df.columns:
        df = detect(df)
    if "excluded" not in df.columns:
        df["excluded"] = False
    return df
