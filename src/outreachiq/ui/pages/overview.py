"""Overview Dashboard - KPIs, charts, quality indicators, campaign activity."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from outreachiq.data.column_mapping import CANONICAL_FIELDS  # noqa: E402
from outreachiq.data.designation import categorize  # noqa: E402
from outreachiq.data.insights import (  # noqa: E402
    campaign_history,
    category_counts,
    email_status_counts,
    kpis,
    missing_per_field,
    top_companies,
)
from outreachiq.ui.components import (  # noqa: E402
    CHART_COLORS,
    load_contacts,
    page_header,
    style_plotly_fig,
)

page_header("Overview Dashboard", "Campaign and contact summary")

df = load_contacts()
_has_data = df is not None
if not _has_data:
    st.info("Load and clean contacts in Contact Data Lab first.")
    st.stop()

if _has_data:
    df = categorize(df)
    k = kpis(df)

if _has_data:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total contacts", k["total"])
    c2.metric("Valid emails", k["valid_emails"])
    c3.metric("Invalid emails", k["invalid_emails"])
    c4.metric("Duplicates", k["duplicates"])
    c5.metric("Unique companies", k["unique_companies"])
    c6.metric("Missing fields", k["contacts_with_missing"])

if _has_data:
    st.subheader("Category distribution")
    cat_df = category_counts(df)
    fig = style_plotly_fig(
        px.bar(cat_df, x="title_category", y="count", color="title_category",
               color_discrete_sequence=CHART_COLORS)
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 10 companies")
    tc = top_companies(df, 10)
    fig = style_plotly_fig(
        px.bar(tc, x="company", y="count", color_discrete_sequence=[CHART_COLORS[0]])
    )
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.caption("Valid vs invalid emails")
        es = email_status_counts(df)
        names = [n for n, v in [("Valid", es["valid"]), ("Invalid", es["invalid"])] if v > 0]
        values = [v for v in [es["valid"], es["invalid"]] if v > 0]
        if not names:
            names, values = ["Valid", "Invalid"], [0, 0]
        pie = px.pie(
            names=names, values=values, hole=0.5,
            color=names,
            color_discrete_map={"Valid": CHART_COLORS[0], "Invalid": CHART_COLORS[2]},
        )
        st.plotly_chart(style_plotly_fig(pie), use_container_width=True)
    with right:
        st.caption("Missing values per field")
        mf = missing_per_field(df)
        mf_df = pd.DataFrame(list(mf.items()), columns=["field", "count"])
        bar = px.bar(mf_df, x="field", y="count", color_discrete_sequence=[CHART_COLORS[1]])
        st.plotly_chart(style_plotly_fig(bar), use_container_width=True)

    st.subheader("Data quality indicators")
    mf = missing_per_field(df)
    rows = [
        ("Valid emails", k["valid_emails"]),
        ("Invalid emails", k["invalid_emails"]),
        ("Duplicate rows", k["duplicates"]),
        ("Rows with missing fields", k["contacts_with_missing"]),
    ]
    rows += [(f"Missing {f}", mf.get(f, 0)) for f in CANONICAL_FIELDS]
    st.dataframe(
        pd.DataFrame(rows, columns=["Indicator", "Value"]),
        use_container_width=True,
        hide_index=True,
    )

st.subheader("Campaign activity")
try:
    from outreachiq.campaigns.history_store import FileHistoryStore as _HS
    _store = _HS()
    _campaigns = _store.list_campaigns()
except Exception:
    _campaigns = []

if not _campaigns:
    st.info("No campaigns yet.")
else:
    summary_rows = []
    for c in _campaigns:
        recips = c.get("recipients", [])
        statuses = [r.get("status", "") for r in recips]
        summary_rows.append({
            "campaign_id": c.get("campaign_id", ""),
            "created_at": c.get("created_at", "")[:19].replace("T", " "),
            "mode": c.get("mode", ""),
            "status": c.get("status", ""),
            "ready": c.get("total_ready", 0),
            "accepted_by_server": sum(1 for s in statuses if s == "SMTP Accepted"),
            "simulated": sum(1 for s in statuses if s == "Simulated"),
            "failed": sum(1 for s in statuses if s == "Failed"),
            "unknown": sum(1 for s in statuses if s == "Unknown/Needs Review"),
            "pending": sum(1 for s in statuses if s == "Pending"),
        })
    st.dataframe(
        pd.DataFrame(summary_rows), use_container_width=True, hide_index=True
    )
    st.caption(
        "'accepted_by_server' means Gmail's server accepted the message — "
        "not a delivery confirmation."
    )
