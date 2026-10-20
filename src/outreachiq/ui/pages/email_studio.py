"""Email Studio - template editor, live preview, resume management, campaign prep."""
import sys
from pathlib import Path
import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from outreachiq.config import (  # noqa: E402
    ENV_GMAIL_ADDRESS, is_env_set,
)
from outreachiq.data.export import cleaned_subset  # noqa: E402
from outreachiq.data.insights import load_cleaned  # noqa: E402
from outreachiq.email_tools.attachments import (  # noqa: E402
    MAX_RESUME_BYTES, delete_resume, resume_exists, resume_meta,
    save_resume, validate_resume,
)
from outreachiq.email_tools.campaign_prep import prepare_campaign  # noqa: E402
from outreachiq.email_tools.placeholders import (  # noqa: E402
    find_placeholders, render_for_contact,
)
from outreachiq.email_tools.templates import (  # noqa: E402
    DEFAULT_BODY, DEFAULT_SUBJECT, delete_template, list_templates,
    load_template, load_working, save_template, save_working,
)
from outreachiq.ui.components import load_contacts, page_header  # noqa: E402

page_header("Email Studio", "Compose, preview and prepare personalised outreach")

# ── Contacts source ────────────────────────────────────────────────────────────
contacts: pd.DataFrame | None = st.session_state.get("campaign_selection")

if contacts is None or len(contacts) == 0:
    st.info(
        "No campaign selection found. "
        "Select contacts in Designation Explorer or ML Priority Scores first."
    )
    # Fallback: load from contacts_clean.csv (valid + non-excluded)
    raw = load_contacts()
    if raw is not None and len(raw) > 0:
        contacts = cleaned_subset(raw, include_all=False)
        if len(contacts) > 0:
            st.caption(
                f"Using fallback: {len(contacts)} valid, non-excluded contacts "
                "from contacts_clean.csv."
            )
        else:
            contacts = None

if contacts is None or len(contacts) == 0:
    st.warning("No eligible contacts available. Load and clean data in Contact Data Lab first.")
    st.stop()

# ── Working template (persisted between sessions) ──────────────────────────────
working = load_working()
st.session_state.setdefault("studio_subject", working["subject"])
st.session_state.setdefault("studio_body", working["body"])

tab_tpl, tab_prev, tab_resume, tab_summary = st.tabs(
    ["Template", "Preview", "Resume", "Summary & Prepare"]
)

# ── TAB 1: Template editor ────────────────────────────────────────────────────
with tab_tpl:
    col_editor, col_mgr = st.columns([3, 1])

    with col_mgr:
        st.caption("Saved templates")
        saved = list_templates()
        if saved:
            sel = st.selectbox("Load template", ["(choose)"] + saved, key="tpl_load_sel")
            if st.button("Load", key="btn_load_tpl") and sel != "(choose)":
                t = load_template(sel)
                st.session_state["studio_subject"] = t["subject"]
                st.session_state["studio_body"] = t["body"]
                st.rerun()
        else:
            st.caption("No saved templates yet.")

        save_name = st.text_input("Save as", key="tpl_save_name")
        if st.button("Save template", key="btn_save_tpl"):
            if save_name.strip():
                save_template(
                    save_name,
                    st.session_state["studio_subject"],
                    st.session_state["studio_body"],
                )
                st.success(f"Saved '{save_name}'.")
            else:
                st.error("Enter a name first.")

        if saved:
            del_sel = st.selectbox("Delete template", ["(choose)"] + saved, key="tpl_del_sel")
            if st.button("Delete", key="btn_del_tpl") and del_sel != "(choose)":
                delete_template(del_sel)
                st.success(f"Deleted '{del_sel}'.")
                st.rerun()

        if st.button("Reset to default", key="btn_reset_tpl"):
            st.session_state["studio_subject"] = DEFAULT_SUBJECT
            st.session_state["studio_body"] = DEFAULT_BODY
            st.rerun()

        st.divider()
        all_ph = find_placeholders(
            st.session_state["studio_subject"] + " " + st.session_state["studio_body"]
        )
        cols_available = set(contacts.columns)
        st.caption("Placeholders in use:")
        for ph in sorted(all_ph):
            known = ph.lower() in {"name", "company", "title"} or ph.lower() in {
                c.lower() for c in cols_available
            }
            st.markdown(
                f"- `{{{ph}}}` {'✓' if known else '⚠ unknown'}"
            )

    with col_editor:
        new_subj = st.text_input(
            "Subject",
            value=st.session_state["studio_subject"],
            key="studio_subject_input",
        )
        new_body = st.text_area(
            "Body",
            value=st.session_state["studio_body"],
            height=320,
            key="studio_body_input",
        )
        if new_subj != st.session_state["studio_subject"] or \
                new_body != st.session_state["studio_body"]:
            st.session_state["studio_subject"] = new_subj
            st.session_state["studio_body"] = new_body
            save_working(new_subj, new_body)

# ── TAB 2: Live preview ────────────────────────────────────────────────────────
with tab_prev:
    name_col = "name_clean" if "name_clean" in contacts.columns else "name"
    email_col = "email_clean" if "email_clean" in contacts.columns else "email"
    labels = []
    for i, row in contacts.head(50).iterrows():
        n = str(row.get(name_col) or row.get("name", f"Row {i}")).strip() or f"Row {i}"
        e = str(row.get(email_col, "")).strip()
        labels.append(f"{n} <{e}>")

    if not labels:
        st.info("No contacts to preview.")
    else:
        sel_idx = st.selectbox(
            "Preview for contact", range(len(labels)),
            format_func=lambda i: labels[i], key="prev_contact_sel"
        )
        row = contacts.iloc[sel_idx]
        contact_dict = row.to_dict()
        result = render_for_contact(
            st.session_state["studio_subject"],
            st.session_state["studio_body"],
            contact_dict,
        )
        with st.container(border=True):
            st.markdown(f"**Subject:** {result.subject}")
            st.text(result.body[:600] + ("…" if len(result.body) > 600 else ""))
        if result.used_fallbacks:
            st.warning(f"Fallbacks used: {result.used_fallbacks}")
        if result.unresolved:
            st.error(f"Unresolved placeholders: {result.unresolved} — fix before sending.")

# ── TAB 3: Resume ─────────────────────────────────────────────────────────────
with tab_resume:
    meta = resume_meta()
    if meta:
        mtime = datetime.datetime.fromtimestamp(meta["mtime"]).strftime("%Y-%m-%d %H:%M")
        st.success(
            f"Resume on file: **{meta['filename']}** "
            f"({meta['size_bytes'] / 1024:.1f} KB, saved {mtime})"
        )
        if st.button("Delete saved resume", key="btn_del_resume"):
            delete_resume()
            st.rerun()
    else:
        st.info("No resume saved yet.")

    up = st.file_uploader(
        "Upload resume PDF (max 5 MB)", type=["pdf"], key="resume_uploader"
    )
    if up is not None:
        raw_bytes = up.getvalue()
        ok, msg = validate_resume(raw_bytes, up.name)
        if ok:
            save_resume(raw_bytes)
            st.success("Resume saved.")
            st.rerun()
        else:
            st.error(f"Resume rejected: {msg}")

# ── TAB 4: Summary & Prepare ──────────────────────────────────────────────────
with tab_summary:
    attach_resume = st.checkbox("Attach resume to every email", value=True, key="attach_resume")

    gmail_configured = is_env_set(ENV_GMAIL_ADDRESS)
    st.write(f"Gmail configured: **{'Yes' if gmail_configured else 'No (set GMAIL_ADDRESS in .env)'}**")
    st.write(f"Contacts in selection: **{len(contacts)}**")
    re_exists = resume_exists()
    if attach_resume:
        st.write(
            f"Resume: **{'Found' if re_exists else 'NOT saved — upload in Resume tab'}**"
        )

    if st.button("Prepare campaign", type="primary", key="btn_prepare"):
        camp = prepare_campaign(
            contacts,
            st.session_state["studio_subject"],
            st.session_state["studio_body"],
            attach_resume=attach_resume,
        )
        st.session_state["prepared_campaign"] = camp

    camp = st.session_state.get("prepared_campaign")
    if camp is not None:
        if camp.limit_exceeded:
            st.error(camp.limit_message)
        else:
            st.write(f"**Ready:** {camp.ready_count} | **Excluded:** {camp.excluded_count}")
            if attach_resume and not camp.resume_ready:
                st.error("Resume required but not saved. Upload a PDF in the Resume tab.")
            if camp.excluded_count:
                exc_df = pd.DataFrame([
                    {"name": r.name, "email": r.email, "reason": r.exclusion_reason}
                    for r in camp.recipients_excluded
                ])
                with st.expander(f"Excluded contacts ({camp.excluded_count})", expanded=False):
                    st.dataframe(exc_df, use_container_width=True, hide_index=True)
            if camp.ready_count:
                st.info(
                    f"{camp.ready_count} email(s) prepared. "
                    "Not sent. Go to Campaign Manager to review and send."
                )
