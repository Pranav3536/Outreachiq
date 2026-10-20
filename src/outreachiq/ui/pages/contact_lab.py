"""Contact Data Lab - upload, mapping (Tab 1), cleaning/validation/export (Tab 2)."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from outreachiq.data.cleaning import clean  # noqa: E402
from outreachiq.data.column_mapping import (  # noqa: E402
    CANONICAL_FIELDS, apply_mapping, save_mapped, suggest_mapping,
)
from outreachiq.data.duplicates import apply_exclude, detect  # noqa: E402
from outreachiq.data.export import (  # noqa: E402
    cleaned_csv_bytes, cleaned_xlsx_bytes, report_csv_bytes,
    report_xlsx_bytes, save_cleaned, save_report,
)
from outreachiq.data.loader import LoaderError, load_dataframe, save_upload  # noqa: E402
from outreachiq.data.quality_report import build_report, problem_rows  # noqa: E402
from outreachiq.data.validation import validate  # noqa: E402
from outreachiq.ui.components import page_header  # noqa: E402

page_header("Contact Data Lab", "Upload contacts, map columns, clean and validate")

for key, default in [
    ("contacts_mapped", None), ("contacts_clean", None),
    ("contacts_mapped_path", None), ("contacts_clean_path", None),
]:
    st.session_state.setdefault(key, default)

tab_upload, tab_clean = st.tabs(["1  Upload & Mapping", "2  Clean & Validate"])

# ─────────────────────────────────────────────────────────────
# TAB 1  Upload & Mapping
# ─────────────────────────────────────────────────────────────
with tab_upload:
    uploaded = st.file_uploader("Upload CSV or XLSX", type=["csv", "xlsx", "xls"])

    if uploaded is None:
        if st.session_state["contacts_mapped"] is not None:
            st.info("A previously mapped dataset is in session memory.")
            st.dataframe(
                st.session_state["contacts_mapped"].head(10), use_container_width=True
            )
        else:
            st.info(
                "Upload a CSV or XLSX file to begin. "
                "Try a sample from `sample_data/`."
            )
        st.stop()

    raw = uploaded.getvalue()
    try:
        saved_path = save_upload(uploaded.name, raw)
    except Exception as exc:
        st.error(f"Could not save the uploaded file: {exc}")
        st.stop()

    try:
        df = load_dataframe(saved_path)
    except LoaderError as exc:
        st.error(str(exc))
        st.stop()

    st.success(
        f"Loaded {len(df)} rows x {len(df.columns)} columns from `{uploaded.name}`."
    )
    st.caption(f"Upload saved unchanged to: `{saved_path}`")

    with st.expander("Preview first rows", expanded=True):
        st.dataframe(df.head(10), use_container_width=True)

    st.subheader("Confirm column mapping")
    st.write(f"Canonical fields: {', '.join(CANONICAL_FIELDS)}")

    result = suggest_mapping(df)
    uncertain = [s for s in result.suggestions if s.needs_confirmation]
    if uncertain:
        st.warning(
            f"{len(uncertain)} field(s) need confirmation: "
            + ", ".join(s.canonical for s in uncertain)
        )

    columns = [None] + list(df.columns)
    mapping: dict = {}
    for s in result.suggestions:
        marker = "  !" if s.needs_confirmation else ""
        suggested = s.suggested_column
        default_idx = columns.index(suggested) if suggested in columns else 0
        fallback = "(none)"
        chosen = st.selectbox(
            f"{s.canonical}{marker}",
            columns,
            index=default_idx,
            key=f"map_{s.canonical}",
            help=(
                f"Suggested: {suggested or fallback} | "
                f"confidence: {s.confidence} | {s.reason}"
            ),
        )
        mapping[s.canonical] = chosen or None

    if st.button("Apply mapping", type="primary", key="btn_apply_mapping"):
        mapped = apply_mapping(df, mapping)
        out_path = save_mapped(mapped)
        st.session_state["contacts_mapped"] = mapped
        st.session_state["contacts_mapped_path"] = str(out_path)
        st.success(f"Mapping applied and saved to `{out_path}`.")
        st.write(f"**Rows:** {len(mapped)}")
        preserved = [c for c in mapped.columns if c not in CANONICAL_FIELDS]
        if preserved:
            st.write(
                f"**Preserved columns ({len(preserved)}):** {', '.join(map(str, preserved))}"
            )
        st.dataframe(mapped.head(10), use_container_width=True)

# ─────────────────────────────────────────────────────────────
# TAB 2  Clean & Validate
# ─────────────────────────────────────────────────────────────
with tab_clean:
    mapped_df = st.session_state.get("contacts_mapped")
    if mapped_df is None or len(mapped_df) == 0:
        st.info("Map your contacts in Tab 1 first, then come back here.")
        st.stop()

    st.caption(f"Working from {len(mapped_df)} mapped rows.")

    if st.button("Run cleaning and validation", type="primary", key="btn_run_clean"):
        cleaned, changes = clean(mapped_df)
        cleaned = validate(cleaned)
        cleaned = detect(cleaned)
        if "excluded" not in cleaned.columns:
            cleaned["excluded"] = False
        st.session_state["contacts_clean_raw"] = cleaned
        st.session_state["cleaning_changes"] = changes

    cleaned = st.session_state.get("contacts_clean_raw")
    if cleaned is None:
        st.stop()

    changes = st.session_state.get("cleaning_changes", {})
    if changes:
        delta_parts = [f"{k}: {v} row(s) changed" for k, v in changes.items() if v]
        if delta_parts:
            st.success("Cleaning done. Changes: " + " | ".join(delta_parts))
        else:
            st.success("Cleaning done. No whitespace/casing changes needed.")

    # ── Quality report ──────────────────────────────────────
    report = build_report(cleaned)
    probs = problem_rows(cleaned)
    st.subheader("Quality report")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total rows", report["total_rows"])
    c2.metric("Valid emails", report["valid_emails"])
    c3.metric("Invalid emails", report["invalid_emails"])
    c4.metric("Duplicate rows", report["duplicate_rows"])
    missing_cols = st.columns(len(CANONICAL_FIELDS))
    for col_widget, f in zip(missing_cols, CANONICAL_FIELDS):
        col_widget.metric(f"Missing {f}", report["missing"].get(f, 0))

    if len(probs) > 0:
        with st.expander(f"Problem rows ({len(probs)})", expanded=False):
            disp_cols = [c for c in probs.columns if c not in {
                "email_clean", "missing_name", "missing_email",
                "missing_title", "missing_company",
                "is_duplicate", "duplicate_group_id", "excluded",
            }]
            st.dataframe(probs[disp_cols].head(30), use_container_width=True)

    # ── Before / after preview ──────────────────────────────
    st.subheader("Before / after preview")
    bc, ac = st.columns(2)
    with bc:
        st.caption("Original (mapped)")
        st.dataframe(mapped_df.head(8), use_container_width=True)
    with ac:
        st.caption("After cleaning")
        show_cols = [c for c in cleaned.columns if c in CANONICAL_FIELDS or c.endswith("_clean")]
        st.dataframe(cleaned[show_cols].head(8), use_container_width=True)

    # ── Duplicate review ────────────────────────────────────
    dup_groups = cleaned.loc[
        cleaned["is_duplicate"] | (cleaned["duplicate_group_id"] > 0),
        "duplicate_group_id"
    ].unique()
    dup_groups = [g for g in dup_groups if g > 0]

    if dup_groups:
        st.subheader(f"Duplicate review ({len(dup_groups)} groups)")
        decisions: dict = {}
        for gid in dup_groups:
            group_rows = cleaned[cleaned["duplicate_group_id"] == gid]
            with st.expander(
                f"Group {gid} ({len(group_rows)} rows) "
                + (group_rows["email_clean"].iloc[0] if "email_clean" in group_rows.columns else ""),
                expanded=False,
            ):
                show = [c for c in ["name", "name_clean", "email_clean", "company", "title"]
                        if c in group_rows.columns]
                st.dataframe(group_rows[show], use_container_width=True)
                decisions[gid] = st.radio(
                    "Action",
                    ["keep_first", "keep_all", "exclude"],
                    horizontal=True,
                    key=f"dup_{gid}",
                )
        if st.button("Apply duplicate decisions", key="btn_dup"):
            cleaned = apply_exclude(cleaned, decisions)
            st.session_state["contacts_clean_raw"] = cleaned
            excluded_n = int(cleaned["excluded"].sum())
            st.success(
                f"Decisions applied. {excluded_n} row(s) marked excluded "
                "(nothing deleted)."
            )

    # ── Filter / search ─────────────────────────────────────
    st.subheader("Browse and filter")
    col_f1, col_f2, col_f3 = st.columns(3)
    filter_validity = col_f1.selectbox(
        "Email validity", ["All", "Valid", "Invalid"], key="filter_valid"
    )
    filter_missing = col_f2.selectbox(
        "Missing field",
        ["None"] + list(CANONICAL_FIELDS),
        key="filter_missing",
    )
    companies_list = ["All"]
    if "company_clean" in cleaned.columns:
        companies_list += sorted(
            cleaned["company_clean"].replace("", None).dropna().unique().tolist()
        )
    elif "company" in cleaned.columns:
        companies_list += sorted(cleaned["company"].dropna().unique().tolist())
    filter_company = col_f3.selectbox("Company", companies_list, key="filter_company")

    view = cleaned.copy()
    if filter_validity == "Valid" and "email_valid" in view.columns:
        view = view[view["email_valid"] == True]
    elif filter_validity == "Invalid" and "email_valid" in view.columns:
        view = view[view["email_valid"] == False]
    if filter_missing != "None":
        col_miss = f"missing_{filter_missing}"
        if col_miss in view.columns:
            view = view[view[col_miss] == True]
    if filter_company != "All":
        if "company_clean" in view.columns:
            view = view[view["company_clean"] == filter_company]
        elif "company" in view.columns:
            view = view[view["company"] == filter_company]

    st.write(f"Showing {len(view)} / {len(cleaned)} rows")
    display_cols = [c for c in view.columns if c not in {
        "duplicate_group_id", "is_duplicate",
        "missing_name", "missing_email", "missing_title", "missing_company",
    }]
    st.dataframe(view[display_cols].head(50), use_container_width=True)

    # ── Apply and export ────────────────────────────────────
    st.subheader("Apply and export")
    include_all = st.checkbox(
        "Include all rows (including invalid email / excluded)",
        key="export_include_all",
    )
    if st.button("Apply: save contacts_clean.csv", type="primary", key="btn_save_clean"):
        out_path = save_cleaned(cleaned, include_all=include_all)
        save_report(report)
        st.session_state["contacts_clean"] = cleaned
        st.session_state["contacts_clean_path"] = str(out_path)
        st.success(f"Saved to `{out_path}`.")

    st.caption("Download")
    dl1, dl2, dl3, dl4 = st.columns(4)
    dl1.download_button(
        "CSV (filtered)", cleaned_csv_bytes(cleaned, include_all),
        file_name="contacts_clean.csv", mime="text/csv", key="dl_csv",
    )
    dl2.download_button(
        "XLSX (filtered)", cleaned_xlsx_bytes(cleaned, include_all),
        file_name="contacts_clean.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_xlsx",
    )
    dl3.download_button(
        "Report CSV", report_csv_bytes(report),
        file_name="quality_report.csv", mime="text/csv", key="dl_rpt_csv",
    )
    dl4.download_button(
        "Report XLSX", report_xlsx_bytes(report, probs),
        file_name="quality_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="dl_rpt_xlsx",
    )
