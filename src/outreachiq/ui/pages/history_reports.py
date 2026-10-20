"""Campaign History & Reports - read-only view, filters, charts, review notes."""
import sys
from pathlib import Path
import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from outreachiq.campaigns.history_store import FileHistoryStore  # noqa: E402
from outreachiq.campaigns.reports import (  # noqa: E402
    campaigns_to_df,
    export_csv_bytes,
    export_xlsx_bytes,
    filter_campaigns,
    filter_recipients,
    load_review_notes,
    recipients_df,
    save_review_note,
    summary_stats,
)
from outreachiq.ui.components import (  # noqa: E402
    CHART_COLORS, page_header, style_plotly_fig,
)

page_header("Campaign History & Reports", "Read-only campaign records and metrics")

store = FileHistoryStore()
camp_df, warnings = campaigns_to_df(store)

# Show corrupt-file warnings if any
if warnings:
    st.warning(f"Skipped {len(warnings)} corrupt campaign file(s): {', '.join(warnings)}")

# ── Filters ───────────────────────────────────────────────────────────────────
with st.container(border=True):
    fc1, fc2, fc3, fc4 = st.columns(4)
    date_from = fc1.date_input("From", value=None, key="rep_date_from")
    date_to = fc2.date_input("To", value=None, key="rep_date_to")
    mode_filter = fc3.selectbox(
        "Mode", ["All", "test", "real"], key="rep_mode",
    )
    status_filter = fc4.selectbox(
        "Status",
        ["All", "Running", "Completed", "Stopped", "Draft", "Paused"],
        key="rep_status",
    )
    search = st.text_input("Search (subject, campaign ID, email, company, title)",
                            key="rep_search")

filtered_camps = filter_campaigns(
    camp_df,
    date_from=str(date_from) if date_from else None,
    date_to=str(date_to) if date_to else None,
    mode=mode_filter,
    status=status_filter,
    search=search or None,
)

# ── Summary metrics ──────────────────────────────────────────────────────────
stats = summary_stats(filtered_camps)
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Campaigns", stats["campaigns"])
m2.metric("Accepted by server", stats["smtp_accepted"])
m3.metric("Failed", stats["failed"])
m4.metric("Unknown/Review", stats["unknown_needs_review"])
m5.metric("Simulated", stats["simulated"])
m6.metric("Pending", stats["pending"])
st.caption(
    "**SMTP Accepted means Gmail's server accepted the message. "
    "It does not confirm inbox delivery.**"
)

if filtered_camps.empty:
    st.info("No campaigns match the current filters.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_camps, tab_recips, tab_charts, tab_review = st.tabs(
    ["Campaigns", "Recipients", "Charts", "Needs Review"]
)

# ── Tab 1: Campaigns ──────────────────────────────────────────────────────────
with tab_camps:
    display_camps = filtered_camps.drop(columns=["created_at_dt"], errors="ignore")
    st.dataframe(display_camps, use_container_width=True, hide_index=True)

    st.caption("Download")
    dc1, dc2 = st.columns(2)
    dc1.download_button("Campaigns CSV", export_csv_bytes(display_camps),
                         file_name="campaigns.csv", mime="text/csv", key="dl_camp_csv")
    dc2.download_button("Campaigns XLSX", export_xlsx_bytes(display_camps),
                         file_name="campaigns.xlsx",
                         mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                         key="dl_camp_xlsx")

    # Drill-down
    st.subheader("Campaign drill-down")
    camp_ids = filtered_camps["campaign_id"].tolist()
    if camp_ids:
        sel_id = st.selectbox("Select campaign", camp_ids, key="drill_sel")
        if sel_id:
            recips = recipients_df(campaign_id=sel_id, store=store)
            if not recips.empty:
                st.write(f"{len(recips)} recipients in {sel_id}")
                st.dataframe(recips, use_container_width=True, hide_index=True)
            else:
                st.info("No recipients found in this campaign.")

# ── Tab 2: Recipients ─────────────────────────────────────────────────────────
with tab_recips:
    all_recips = recipients_df(store=store)
    # Apply same mode/search filter to recipients
    filt_recips = filter_recipients(
        all_recips,
        mode=mode_filter,
        search=search or None,
    )
    if filt_recips.empty:
        st.info("No recipient rows match the current filters.")
    else:
        st.write(f"{len(filt_recips)} recipient rows")
        st.dataframe(filt_recips, use_container_width=True, hide_index=True)
        dr1, dr2 = st.columns(2)
        dr1.download_button("Recipients CSV", export_csv_bytes(filt_recips),
                             file_name="recipients.csv", mime="text/csv", key="dl_rec_csv")
        dr2.download_button("Recipients XLSX", export_xlsx_bytes(filt_recips),
                             file_name="recipients.xlsx",
                             mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             key="dl_rec_xlsx")

# ── Tab 3: Charts ─────────────────────────────────────────────────────────────
with tab_charts:
    st.subheader("Campaigns over time")
    if not filtered_camps.empty and "created_at_dt" in filtered_camps:
        time_df = filtered_camps.copy()
        time_df["date"] = time_df["created_at_dt"].dt.date
        by_date = time_df.groupby("date").size().reset_index(name="campaigns")
        fig = style_plotly_fig(
            px.bar(by_date, x="date", y="campaigns",
                   color_discrete_sequence=[CHART_COLORS[0]])
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Status distribution")
    status_cols = ["smtp_accepted", "simulated", "failed", "unknown_needs_review", "pending"]
    status_labels = ["SMTP Accepted", "Simulated", "Failed", "Unknown/Review", "Pending"]
    if not filtered_camps.empty:
        totals = [int(filtered_camps[c].sum()) for c in status_cols]
        pie_df = pd.DataFrame({"status": status_labels, "count": totals})
        pie_df = pie_df[pie_df["count"] > 0]
        if not pie_df.empty:
            pie = px.pie(
                pie_df, names="status", values="count", hole=0.4,
                color="status",
                color_discrete_sequence=CHART_COLORS,
            )
            st.plotly_chart(style_plotly_fig(pie), use_container_width=True)
        else:
            st.info("No status data to chart.")

# ── Tab 4: Needs Review ────────────────────────────────────────────────────────
with tab_review:
    st.caption("Real-mode recipients with status 'Unknown/Needs Review'. "
               "Add a manual note for your records. No resend button.")
    all_recips_rv = recipients_df(store=store)
    review_rows = all_recips_rv[
        (all_recips_rv["status"] == "Unknown/Needs Review")
        & (all_recips_rv["mode"] == "real")
    ] if not all_recips_rv.empty else pd.DataFrame()

    if review_rows.empty:
        st.info("No 'Unknown/Needs Review' rows found in real-mode campaigns.")
    else:
        st.write(f"{len(review_rows)} row(s) need review")
        notes = load_review_notes()
        for i, row in review_rows.iterrows():
            cid = row["campaign_id"]
            email = row["email"]
            key = f"{cid}|{email.lower()}"
            existing = notes.get(key, {}).get("note", "")
            with st.expander(f"{email} — {cid}", expanded=False):
                st.write(f"**Error:** {row.get('error_summary', '')}")
                st.write(f"**Time:** {row.get('timestamp', '')[:19]}")
                note_text = st.text_area(
                    "Manual note", value=existing, key=f"note_{cid}_{email}",
                )
                if st.button("Save note", key=f"btn_note_{cid}_{email}"):
                    save_review_note(cid, email, note_text)
                    st.success("Note saved.")
