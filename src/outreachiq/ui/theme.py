"""Custom CSS for OutreachIQ. Premium white + light sage, restrained.

All CSS lives in this one function. Google Fonts loaded via @import for
Inter (body) and Fraunces (serif headings). No images, no glow, no heavy
gradients.
"""
from __future__ import annotations

import streamlit as st

_FONTS_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap');"


def _shared_css() -> str:
    return f"""
<style>
{_FONTS_IMPORT}
:root {{
    --sage-50: #F4F8F4;  --sage-100: #E6F0E7; --sage-200: #D2E3D5;
    --sage-300: #B7D3BE; --green-600: #426F52; --green-700: #365A44;
    --green-900: #1F3A2B; --bg: #F7F9F6; --card: #FFFFFF;
    --text: #1F2A22; --muted: #6B7A70; --border: #DDE7DF;
}}

/* ── Typography ─────────────────────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: "Inter", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    color: var(--text); line-height: 1.55;
}}
h1 {{ font-family: "Fraunces", Georgia, serif; font-weight: 600;
     letter-spacing: -0.02em; color: var(--green-900); font-size: 1.75rem; }}
h2 {{ font-weight: 600; letter-spacing: -0.01em; color: var(--text); font-size: 1.25rem; }}
h3 {{ font-weight: 600; letter-spacing: -0.01em; color: var(--text); font-size: 1.1rem; }}

/* ── Layout ──────────────────────────────────────────────────────────── */
.block-container {{
    padding-top: 2.5rem; padding-bottom: 2rem; max-width: 1200px;
}}
[data-testid="stCaptionContainer"] {{ color: var(--muted); font-size: 0.85rem; }}

/* ── Cards ──────────────────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background-color: var(--card); border: 1px solid var(--border);
    border-radius: 12px; box-shadow: 0 1px 2px rgba(31,58,43,0.05);
}}

/* ── Metric cards ───────────────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background-color: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1rem 1.25rem;
    box-shadow: 0 1px 2px rgba(31,58,43,0.05);
    border-top: 3px solid var(--green-600);
}}
[data-testid="stMetric"] label {{
    color: var(--muted); font-size: 0.7rem;
    text-transform: uppercase; letter-spacing: 0.06em;
}}
[data-testid="stMetricValue"] {{ color: var(--green-900); font-weight: 700; font-size: 1.5rem; }}

/* ── Sidebar ────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background-color: var(--sage-50); border-right: 1px solid var(--border);
}}
section[data-testid="stSidebar"] > div:first-child {{ padding-top: 1.5rem; }}
section[data-testid="stSidebar"] h3 {{
    font-family: "Fraunces", Georgia, serif; font-size: 1.1rem;
    color: var(--green-900); margin-bottom: 0; padding: 0 0.5rem;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{ gap: 0.15rem; }}
/* Active nav item: soft sage bg, dark-green text, 3px green left accent */
section[data-testid="stSidebar"] [aria-current="page"] {{
    background-color: var(--sage-200); border-radius: 8px;
    border-left: 3px solid var(--green-600);
}}
section[data-testid="stSidebar"] [aria-current="page"] span,
section[data-testid="stSidebar"] [aria-current="page"] p {{
    color: var(--green-900); font-weight: 500;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{
    background-color: var(--sage-100); border-radius: 8px;
}}

/* ── Buttons ────────────────────────────────────────────────────────── */
[data-testid="stBaseButton-primary"] {{
    background-color: var(--green-600); color: #fff;
    border: none; border-radius: 8px; font-weight: 500;
    transition: background-color 0.15s ease;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background-color: var(--green-700); color: #fff; border-color: var(--green-700);
}}
[data-testid="stBaseButton-secondary"] {{
    background-color: var(--card); border: 1px solid var(--border);
    border-radius: 8px; color: var(--text); font-weight: 500;
    transition: border-color 0.15s ease, color 0.15s ease;
}}
[data-testid="stBaseButton-secondary"]:hover {{
    border-color: var(--green-600); color: var(--green-600);
}}

/* ── Inputs ─────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    border-radius: 8px; border-color: var(--border);
    font-family: "Inter", sans-serif;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
    outline: none; border-color: var(--green-600);
    box-shadow: 0 0 0 2px rgba(66,111,82,0.12);
}}
[data-testid="stSelectbox"] > div > div {{
    border-radius: 8px; border-color: var(--border);
}}

/* ── Tabs ───────────────────────────────────────────────────────────── */
[data-testid="stTabs"][role="tablist"] button {{
    color: var(--muted); font-weight: 500;
}}
[data-testid="stTabs"][role="tablist"] button[aria-selected="true"] {{
    color: var(--green-600); border-bottom: 2px solid var(--green-600);
}}

/* ── DataFrames ─────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] th {{
    background-color: var(--sage-50); color: var(--text);
    font-weight: 600; font-size: 0.8rem; text-transform: uppercase;
    letter-spacing: 0.03em;
}}
[data-testid="stDataFrame"] td {{ border-bottom: 1px solid var(--border); padding: 0.5rem 0.75rem; }}

/* ── Alerts ─────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {{
    border-radius: 8px !important; border-left: 3px solid !important;
}}

/* ── Progress bars ──────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div {{ background-color: var(--green-600); }}

/* ── Dividers ───────────────────────────────────────────────────────── */
[data-testid="stDivider"] > hr {{
    border-color: var(--border); margin: 1rem 0;
}}

/* ── Campaign Manager: real-send mode tint (amber/warm tint, tasteful) ──── */
.oi-real-send-block {{
    background-color: #FFF8F0;
    border: 1px solid #E8C99A;
    border-left: 3px solid #C87941;
    border-radius: 8px;
    padding: 0.75rem 1rem;
}}
/* ── Hide Streamlit chrome ───────────────────────────────────────────── */
[data-testid="stFooter"] {{ display: none !important; }}
[data-testid="stMainMenu"] {{ display: none !important; }}
header[data-testid="stHeader"] {{ background: transparent; }}
</style>
"""


def _login_css() -> str:
    return """
<style>
    /* ── Hide Streamlit chrome on login ─────────────────────────────── */
    section[data-testid="stSidebar"]          { display: none !important; }
    [data-testid="stSidebarCollapseButton"]   { display: none !important; }
    header[data-testid="stHeader"]            { display: none !important; }
    [data-testid="stToolbar"]                 { display: none !important; }

    /* ── Sage background, zero padding, full viewport ───────────────── */
    body, [data-testid="stApp"]   { background-color: #F4F8F4 !important; }
    .block-container {
        max-width: 100% !important;
        padding: 0 !important;
        margin:  0 !important;
    }
    [data-testid="stMainBlockContainer"] {
        max-width: 100% !important;
        padding: 0 !important;
        min-height: 100vh;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        animation: oiFadeIn 0.25s ease;
    }
    @keyframes oiFadeIn { from { opacity:0; transform:translateY(4px); }
                          to   { opacity:1; transform:translateY(0);    } }

    /* ── White card, centered, compact ─────────────────────────────── */
    [data-testid="stMainBlockContainer"] > div {
        width: 100%;
        max-width: 420px;
        background: #FFFFFF;
        border: 1px solid #DDE7DF;
        border-radius: 12px;
        padding: 2rem 2.25rem 1.75rem;
        box-shadow: 0 2px 8px rgba(31,58,43,0.07);
    }

    /* ── Tighten inner spacing ──────────────────────────────────────── */
    [data-testid="stMainBlockContainer"] h1 {
        font-size: 1.65rem !important; margin-bottom: 0.1rem !important;
    }
    [data-testid="stMainBlockContainer"] [data-testid="stCaptionContainer"] {
        margin-bottom: 0.5rem !important;
    }
    [data-testid="stMainBlockContainer"] hr { margin: 0.75rem 0 !important; }

    /* ── Feature lines row ──────────────────────────────────────────── */
    .oi-features {
        display: flex; gap: 1rem; flex-wrap: wrap;
        margin-top: 1rem; padding-top: 0.75rem;
        border-top: 1px solid #DDE7DF;
    }
    .oi-feat {
        font-size: 0.75rem; color: #6B7A70; line-height: 1.4;
        flex: 1 1 30%; min-width: 90px;
    }
    .oi-feat::before {
        content: ""; display: block; width: 18px; height: 1px;
        background: #426F52; margin-bottom: 0.3rem;
    }

    /* ── Narrow screens: allow scroll, tighter padding ─────────────── */
    @media (max-width: 480px) {
        [data-testid="stMainBlockContainer"] > div {
            border-radius: 0; border: none; box-shadow: none;
            padding: 1.5rem 1.25rem;
        }
    }
</style>
"""


def apply_theme(login: bool = False) -> None:
    """Inject the full CSS bundle. In login mode, hide sidebar and split layout."""
    st.markdown(_shared_css(), unsafe_allow_html=True)
    if login:
        st.markdown(_login_css(), unsafe_allow_html=True)
