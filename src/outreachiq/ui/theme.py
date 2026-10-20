"""OutreachIQ – Advanced UI theme. Light mode only, modern SaaS-grade green design.

apply_theme(login=False) injects all CSS. apply_theme(login=True) also injects
the full-viewport split login layout. All CSS lives here.
"""
from __future__ import annotations

import streamlit as st

_FONTS = (
    "https://fonts.googleapis.com/css2?"
    "family=Plus+Jakarta+Sans:wght@400;500;600;700&"
    "family=Fraunces:opsz,wght@9..144,400;9..144,600&"
    "display=swap"
)


def _base_css() -> str:  # noqa: PLR0915
    return f"""
<style>
@import url('{_FONTS}');
/* ── Force light mode regardless of OS dark setting ──────────────────── */
:root, html, body {{ color-scheme: light only !important; }}
/* ── CSS Design Tokens ──────────────────────────────────────────────── */
:root {{
    --g950:#14291D; --g900:#1F3A2B; --g700:#2F5D42; --g600:#3B7A57;
    --g500:#4E9A6C; --g300:#9CCDAE; --g100:#DCEEE1; --g50:#EEF6F0;
    --bg:#F5F8F5;   --card:#FFFFFF; --text:#17231B; --muted:#667A6D;
    --border:#DDE8E0;
    --amber:#C98A1B; --danger:#B54A3C;
    --shadow-sm: 0 1px 3px rgba(20,41,29,.06),0 1px 2px rgba(20,41,29,.04);
    --shadow-md: 0 4px 12px rgba(20,41,29,.08),0 1px 3px rgba(20,41,29,.06);
    --shadow-lg: 0 8px 24px rgba(20,41,29,.10),0 2px 6px rgba(20,41,29,.06);
    --r-sm:8px; --r-md:14px; --r-lg:18px; --r-pill:999px;
    --t:0.18s ease;
}}
/* ── Base typography ─────────────────────────────────────────────────── */
html,body,[class*="css"] {{
    font-family:"Plus Jakarta Sans","Inter","Segoe UI",sans-serif;
    color:var(--text); background-color:var(--bg);
    color-scheme:light !important; line-height:1.55;
}}
h1 {{ font-family:"Fraunces",Georgia,serif; font-weight:600;
     letter-spacing:-.02em; color:var(--g900); font-size:1.8rem; }}
h2 {{ font-weight:600; letter-spacing:-.01em; color:var(--text); font-size:1.2rem; }}
h3 {{ font-weight:600; letter-spacing:-.01em; color:var(--text); font-size:1.05rem; }}
/* ── Layout & spacing ────────────────────────────────────────────────── */
.block-container {{ padding-top:2rem; padding-bottom:2.5rem; max-width:1280px; }}
[data-testid="stCaptionContainer"] {{ color:var(--muted); font-size:.83rem; }}
[data-testid="stDivider"]>hr {{ border-color:var(--border); margin:.75rem 0; }}
/* ── Cards ───────────────────────────────────────────────────────────── */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background:var(--card); border:1px solid var(--border);
    border-radius:var(--r-md); box-shadow:var(--shadow-sm);
    transition:box-shadow var(--t);
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    box-shadow:var(--shadow-md);
}}
/* ── Metrics ─────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background:var(--card); border:1px solid var(--border);
    border-radius:var(--r-md); padding:1rem 1.25rem;
    box-shadow:var(--shadow-sm); border-top:3px solid var(--g600);
    transition:box-shadow var(--t),transform var(--t);
}}
[data-testid="stMetric"]:hover {{ box-shadow:var(--shadow-md); transform:translateY(-1px); }}
[data-testid="stMetric"] label {{
    color:var(--muted); font-size:.68rem; font-weight:600;
    text-transform:uppercase; letter-spacing:.06em;
}}
[data-testid="stMetricValue"] {{ color:var(--g900); font-weight:700; font-size:1.55rem; }}
/* ── Dark sidebar ────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background:var(--g950) !important; border-right:1px solid var(--g900);
}}
section[data-testid="stSidebar"] * {{ color-scheme:dark; }}
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label {{
    color:#E8F3EC !important;
}}
section[data-testid="stSidebar"] > div:first-child {{ padding-top:1.5rem; }}
section[data-testid="stSidebar"] h3 {{
    font-family:"Fraunces",Georgia,serif; font-size:1.05rem;
    color:#FFFFFF !important; padding:0 .75rem; margin-bottom:.25rem;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{ gap:.1rem; }}
section[data-testid="stSidebar"] [aria-current="page"] {{
    background:var(--g600) !important; border-radius:10px;
    border-left:3px solid var(--g300);
}}
section[data-testid="stSidebar"] [aria-current="page"] span,
section[data-testid="stSidebar"] [aria-current="page"] p {{
    color:#FFFFFF !important; font-weight:600;
}}
section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {{
    background:rgba(78,154,108,.18) !important; border-radius:10px;
}}
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    color:#9CCDAE !important;
}}
/* ── Buttons ──────────────────────────────────────────────────────────── */
[data-testid="stBaseButton-primary"] {{
    background:var(--g600); color:#fff; border:none;
    border-radius:var(--r-sm); font-weight:600;
    box-shadow:0 1px 3px rgba(59,122,87,.3);
    transition:background var(--t),transform var(--t),box-shadow var(--t);
}}
[data-testid="stBaseButton-primary"]:hover {{
    background:var(--g700); transform:translateY(-1px);
    box-shadow:0 4px 10px rgba(59,122,87,.35);
}}
[data-testid="stBaseButton-secondary"] {{
    background:var(--card); border:1.5px solid var(--border);
    border-radius:var(--r-sm); color:var(--text); font-weight:500;
    transition:border-color var(--t),color var(--t);
}}
[data-testid="stBaseButton-secondary"]:hover {{
    border-color:var(--g600); color:var(--g600);
}}
/* ── Inputs ───────────────────────────────────────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {{
    border-radius:10px; border-color:var(--border);
    font-family:"Plus Jakarta Sans",sans-serif; font-size:.93rem;
    transition:border-color var(--t),box-shadow var(--t);
    background:var(--card) !important; color:var(--text) !important;
}}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {{
    border-color:var(--g600) !important;
    box-shadow:0 0 0 3px rgba(59,122,87,.15) !important;
    outline:none;
}}
[data-testid="stSelectbox"]>div>div {{
    border-radius:10px; border-color:var(--border);
    background:var(--card) !important;
}}
/* ── Tabs as pill/segmented ───────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {{
    gap:.35rem; background:var(--g50); border-radius:var(--r-pill);
    padding:.3rem; border:1px solid var(--border); display:inline-flex;
}}
[data-testid="stTabs"] [role="tablist"] button {{
    color:var(--muted); font-weight:500; border-radius:var(--r-pill);
    padding:.35rem .9rem; transition:all var(--t); border:none;
    background:transparent;
}}
[data-testid="stTabs"] [role="tablist"] button[aria-selected="true"] {{
    background:var(--g600); color:#fff; font-weight:600;
    box-shadow:var(--shadow-sm);
}}
/* ── DataFrames ────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] th {{
    background:var(--g50); color:var(--text); font-weight:600;
    font-size:.76rem; text-transform:uppercase; letter-spacing:.04em;
    border-bottom:2px solid var(--g100);
}}
[data-testid="stDataFrame"] tr:hover td {{ background:var(--g50); }}
[data-testid="stDataFrame"] td {{
    border-bottom:1px solid var(--border); padding:.45rem .75rem;
    font-size:.88rem;
}}
/* ── Alerts (tinted cards with left accent) ─────────────────────────── */
[data-testid="stAlert"] {{
    border-radius:var(--r-sm) !important;
    border-left:3px solid !important;
    border-top:none !important; border-right:none !important;
    border-bottom:none !important;
}}
/* ── Progress bars ───────────────────────────────────────────────────── */
[data-testid="stProgress"]>div>div {{ background:var(--g600); border-radius:99px; }}
/* ── Campaign Manager real-send tint ──────────────────────────────────── */
.oi-real-warn {{
    background:#FFF8EC; border:1px solid #E8C99A;
    border-left:3px solid var(--amber); border-radius:var(--r-sm);
    padding:.75rem 1rem; margin-bottom:.5rem;
}}
/* ── Hide Streamlit chrome ────────────────────────────────────────────── */
[data-testid="stFooter"]   {{ display:none !important; }}
[data-testid="stMainMenu"] {{ display:none !important; }}
header[data-testid="stHeader"] {{ background:transparent !important; }}
[data-testid="stToolbar"]  {{ display:none !important; }}
/* ── Slim scrollbar ───────────────────────────────────────────────────── */
::-webkit-scrollbar {{ width:5px; height:5px; }}
::-webkit-scrollbar-track {{ background:transparent; }}
::-webkit-scrollbar-thumb {{ background:var(--g300); border-radius:99px; }}
/* ── Smooth transitions, respect prefers-reduced-motion ─────────────── */
@media (prefers-reduced-motion:reduce) {{
    *,*::before,*::after {{ transition:none !important; animation:none !important; }}
}}
</style>
"""


def _login_css() -> str:
    return """
<style>
/* ── Force light on login ────────────────────────────────────────────── */
:root,html,body{color-scheme:light only!important;background:#FFFFFF!important;}
/* ── Hide Streamlit chrome ──────────────────────────────────────────── */
section[data-testid="stSidebar"]{display:none!important;}
[data-testid="stSidebarCollapseButton"]{display:none!important;}
header[data-testid="stHeader"]{display:none!important;}
[data-testid="stToolbar"]{display:none!important;}
/* ── Remove all container padding → full viewport ───────────────────── */
.block-container{max-width:100%!important;padding:0!important;margin:0!important;}
[data-testid="stMainBlockContainer"]{
    max-width:100%!important;padding:0!important;margin:0!important;
    display:flex!important;align-items:center!important;
    justify-content:center!important;min-height:100vh;
}
[data-testid="stAppViewBlockContainer"]{padding:0!important;}
/* ── Fade-slide in ──────────────────────────────────────────────────── */
@keyframes oiIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
[data-testid="stMainBlockContainer"]>div{
    animation:oiIn .35s ease;width:100%;max-width:440px;
    background:#fff;border:1px solid #DDE8E0;border-radius:16px;
    padding:2.25rem 2.5rem 2rem;
    box-shadow:0 4px 24px rgba(20,41,29,.09),0 1px 4px rgba(20,41,29,.06);
}
/* ── Compact inner spacing ──────────────────────────────────────────── */
[data-testid="stMainBlockContainer"] h1{
    font-size:1.6rem!important;margin-bottom:.1rem!important;
    color:#1F3A2B!important;
}
[data-testid="stMainBlockContainer"] hr{margin:.65rem 0!important;}
/* ── Feature row below form ─────────────────────────────────────────── */
.oi-feats{
    display:flex;gap:.75rem;flex-wrap:wrap;
    margin-top:1.25rem;padding-top:1rem;
    border-top:1px solid #DDE8E0;
}
.oi-feat{
    flex:1 1 28%;min-width:80px;font-size:.73rem;
    color:#667A6D;line-height:1.4;
}
.oi-feat-icon{
    font-size:.9rem;margin-bottom:.2rem;display:block;
}
/* ── Narrow: allow scroll ───────────────────────────────────────────── */
@media(max-width:520px){
    [data-testid="stMainBlockContainer"]>div{
        border:none;border-radius:0;box-shadow:none;padding:1.75rem 1.25rem;
    }
}
</style>
"""


def apply_theme(login: bool = False) -> None:
    """Inject the CSS bundle. login=True adds the centered card + hides sidebar."""
    st.markdown(_base_css(), unsafe_allow_html=True)
    if login:
        st.markdown(_login_css(), unsafe_allow_html=True)
