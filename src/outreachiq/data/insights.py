"""Insights and aggregations for the Overview Dashboard and Designation Explorer.

All functions are pure (no Streamlit) so they can be unit-tested. They work on
a cleaned contacts dataframe (canonical columns name/email/title/company, plus
the *_clean and validation flag columns from Phase 2b). Flag columns are
re-derived if missing so the functions also work on the exported file.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ..config import CAMPAIGNS_DIR, PROCESSED_DIR
from .column_mapping import CANONICAL_FIELDS
from .designation import categorize
from .duplicates import detect
from .validation import validate

CLEANED_FILE = PROCESSED_DIR / "contacts_clean.csv"


def load_cleaned(path=None):
    """Load contacts_clean.csv. Returns None if the file is missing/unreadable."""
    if path is None:
        path = CLEANED_FILE
    path = Path(path)
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:
        return None


def with_flags(df):
    """Re-derive validation + duplicate flag columns if missing (idempotent)."""
    if df is None or len(df) == 0:
        return df
    df = validate(df)
    df = detect(df)
    return df


def kpis(df) -> dict:
    df = with_flags(df)
    if df is None or len(df) == 0:
        return {
            "total": 0, "valid_emails": 0, "invalid_emails": 0, "duplicates": 0,
            "unique_companies": 0, "contacts_with_missing": 0,
        }
    missing_cols = [f"missing_{f}" for f in CANONICAL_FIELDS if f"missing_{f}" in df.columns]
    cwm = int(df[missing_cols].any(axis=1).sum()) if missing_cols else 0
    return {
        "total": int(len(df)),
        "valid_emails": int(df["email_valid"].astype(bool).sum()) if "email_valid" in df.columns else 0,
        "invalid_emails": int((~df["email_valid"].astype(bool)).sum()) if "email_valid" in df.columns else 0,
        "duplicates": int(df["is_duplicate"].astype(bool).sum()) if "is_duplicate" in df.columns else 0,
        "unique_companies": (
            int(df["company_clean"].replace("", pd.NA).nunique())
            if "company_clean" in df.columns
            else (int(df["company"].nunique()) if "company" in df.columns else 0)
        ),
        "contacts_with_missing": cwm,
    }


def category_counts(df) -> pd.DataFrame:
    """Count contacts per title_category (after applying designation)."""
    df = categorize(df)
    if df is None or len(df) == 0 or "title_category" not in df.columns:
        return pd.DataFrame(columns=["title_category", "count"])
    counts = df["title_category"].value_counts().rename_axis("title_category").reset_index(name="count")
    return counts


def top_companies(df, n: int = 10) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=["company", "count"])
    col = "company_clean" if "company_clean" in df.columns else "company"
    if col not in df.columns:
        return pd.DataFrame(columns=["company", "count"])
    s = df[col].replace("", pd.NA).dropna()
    counts = s.value_counts().head(n).rename_axis("company").reset_index(name="count")
    return counts


def email_status_counts(df) -> dict:
    df = with_flags(df)
    if df is None or len(df) == 0:
        return {"valid": 0, "invalid": 0}
    return {
        "valid": int(df["email_valid"].astype(bool).sum()) if "email_valid" in df.columns else 0,
        "invalid": int((~df["email_valid"].astype(bool)).sum()) if "email_valid" in df.columns else 0,
    }


def missing_per_field(df) -> dict:
    df = with_flags(df)
    if df is None or len(df) == 0:
        return {f: 0 for f in CANONICAL_FIELDS}
    return {f: int(df[f"missing_{f}"].sum()) if f"missing_{f}" in df.columns else 0 for f in CANONICAL_FIELDS}


def distinct_titles(df) -> pd.DataFrame:
    """Distinct original titles with contact counts."""
    if df is None or len(df) == 0 or "title" not in df.columns:
        return pd.DataFrame(columns=["title", "count"])
    s = df["title"].replace("", pd.NA).dropna()
    counts = s.value_counts().rename_axis("title").reset_index(name="count")
    return counts


def eligible_for_campaign(df):
    """Return (eligible_df, n_excluded). Eligible = valid email AND not excluded.

    Never deletes rows from the input; returns a filtered copy plus the count
    of rows that were excluded (invalid email or flagged as excluded duplicate).
    """
    if df is None or len(df) == 0:
        return df, 0
    mask = pd.Series(True, index=df.index)
    if "email_valid" in df.columns:
        mask &= df["email_valid"].astype(bool)
    if "excluded" in df.columns:
        mask &= ~df["excluded"].astype(bool)
    n_excluded = int((~mask).sum())
    return df[mask].copy(), n_excluded


def campaign_history() -> list:
    """Read campaign summary records from runtime/campaigns/*.json. Returns []."""
    if not CAMPAIGNS_DIR.exists():
        return []
    records = []
    for p in sorted(CAMPAIGNS_DIR.glob("*.json")):
        try:
            records.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    return records
