"""Quality report: summary metrics + problem-rows table."""
from __future__ import annotations

import pandas as pd

from .column_mapping import CANONICAL_FIELDS


def build_report(df: pd.DataFrame) -> dict:
    """Return a dict of summary metrics for the (validated) dataframe."""
    report = {
        "total_rows": int(len(df)),
        "valid_emails": int(df["email_valid"].sum()) if "email_valid" in df.columns else 0,
        "invalid_emails": int((~df["email_valid"]).sum()) if "email_valid" in df.columns else 0,
        "missing": {
            f: int(df[f"missing_{f}"].sum())
            for f in CANONICAL_FIELDS if f"missing_{f}" in df.columns
        },
        "duplicate_rows": int(df["is_duplicate"].sum()) if "is_duplicate" in df.columns else 0,
        "duplicate_groups": (
            int(df.loc[df["duplicate_group_id"] > 0, "duplicate_group_id"].nunique())
            if "duplicate_group_id" in df.columns else 0
        ),
        "unique_companies": (
            int(df["company_clean"].replace("", pd.NA).nunique())
            if "company_clean" in df.columns
            else (int(df["company"].nunique()) if "company" in df.columns else 0)
        ),
        "excluded_rows": int(df["excluded"].sum()) if "excluded" in df.columns else 0,
    }
    return report


def problem_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Return rows with any issue: invalid email, missing field, or duplicate."""
    mask = pd.Series(False, index=df.index)
    if "email_valid" in df.columns:
        mask |= ~df["email_valid"].astype(bool)
    for f in CANONICAL_FIELDS:
        col = f"missing_{f}"
        if col in df.columns:
            mask |= df[col].astype(bool)
    if "is_duplicate" in df.columns:
        mask |= df["is_duplicate"].astype(bool)
    return df[mask].copy()
