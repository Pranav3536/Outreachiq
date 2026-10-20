"""Non-destructive cleaning: trim, collapse spaces, and fix casing into NEW columns.

Original columns are always kept. Returns a per-column change summary counting
how many rows actually changed for each cleaned field.
"""
from __future__ import annotations

import re

import pandas as pd


def _collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _title_case(s: str) -> str:
    """Capitalize the first letter of each whitespace-separated token."""
    return " ".join(w.capitalize() for w in s.split())


def clean_name(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return _title_case(_collapse_spaces(str(value)))


def clean_company(value) -> str:
    if value is None or pd.isna(value):
        return ""
    return _title_case(_collapse_spaces(str(value)))


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Add name_clean and company_clean columns (originals kept).

    Returns (df_with_cleaned_columns, change_summary) where change_summary maps
    each cleaned field name to the number of rows that changed.
    """
    out = df.copy()
    summary: dict = {}
    specs = [("name", clean_name), ("company", clean_company)]
    for field, fn in specs:
        if field not in out.columns:
            out[f"{field}_clean"] = ""
            summary[field] = 0
            continue
        orig = out[field]
        cleaned = orig.apply(fn)
        out[f"{field}_clean"] = cleaned
        non_null = orig.notna()
        changed = int(((cleaned.astype(str) != orig.astype(str)) & non_null).sum())
        summary[field] = changed
    return out, summary
