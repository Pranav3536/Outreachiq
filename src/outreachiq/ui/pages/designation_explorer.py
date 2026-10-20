"""Designation Explorer - browse by role, filter, build a campaign selection."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import pandas as pd  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from outreachiq.data.designation import categorize  # noqa: E402
from outreachiq.data.insights import (  # noqa: E402
    category_counts,
    distinct_titles,
    eligible_for_campaign,
)
from outreachiq.ui.components import (  # noqa: E402
    CHART_COLORS,
    load_contacts,
    page_header,
    style_plotly_fig,
)

page_header("Designation Explorer", "Browse contacts by role and build a campaign selection")

df = load_contacts()
if df is None:
    st.info("Load and clean contacts in Contact Data Lab first.")
    st.stop()

df = categorize(df)

st.subheader("Distinct titles")
titles_df = distinct_titles(df)
search = st.text_input("Search titles", key="title_search")
if search:
    titles_df = titles_df[
        titles_df["title"].astype(str).str.contains(search, case=False, na=False)
    ]
st.dataframe(titles_df, use_container_width=True, hide_index=True)

st.subheader("Filter contacts")
fc1, fc2, fc3 = st.columns(3)
cat_options = ["All"] + sorted(df["title_category"].dropna().unique().tolist())
sel_cat = fc1.selectbox("Category", cat_options, key="sel_cat")
comp_col = "company_clean" if "company_clean" in df.columns else "company"
if comp_col in df.columns:
    comp_values = sorted(df[comp_col].replace("", pd.NA).dropna().unique().tolist())
else:
    comp_values = []
comp_options = ["All"] + comp_values
sel_comp = fc2.selectbox("Company", comp_options, key="sel_comp")
title_text = fc3.text_input("Title contains", key="title_text")

view = df.copy()
if sel_cat != "All":
    view = view[view["title_category"] == sel_cat]
if sel_comp != "All" and comp_col in view.columns:
    view = view[view[comp_col] == sel_comp]
if title_text:
    view = view[view["title"].astype(str).str.contains(title_text, case=False, na=False)]

st.write(f"Matching contacts: {len(view)}")
display_cols = [
    c for c in [
        "name", "name_clean", "email", "email_clean",
        "title", "title_category", "company", "company_clean",
    ] if c in view.columns
]
st.dataframe(view[display_cols].head(100), use_container_width=True, hide_index=True)

st.subheader("Category summary")
cat_df = category_counts(df)
fig = style_plotly_fig(
    px.bar(cat_df, x="title_category", y="count", color="title_category",
           color_discrete_sequence=CHART_COLORS)
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Send selection to campaign")
eligible, n_excluded = eligible_for_campaign(view)
st.write(f"Eligible (valid email, not excluded): {len(eligible)}")
if n_excluded:
    st.caption(f"{n_excluded} row(s) excluded (invalid email or excluded duplicate).")
if st.button("Send selection to campaign", type="primary", key="btn_send_campaign"):
    st.session_state["campaign_selection"] = eligible
    st.success(f"Stored {len(eligible)} contacts in campaign_selection.")
