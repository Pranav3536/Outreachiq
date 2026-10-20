"""Reusable UI components for OutreachIQ pages."""
from __future__ import annotations

import streamlit as st

from ..data.duplicates import detect
from ..data.insights import load_cleaned
from ..data.validation import validate
from .theme import apply_theme

# Plotly chart color palette
CHART_COLORS = ["#2F5D42", "#4E9A6C", "#9CCDAE", "#DCEEE1", "#C98A1B", "#B54A3C"]


# ── Page header ───────────────────────────────────────────────────────────────

def page_header(
    title: str,
    subtitle: str | None = None,
    section_label: str | None = None,
    status_chip: str | None = None,
    status_kind: str = "neutral",
) -> None:
    """Hero-style page header. Applies theme, renders serif title + subtitle + divider.

    section_label: small uppercase label above title (e.g. "Data").
    status_chip: optional right-aligned status text (e.g. "1 843 contacts loaded").
    status_kind: "success" | "warning" | "danger" | "neutral" | "info".
    """
    apply_theme()
    if section_label or status_chip:
        c1, c2 = st.columns([3, 1])
        with c1:
            if section_label:
                st.markdown(
                    f'<p style="font-size:.7rem;font-weight:700;letter-spacing:.1em;'
                    f'text-transform:uppercase;color:var(--g600,#3B7A57);'
                    f'margin-bottom:.2rem;">{section_label}</p>',
                    unsafe_allow_html=True,
                )
            st.title(title)
        with c2:
            if status_chip:
                status_chip_html(status_chip, status_kind)
    else:
        st.title(title)
    if subtitle:
        st.caption(subtitle)
    st.divider()


# ── Status chip ───────────────────────────────────────────────────────────────

_CHIP_COLORS = {
    "success":  ("#D1F5E3", "#1F6B42", "#29A05A"),
    "warning":  ("#FFF2D8", "#8A5A00", "#C98A1B"),
    "danger":   ("#FDE8E6", "#7C2316", "#B54A3C"),
    "neutral":  ("#EEF6F0", "#3B7A57", "#4E9A6C"),
    "info":     ("#E6F2FF", "#1A4D8F", "#2F7ADE"),
}


def status_chip_html(text: str, kind: str = "neutral") -> None:
    bg, fg, bd = _CHIP_COLORS.get(kind, _CHIP_COLORS["neutral"])
    st.markdown(
        f'<span style="display:inline-block;background:{bg};color:{fg};'
        f'border:1px solid {bd};border-radius:999px;'
        f'padding:.25rem .75rem;font-size:.75rem;font-weight:600;'
        f'letter-spacing:.02em;">{text}</span>',
        unsafe_allow_html=True,
    )


def status_chip(text: str, kind: str = "neutral") -> None:
    status_chip_html(text, kind)


# ── Metric card ───────────────────────────────────────────────────────────────

def metric_card(
    label: str,
    value: str | int,
    delta: str | None = None,
    icon: str | None = None,
) -> None:
    """Render a styled metric card using st.metric. icon is display text/emoji."""
    display_label = f"{icon}  {label}" if icon else label
    if delta is not None:
        st.metric(display_label, value, delta=delta)
    else:
        st.metric(display_label, value)


# ── Section card ──────────────────────────────────────────────────────────────

def section_card(border: bool = True):
    """Return st.container(border=True/False) with consistent styling."""
    return st.container(border=border)


# ── Empty state ───────────────────────────────────────────────────────────────

def empty_state(message: str, hint: str | None = None, icon: str = "○") -> None:
    st.markdown(
        f'<div style="text-align:center;padding:2.5rem 1rem;'
        f'color:var(--muted,#667A6D);">'
        f'<div style="font-size:2rem;margin-bottom:.5rem;">{icon}</div>'
        f'<p style="font-weight:600;color:var(--text,#17231B);margin-bottom:.25rem;">'
        f'{message}</p>'
        + (f'<p style="font-size:.85rem;">{hint}</p>' if hint else "")
        + "</div>",
        unsafe_allow_html=True,
    )


# ── Info callout ──────────────────────────────────────────────────────────────

def info_callout(text: str, kind: str = "info") -> None:
    """Render a tinted info callout using st.info / st.warning / st.error / st.success."""
    fn = {"info": st.info, "warning": st.warning, "danger": st.error, "success": st.success}
    fn.get(kind, st.info)(text)


# ── Plotly chart styler ────────────────────────────────────────────────────────

def style_plotly_fig(fig, show_legend: bool = False, title: str | None = None):
    """Apply the OutreachIQ Plotly template: transparent bg, sage palette, clean axes."""
    fig.update_layout(
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font_family="'Plus Jakarta Sans', 'Inter', 'Segoe UI', sans-serif",
        font_color="#17231B",
        margin=dict(l=8, r=8, t=40 if title else 28, b=8),
        showlegend=show_legend,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor="rgba(0,0,0,0)",
            font_size=11,
        ),
        title_text=title,
        title_font_size=13,
        title_font_color="#667A6D",
    )
    fig.update_xaxes(
        gridcolor="#DCEEE1",
        linecolor="#DDE8E0",
        zerolinecolor="#DCEEE1",
        tickfont_size=11,
    )
    fig.update_yaxes(
        gridcolor="#DCEEE1",
        linecolor="#DDE8E0",
        zerolinecolor="#DCEEE1",
        tickfont_size=11,
    )
    # Bar-specific: slight opacity
    fig.update_traces(
        opacity=0.92,
        selector=dict(type="bar"),
    )
    # Pie / donut: hole 0.6 for consistent donut style
    fig.update_traces(
        hole=0.6,
        textfont_size=11,
        selector=dict(type="pie"),
    )
    return fig


# ── Contact loader (unchanged logic) ──────────────────────────────────────────

def load_contacts():
    """Load cleaned contacts; prefer session state, fall back to CSV."""
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
