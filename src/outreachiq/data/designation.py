"""Rule-based designation categorization (no ML).

Normalizes a job title (lowercase, strip punctuation, expand common
abbreviations) and maps it to a category using keyword rules. The original
title is always kept; a title_category column is added.

CATEGORY_RULES is a plain dict at the top so you can edit it. Matching is
first-match-wins in dict insertion order; rows matching no rule fall back to
"Other/Unknown". Don't assume every category appears in the data.
"""
from __future__ import annotations

import re

import pandas as pd

CATEGORIES = [
    "Founder/CEO/Owner",
    "Talent Acquisition",
    "HR/Recruiting",
    "Director/Head",
    "Manager",
    "Other/Unknown",
]

# category -> keyword patterns (lowercase, alnum-only). First match wins.
CATEGORY_RULES: dict[str, list[str]] = {
    "Founder/CEO/Owner": [
        "founder", "cofounder", "ceo", "chiefexecutiveofficer",
        "owner", "proprietor",
    ],
    "Talent Acquisition": [
        "talentacquisition", "talent", "sourcer", "sourcing",
    ],
    "HR/Recruiting": [
        "humanresources", "humanresource", "hr", "recruiter",
        "recruiting", "recruitment", "peopleops",
    ],
    "Director/Head": [
        "director", "head", "vp", "vicepresident",
    ],
    "Manager": [
        "manager", "mgr", "supervisor", "teamlead",
    ],
}

# Whole-word abbreviation expansion (applied before matching).
_ABBREVIATIONS = {
    "hr": "human resources",
    "ta": "talent acquisition",
    "sr": "senior",
    "jr": "junior",
    "mgr": "manager",
    "vp": "vice president",
    "ceo": "chief executive officer",
    "cto": "chief technology officer",
    "coo": "chief operating officer",
    "chro": "chief human resources officer",
}


def normalize_title(value) -> str:
    """Lowercase, strip punctuation, collapse spaces, expand abbreviations."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = [_ABBREVIATIONS.get(tok, tok) for tok in s.split()]
    return " ".join(tokens)


def _match_key(normalized_title: str) -> str:
    key = re.sub(r"\s+", "", normalized_title)  # alnum only
    if not key:
        return "Other/Unknown"
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw and kw in key:
                return category
    return "Other/Unknown"


def categorize_title(value) -> str:
    """Return the category for a single title."""
    return _match_key(normalize_title(value))


def categorize(df: pd.DataFrame, title_col: str = "title") -> pd.DataFrame:
    """Add a title_category column. The original title column is never modified."""
    out = df.copy()
    if title_col not in out.columns:
        out["title_category"] = "Other/Unknown"
        return out
    out["title_category"] = out[title_col].apply(categorize_title)
    return out
