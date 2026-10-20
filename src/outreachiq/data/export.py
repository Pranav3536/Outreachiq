"""Export cleaned contacts and quality report to CSV/XLSX and data/processed/.

The cleaned export defaults to rows with a valid email that are not excluded;
set include_all=True to export every row. Internal flag columns are dropped from
the cleaned export; data columns (originals + *_clean + extras) are kept.
"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from ..config import PROCESSED_DIR
from .column_mapping import CANONICAL_FIELDS

# Internal flag columns not included in the cleaned export.
_INTERNAL_COLS = {
    "email_valid", "email_issue", "is_duplicate", "duplicate_group_id", "excluded",
}
_INTERNAL_COLS |= {f"missing_{f}" for f in CANONICAL_FIELDS}


def export_columns(df: pd.DataFrame) -> list:
    """Columns to include in a cleaned export (data + cleaned, drop internal flags)."""
    return [c for c in df.columns if c not in _INTERNAL_COLS]


def cleaned_subset(df: pd.DataFrame, include_all: bool = False) -> pd.DataFrame:
    """Return the rows/columns for export.

    Default: valid email AND not excluded. include_all=True returns all rows.
    """
    cols = export_columns(df)
    if include_all:
        return df[cols].copy()
    mask = pd.Series(True, index=df.index)
    if "email_valid" in df.columns:
        mask &= df["email_valid"].astype(bool)
    if "excluded" in df.columns:
        mask &= ~df["excluded"].astype(bool)
    return df.loc[mask, cols].copy()


def cleaned_csv_bytes(df: pd.DataFrame, include_all: bool = False) -> bytes:
    return cleaned_subset(df, include_all=include_all).to_csv(index=False).encode("utf-8")


def cleaned_xlsx_bytes(df: pd.DataFrame, include_all: bool = False) -> bytes:
    buf = BytesIO()
    cleaned_subset(df, include_all=include_all).to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def save_cleaned(df: pd.DataFrame, path=None, include_all: bool = False) -> Path:
    if path is None:
        path = PROCESSED_DIR / "contacts_clean.csv"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned_subset(df, include_all=include_all).to_csv(path, index=False)
    return path


def report_to_dataframe(report: dict) -> pd.DataFrame:
    """Flatten a report dict into a two-column Metric/Value dataframe."""
    rows = [
        ("Total rows", report["total_rows"]),
        ("Valid emails", report["valid_emails"]),
        ("Invalid emails", report["invalid_emails"]),
    ]
    for f, n in report.get("missing", {}).items():
        rows.append((f"Missing {f}", n))
    rows.append(("Duplicate rows", report["duplicate_rows"]))
    rows.append(("Duplicate groups", report["duplicate_groups"]))
    rows.append(("Unique companies", report["unique_companies"]))
    rows.append(("Excluded rows", report["excluded_rows"]))
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def report_csv_bytes(report: dict) -> bytes:
    return report_to_dataframe(report).to_csv(index=False).encode("utf-8")


def report_xlsx_bytes(report: dict, problems: pd.DataFrame) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        report_to_dataframe(report).to_excel(writer, sheet_name="Summary", index=False)
        if len(problems) > 0:
            problems.to_excel(writer, sheet_name="Problem Rows", index=False)
    return buf.getvalue()


def save_report(report: dict, path=None) -> Path:
    if path is None:
        path = PROCESSED_DIR / "quality_report.csv"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(report_csv_bytes(report))
    return path
