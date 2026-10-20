"""Campaign Manager - assistant tab + review/confirm/send campaign."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from outreachiq.assistant.tools import (  # noqa: E402
    campaign_history_summary,
    data_quality_summary,
    inspect_dataset,
    propose_campaign,
    selection_summary,
    suggest_classifications,
)
from outreachiq.assistant.workflow import (  # noqa: E402
    SUPPORTED_COMMANDS,
    parse_command,
    unknown_command_help,
)
from outreachiq.campaigns.history_store import FileHistoryStore  # noqa: E402
from outreachiq.config import (  # noqa: E402
    ENV_GMAIL_ADDRESS, ENV_MAX_RECIPIENTS_PER_CAMPAIGN,
    get_env_int, is_env_set,
)
from outreachiq.email_tools.attachments import resume_exists  # noqa: E402
from outreachiq.email_tools.smtp_config import (  # noqa: E402
    SmtpConfigError, credentials_status, load_smtp_config,
)
from outreachiq.email_tools.smtp_sender import (  # noqa: E402
    STATUS_ACCEPTED, STATUS_FAILED, STATUS_PENDING,
    STATUS_SIMULATED, STATUS_UNKNOWN,
    run_batch,
)
from outreachiq.ui.components import load_contacts, page_header  # noqa: E402

page_header("Campaign Manager", "Review, confirm and send your outreach campaign")

store = FileHistoryStore()

# ── Tabs: assistant + send ────────────────────────────────────────────────────
tab_assistant, tab_send = st.tabs(["Outreach Assistant", "Send Campaign"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: OUTREACH ASSISTANT
# ═══════════════════════════════════════════════════════════════════════════════

with tab_assistant:
    st.session_state.setdefault("assistant_transcript", [])
    st.session_state.setdefault("assistant_proposal", None)

    contacts_df = load_contacts()

    def _handle_command(text):
        if not text or not text.strip():
            return
        cmd, args = parse_command(text)
        ts = st.session_state["assistant_transcript"]
        ts.append(f"**You:** {text}")

        if cmd == "inspect":
            r = inspect_dataset(contacts_df)
            ts.append(
                f"**Assistant:** Dataset has {r['rows']} rows, "
                f"{len(r['columns'])} columns. Mapping: {r['mapping_status']}."
            )
        elif cmd == "quality":
            r = data_quality_summary(contacts_df)
            ts.append(
                f"**Assistant:** Invalid emails: {r['invalid_emails']}, "
                f"Duplicates: {r['duplicates']}, "
                f"Missing fields: {r['missing_fields']}."
            )
        elif cmd == "suggest_titles":
            results = suggest_classifications(contacts_df)
            if not results:
                ts.append("**Assistant:** No uncertain titles found.")
            else:
                for item in results[:10]:
                    ts.append(
                        f"**Assistant:** '{item['title']}' "
                        f"-> {item['suggested_category']} "
                        f"(confidence: {item['confidence']}, "
                        f"source: {item['source']})"
                    )
        elif cmd == "selection":
            sel = st.session_state.get("campaign_selection")
            r = selection_summary(sel)
            cats = ", ".join(f"{k}: {v}" for k, v in r["categories"].items()) or "none"
            ts.append(
                f"**Assistant:** Selection has {r['count']} eligible contacts "
                f"({r['excluded']} excluded). Categories: {cats}."
            )
        elif cmd == "history":
            r = campaign_history_summary(store)
            ts.append(
                f"**Assistant:** {r['campaigns']} campaigns. "
                f"Accepted: {r['smtp_accepted']}, "
                f"Failed: {r['failed']}, "
                f"Unknown: {r['unknown_needs_review']}, "
                f"Simulated: {r['simulated']}."
            )
        elif cmd == "propose":
            proposal = propose_campaign(
                contacts_df,
                categories=args.get("categories"),
                limit=args.get("limit"),
                store=store,
            )
            st.session_state["assistant_proposal"] = proposal
            ts.append(
                f"**Assistant:** Proposed campaign with "
                f"{proposal.recipient_count} recipients. "
                f"{len(proposal.exclusion_reasons)} excluded, "
                f"{len(proposal.already_sent_skips)} already sent. "
                f"Template ready: {proposal.template_ready}, "
                f"Resume: {proposal.resume_ready}, "
                f"Gmail configured: {proposal.gmail_configured}."
            )
        else:
            ts.append(f"**Assistant:** {unknown_command_help()}")

        st.session_state["assistant_transcript"] = ts[-100:]
        st.rerun()

    # Transcript display
    for line in st.session_state["assistant_transcript"]:
        st.markdown(line)

    # Quick-action buttons
    st.caption("Quick actions")
    qa = st.columns(len(SUPPORTED_COMMANDS))
    for i, (cmd_label, _desc) in enumerate(SUPPORTED_COMMANDS):
        label = cmd_label.split("<")[0].strip()
        if qa[i].button(label, key=f"qa_{i}", use_container_width=True):
            _handle_command(label)

    # Chat input
    user_input = st.text_input("Ask the assistant...", key="assistant_input")
    if st.button("Send", key="btn_assistant_send"):
        _handle_command(user_input)

    # Proposal card
    proposal = st.session_state.get("assistant_proposal")
    if proposal is not None:
        with st.container(border=True):
            st.subheader("Campaign proposal")
            pc1, pc2, pc3 = st.columns(3)
            pc1.metric("Recipients", proposal.recipient_count)
            pc2.metric("Excluded", proposal.excluded_count)
            pc3.metric("Already sent (skip)", len(proposal.already_sent_skips))

            st.write(f"**Categories:** {', '.join(proposal.categories) or 'all'}")
            st.write(f"**Limit:** {proposal.limit}")
            st.write(f"**Template ready:** {proposal.template_ready}")
            st.write(f"**Resume ready:** {proposal.resume_ready}")
            st.write(f"**Gmail configured:** {proposal.gmail_configured}")

            if proposal.exclusion_reasons:
                with st.expander(f"Exclusions ({len(proposal.exclusion_reasons)})"):
                    st.dataframe(
                        pd.DataFrame(proposal.exclusion_reasons),
                        use_container_width=True, hide_index=True,
                    )
            if proposal.already_sent_skips:
                with st.expander(f"Already sent ({len(proposal.already_sent_skips)})"):
                    st.write(proposal.already_sent_skips)

            ac1, ac2 = st.columns(2)
            if ac1.button("Approve proposal", type="primary", key="btn_approve"):
                st.session_state["campaign_selection"] = proposal.included
                st.success(
                    "Proposal approved. Go to Email Studio, "
                    "then Campaign Manager (Send tab) to review and send."
                )
                st.session_state["assistant_proposal"] = None
                st.rerun()
            if ac2.button("Discard", key="btn_discard"):
                st.session_state["assistant_proposal"] = None
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: SEND CAMPAIGN (existing flow)
# ═══════════════════════════════════════════════════════════════════════════════

with tab_send:
    campaign = st.session_state.get("prepared_campaign")
    if campaign is None:
        st.info(
            "No prepared campaign found. "
            "Go to Email Studio, compose your template, "
            "and click 'Prepare campaign'."
        )
    else:
        max_recip = get_env_int(ENV_MAX_RECIPIENTS_PER_CAMPAIGN, default=100) or 100
        cred_status = credentials_status()
        gmail_ok = cred_status["configured"]
        resume_ok = resume_exists()

        # ── Mode selector ─────────────────────────────────────────────────────
        st.subheader("Send mode")
        mode = st.radio(
            "Choose mode",
            ["Test mode (no email sent)", "Real send (Gmail SMTP)"],
            index=0, key="camp_mode", horizontal=True,
        )
        is_real = mode == "Real send (Gmail SMTP)"

        if is_real:
            st.warning(
                "**Real send mode.** Emails will be sent via Gmail SMTP. "
                "Review all recipients carefully before pressing Send."
            )
        else:
            st.info("Test mode: simulates sending, no network connection made.")

        # ── Pre-send panel ────────────────────────────────────────────────────
        with st.container(border=True):
            st.subheader("Pre-send checklist")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Ready recipients", campaign.ready_count)
            col2.metric("Excluded", campaign.excluded_count)
            col3.metric("Resume attached", "Yes" if campaign.attach_resume and resume_ok else "No")
            col4.metric("Gmail configured", "Yes" if gmail_ok else "No")

            if campaign.excluded_count:
                with st.expander(f"Excluded recipients ({campaign.excluded_count})", expanded=False):
                    exc_rows = [
                        {"name": r.name, "email": r.email, "reason": r.exclusion_reason}
                        for r in campaign.recipients_excluded
                    ]
                    st.dataframe(pd.DataFrame(exc_rows), use_container_width=True, hide_index=True)

            past_sent = store.sent_keys()
            ready_emails = {r.email.lower() for r in campaign.recipients_ready}
            already_in_history = ready_emails & past_sent
            if already_in_history:
                st.warning(
                    f"{len(already_in_history)} recipient(s) already appear in past "
                    "real-mode campaigns. They will be skipped automatically."
                )
                with st.expander("See list", expanded=False):
                    st.write(sorted(already_in_history))

            if campaign.recipients_ready:
                sample = campaign.recipients_ready[0]
                with st.expander("Sample rendered email (first recipient)", expanded=False):
                    st.markdown(f"**To:** {sample.email}")
                    if sample.rendered:
                        st.markdown(f"**Subject:** {sample.rendered.subject}")
                        st.text(sample.rendered.body[:400] + (
                            "\u2026" if sample.rendered.body and len(sample.rendered.body) > 400 else ""
                        ))

            delay_default = get_env_int("SEND_DELAY_SECONDS", default=5) or 5
            delay_min = 3 if is_real else 0
            delay = st.number_input(
                "Delay between emails (seconds)",
                min_value=delay_min, max_value=60,
                value=max(delay_min, delay_default),
                key="camp_delay",
            )

        # ── Blocking checks ───────────────────────────────────────────────────
        blocked = False
        if is_real:
            if not gmail_ok:
                st.error(
                    f"Gmail not configured. Set {ENV_GMAIL_ADDRESS} "
                    "(and GMAIL_APP_PASSWORD) in your .env file."
                )
                blocked = True
            if not campaign.is_sendable:
                st.error("Campaign is not sendable. Check resume and recipient list.")
                blocked = True
            if campaign.ready_count > max_recip:
                st.error(f"{campaign.ready_count} recipients exceeds the limit of {max_recip}.")
                blocked = True
            if campaign.ready_count >= 10:
                st.warning(
                    f"Sending to {campaign.ready_count} recipients. "
                    "Be aware of Gmail daily limits (~500/day). "
                    "Bulk outreach may be flagged as spam."
                )

        # ── Real-mode confirmation gate ───────────────────────────────────────
        confirmed = True
        if is_real and not blocked:
            st.subheader("Confirmation required")
            chk = st.checkbox(
                "I have reviewed the recipients and want to send real emails.",
                key="camp_confirm_chk",
            )
            recip_input = st.text_input(
                f"Type the number of recipients ({campaign.ready_count}) to confirm:",
                key="camp_confirm_num",
            )
            confirmed = chk and recip_input.strip() == str(campaign.ready_count)
            if not confirmed:
                st.caption("Both confirmation fields are required before sending.")

        # ── Session state for run control ──────────────────────────────────────
        st.session_state.setdefault("camp_results", [])
        st.session_state.setdefault("camp_running", False)
        st.session_state.setdefault("camp_stop", False)
        st.session_state.setdefault("camp_id", None)

        # ── Send / Stop buttons ───────────────────────────────────────────────
        btn_col1, btn_col2 = st.columns(2)
        send_pressed = btn_col1.button(
            "Send" if is_real else "Simulate send",
            type="primary",
            disabled=(blocked or not confirmed or st.session_state["camp_running"]),
            key="btn_camp_send",
        )
        stop_pressed = btn_col2.button(
            "Stop", disabled=not st.session_state["camp_running"], key="btn_camp_stop"
        )

        if stop_pressed:
            st.session_state["camp_stop"] = True

        if send_pressed and not blocked and confirmed:
            st.session_state["camp_results"] = []
            st.session_state["camp_stop"] = False
            st.session_state["camp_running"] = True

            template_name = st.session_state.get("tpl_load_sel", "working")
            camp_id = store.create_campaign(
                mode="real" if is_real else "test",
                subject=campaign.subject_template,
                template_name=template_name if template_name != "(choose)" else "working",
                resume_attached=campaign.attach_resume and resume_ok,
                total_ready=campaign.ready_count,
                total_excluded=campaign.excluded_count,
            )
            st.session_state["camp_id"] = camp_id

            config = None
            if is_real:
                try:
                    config = load_smtp_config()
                except SmtpConfigError as exc:
                    st.error(str(exc))
                    st.session_state["camp_running"] = False

            if config is not None or not is_real:
                results_holder = []

                def _on_result(r):
                    results_holder.append(r)
                    store.update_recipient(camp_id, r)
                    st.session_state["camp_results"] = list(results_holder)

                def _should_stop():
                    return bool(st.session_state.get("camp_stop", False))

                try:
                    import time as _time
                    results = run_batch(
                        campaign,
                        config=config,
                        mode="real" if is_real else "test",
                        delay_seconds=int(delay),
                        already_sent_keys=past_sent,
                        on_result=_on_result,
                        should_stop=_should_stop,
                        _sleep=_time.sleep,
                    )
                except Exception as exc:
                    err = str(exc)
                    for word in ("password", "secret", "token"):
                        if word in err.lower():
                            err = "(credential-related error -- check .env)"
                            break
                    st.error(f"Batch error: {err}")
                    results = results_holder

                final_status = "Stopped" if st.session_state["camp_stop"] else "Completed"
                store.set_status(camp_id, final_status)
            st.session_state["camp_running"] = False

        # ── Progress / results ────────────────────────────────────────────────
        results = st.session_state.get("camp_results", [])
        if results:
            st.subheader("Results")
            counts = {
                STATUS_ACCEPTED: 0, STATUS_SIMULATED: 0,
                STATUS_FAILED: 0, STATUS_UNKNOWN: 0, STATUS_PENDING: 0,
            }
            for r in results:
                if r.status in counts:
                    counts[r.status] += 1

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Accepted by server", counts[STATUS_ACCEPTED])
            c2.metric("Simulated", counts[STATUS_SIMULATED])
            c3.metric("Failed", counts[STATUS_FAILED])
            c4.metric("Unknown/Review", counts[STATUS_UNKNOWN])
            c5.metric("Pending", counts[STATUS_PENDING])

            rows = [
                {
                    "name": r.recipient_name, "email": r.email,
                    "status": r.status, "mode": r.mode,
                    "summary": r.error_summary,
                    "time": r.timestamp[:19].replace("T", " "),
                }
                for r in results
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

            unknown_rows = [r for r in results if r.status == STATUS_UNKNOWN]
            if unknown_rows:
                st.warning(
                    f"{len(unknown_rows)} result(s) are Unknown/Needs Review. "
                    "Check your Gmail Sent folder. Do NOT retry."
                )

            st.info(
                "**SMTP Accepted means Gmail's server accepted the message. "
                "It does not confirm inbox delivery. Check your Gmail Sent folder.**"
            )

            if counts.get(STATUS_FAILED, 0):
                auth_fail = any("authentication" in r.error_summary.lower() for r in results)
                rate_fail = any(
                    "rate" in r.error_summary.lower() or "quota" in r.error_summary.lower()
                    for r in results
                )
                if auth_fail:
                    st.error(
                        "Authentication failure. Check GMAIL_APP_PASSWORD in .env. "
                        "Generate a new App Password at myaccount.google.com if needed."
                    )
                if rate_fail:
                    st.error("Rate-limit or quota error. Wait several hours before sending again.")
