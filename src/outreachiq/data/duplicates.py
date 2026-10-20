"""Duplicate detection by email_clean (optionally name+company). Flags only.

Never removes rows. Adds duplicate_group_id and is_duplicate columns. The first
row in each duplicate group is is_duplicate=False; later rows are True. Singleton
rows and rows with an empty key get duplicate_group_id=0.
"""
from __future__ import annotations

import pandas as pd


def detect(df: pd.DataFrame, include_name_company: bool = False) -> pd.DataFrame:
    """Add duplicate_group_id and is_duplicate columns."""
    out = df.copy()
    if include_name_company:
        key_cols = ["name_clean", "company_clean", "email_clean"]
    else:
        key_cols = ["email_clean"]
    for c in key_cols:
        if c not in out.columns:
            out[c] = ""
    key = out[key_cols].astype(str).agg("\x1f".join, axis=1).str.strip().str.lower()
    empty_key = key.apply(lambda v: all(p == "" for p in v.split("\x1f")))
    counts = key.groupby(key, sort=False).transform("size")
    is_first = ~key.duplicated(keep="first")
    out["is_duplicate"] = (~is_first) & (counts > 1) & (~empty_key)
    # Assign sequential ids to multi-member, non-empty groups only.
    dup_keys = key[(counts > 1) & (~empty_key)].drop_duplicates()
    id_map = {g: i + 1 for i, g in enumerate(dup_keys)}
    out["duplicate_group_id"] = key.map(id_map).fillna(0).astype(int)
    return out


def apply_exclude(df: pd.DataFrame, decisions: dict) -> pd.DataFrame:
    """Apply per-group keep/exclude decisions by setting an 'excluded' flag.

    decisions: {group_id: 'keep_first' | 'keep_all' | 'exclude'}.
    Never removes rows. Returns a new dataframe with an 'excluded' bool column.
    """
    out = df.copy()
    if "excluded" not in out.columns:
        out["excluded"] = False
    else:
        out["excluded"] = out["excluded"].astype(bool)
    if "duplicate_group_id" not in out.columns or "is_duplicate" not in out.columns:
        return out
    for gid, decision in decisions.items():
        in_group = out["duplicate_group_id"] == int(gid)
        if decision == "exclude":
            out.loc[in_group, "excluded"] = True
        elif decision == "keep_first":
            out.loc[in_group & (out["is_duplicate"] == True), "excluded"] = True
        # 'keep_all' leaves nothing excluded
    return out
