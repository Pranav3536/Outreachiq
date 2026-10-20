"""OutreachIQ - main entry. Polished login card + multipage navigation.

First run: create a local user with `python scripts/create_user.py`, then
`streamlit run app.py` and log in.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from outreachiq.auth import LoginAttemptTracker, list_users, verify  # noqa: E402
from outreachiq.config import AUTH_DIR, ensure_dirs  # noqa: E402
from outreachiq.ui.theme import apply_theme  # noqa: E402

PAGES_DIR = Path(__file__).resolve().parent / "src" / "outreachiq" / "ui" / "pages"


def _any_user_exists() -> bool:
    if not (AUTH_DIR / "credentials.json").exists():
        return False
    return len(list_users()) > 0


def _show_login() -> None:
    apply_theme(login=True)
    st.title("OutreachIQ")
    st.caption("Smart Outreach Intelligence Platform")
    st.divider()

    if not _any_user_exists():
        st.warning("No local user found. Create one in your terminal:")
        st.code("python scripts/create_user.py", language="bash")
        _login_features()
        return

    if "login_tracker" not in st.session_state:
        st.session_state["login_tracker"] = LoginAttemptTracker()
    tracker: LoginAttemptTracker = st.session_state["login_tracker"]

    if tracker.is_locked():
        st.error(f"Too many failed attempts. Please wait {tracker.lockout_remaining_seconds()}s.")
        _login_features()
        return

    st.subheader("Welcome back")
    st.caption("Sign in to your local workspace")

    with st.form("login_form"):
        username = st.text_input(
            "Username", autocomplete="username", placeholder="your username",
        )
        password = st.text_input(
            "Password", type="password", autocomplete="current-password",
            placeholder="\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022",
        )
        submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")

    if submitted:
        if not username or not password:
            st.error("Invalid credentials.")
        elif verify(username, password):
            tracker.record_success()
            st.session_state["authenticated"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            tracker.record_failure()
            remaining = tracker.remaining_attempts()
            msg = (
                f"Invalid credentials. {remaining} attempt(s) remaining."
                if remaining > 0
                else "Too many failed attempts. Locked temporarily."
            )
            st.error(msg)
            st.rerun()

    _login_features()


def _login_features() -> None:
    st.markdown(
        '<div class="oi-feats">'
        '<div class="oi-feat">'
        '<span class="oi-feat-icon">&#9783;</span>Clean contact data</div>'
        '<div class="oi-feat">'
        '<span class="oi-feat-icon">&#9670;</span>Explainable ML</div>'
        '<div class="oi-feat">'
        '<span class="oi-feat-icon">&#9993;</span>Controlled email</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def _build_nav() -> dict:
    return {
        "Navigate": [
            st.Page(PAGES_DIR / "overview.py", title="Overview Dashboard", default=True),
            st.Page(PAGES_DIR / "contact_lab.py", title="Contact Data Lab"),
            st.Page(PAGES_DIR / "designation_explorer.py", title="Designation Explorer"),
            st.Page(PAGES_DIR / "ml_nlp.py", title="ML & NLP Intelligence"),
            st.Page(PAGES_DIR / "email_studio.py", title="Email Studio"),
            st.Page(PAGES_DIR / "campaign_manager.py", title="Campaign Manager"),
            st.Page(PAGES_DIR / "history_reports.py", title="Campaign History & Reports"),
        ]
    }


def _show_app() -> None:
    apply_theme()
    pg = st.navigation(_build_nav())
    with st.sidebar:
        st.markdown(
            '<h3 style="color:#FFFFFF;font-family:Fraunces,serif;'
            'letter-spacing:-.01em;padding:0 .25rem .1rem;">OutreachIQ</h3>',
            unsafe_allow_html=True,
        )
        st.divider()
        uname = st.session_state.get("username", "")
        st.markdown(
            f'<div style="font-size:.8rem;color:#9CCDAE;padding:0 .25rem .5rem;">'
            f'Signed in as <strong style="color:#DCEEE1;">{uname}</strong></div>',
            unsafe_allow_html=True,
        )
    pg.run()
    with st.sidebar:
        st.divider()
        if st.button("Log out", use_container_width=True):
            for key in ("authenticated", "username", "login_tracker"):
                st.session_state.pop(key, None)
            st.rerun()


def main() -> None:
    st.set_page_config(page_title="OutreachIQ", page_icon="📬", layout="wide")
    ensure_dirs()
    st.session_state.setdefault("authenticated", False)
    if st.session_state["authenticated"]:
        _show_app()
    else:
        _show_login()


if __name__ == "__main__":
    main()
