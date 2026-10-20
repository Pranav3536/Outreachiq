"""Email and field validation. Syntax-only (no DNS), never deletes rows.

Adds helper columns to a dataframe: email_clean, email_valid, email_issue, and
missing_<field> for each canonical field. Original columns are never modified.
"""
from __future__ import annotations

import pandas as pd
from email_validator import EmailNotValidError, validate_email

from .column_mapping import CANONICAL_FIELDS


def email_clean(value) -> str:
    """Trim and lowercase an email. Returns '' for missing/NaN. Strips mailto:."""
    if value is None or pd.isna(value):
        return ""
    s = str(value).strip().lower()
    if s.startswith("mailto:"):
        s = s[len("mailto:"):]
    return s.strip()


def email_valid(value) -> bool:
    """True if the email passes syntax validation (no deliverability check)."""
    s = email_clean(value)
    if not s:
        return False
    try:
        validate_email(s, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def email_issue(value) -> str:
    """Return '' if valid, else a short human-readable reason."""
    if value is None or pd.isna(value) or str(value).strip() == "":
        return "missing email"
    s = email_clean(value)
    try:
        validate_email(s, check_deliverability=False)
        return ""
    except EmailNotValidError as exc:
        return str(getattr(exc, "message", exc))


def _is_missing(value) -> bool:
    if value is None or pd.isna(value):
        return True
    return str(value).strip() == ""


def validate(df: pd.DataFrame) -> pd.DataFrame:
    """Add validation columns. Never deletes rows.

    Adds: email_clean, email_valid, email_issue, and missing_<field> for each
    canonical field (name, email, title, company).
    """
    out = df.copy()
    if "email" in out.columns:
        out["email_clean"] = out["email"].apply(email_clean)
        out["email_valid"] = out["email"].apply(email_valid)
        out["email_issue"] = out["email"].apply(email_issue)
    else:
        out["email_clean"] = ""
        out["email_valid"] = False
        out["email_issue"] = "no email column"
    for field in CANONICAL_FIELDS:
        if field in out.columns:
            out[f"missing_{field}"] = out[field].apply(_is_missing)
        else:
            out[f"missing_{field}"] = True
    return out
