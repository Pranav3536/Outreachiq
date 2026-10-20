"""Suggest mappings from source columns to canonical fields.

Canonical (required) fields: name, email, title, company. All other source
columns are preserved as-is. Suggestions are never silent: any field that is
not a high-confidence, unambiguous match is flagged for the user to confirm.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from ..config import PROCESSED_DIR

CANONICAL_FIELDS = ("name", "email", "title", "company")

# Header aliases per canonical field, normalized (lowercase, alnum only).
_ALIASES = {
    "name": ["name", "fullname", "contactname", "firstname", "contact", "person", "candidate"],
    "email": ["email", "emailaddress", "emailid", "mail"],
    "title": ["title", "designation", "jobtitle", "position", "role", "job"],
    "company": ["company", "organisation", "organization", "employer", "companyname", "firm"],
}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Score gap below which two candidates are considered tied.
_TIE_MARGIN = 10


@dataclass
class FieldSuggestion:
    canonical: str
    suggested_column: Optional[str]
    confidence: str  # "high" | "medium" | "low" | "none"
    reason: str
    needs_confirmation: bool


@dataclass
class MappingResult:
    suggestions: list  # list[FieldSuggestion], ordered by CANONICAL_FIELDS
    extra_columns: list  # source columns not chosen for any canonical field

    def as_dict(self) -> dict:
        return {s.canonical: s for s in self.suggestions}


def _normalize(header) -> str:
    return re.sub(r"[^a-z0-9]", "", str(header).lower())


def _email_fraction(series: pd.Series, sample_size: int = 20) -> float:
    """Fraction of non-null sample values that look like emails."""
    non_null = series.dropna().astype(str).str.strip()
    if len(non_null) == 0:
        return 0.0
    sample = non_null.head(sample_size)
    matches = sum(1 for v in sample if _EMAIL_RE.match(v))
    return matches / len(sample)


def _header_score(normalized_header: str, canonical: str) -> tuple[int, str]:
    aliases = _ALIASES.get(canonical, [])
    if not normalized_header:
        return 0, ""
    if normalized_header in aliases:
        return 100, f"Header matches '{canonical}' exactly."
    for alias in aliases:
        if not alias:
            continue
        # Substring match, but only when the overlapping token is long enough
        # to avoid false positives (e.g., "name" inside "companyname").
        if len(alias) >= 5 and alias in normalized_header:
            return 60, f"Header loosely matches alias '{alias}'."
        if len(normalized_header) >= 5 and normalized_header in alias:
            return 60, f"Header loosely matches alias '{alias}'."
    return 0, ""


def suggest_mapping(df: pd.DataFrame) -> MappingResult:
    """Suggest source-column -> canonical-field mappings for the given dataframe."""
    columns = list(df.columns)
    normalized = {c: _normalize(c) for c in columns}

    suggestions = []
    for canonical in CANONICAL_FIELDS:
        candidates = []
        for col in columns:
            score, reason = _header_score(normalized[col], canonical)
            # Value-based boost for email when the header isn't an exact match.
            if canonical == "email" and score < 100:
                frac = _email_fraction(df[col])
                if frac >= 0.5:
                    value_score = 70
                    if value_score > score:
                        score = value_score
                        reason = f"Column values look like emails ({frac:.0%} match)."
            if score > 0:
                candidates.append((col, score, reason))

        candidates.sort(key=lambda x: x[1], reverse=True)

        if not candidates:
            suggestions.append(FieldSuggestion(
                canonical=canonical,
                suggested_column=None,
                confidence="none",
                reason="No matching column found.",
                needs_confirmation=True,
            ))
            continue

        best_col, best_score, best_reason = candidates[0]
        if best_score >= 100:
            confidence = "high"
        elif best_score >= 70:
            confidence = "medium"
        else:
            confidence = "low"

        tie = False
        if len(candidates) >= 2 and (best_score - candidates[1][1]) < _TIE_MARGIN:
            tie = True
            best_reason += f" Close tie with '{candidates[1][0]}'."

        suggestions.append(FieldSuggestion(
            canonical=canonical,
            suggested_column=best_col,
            confidence=confidence,
            reason=best_reason,
            needs_confirmation=(confidence != "high") or tie,
        ))

    chosen = {s.suggested_column for s in suggestions if s.suggested_column}
    extra = [c for c in columns if c not in chosen]

    return MappingResult(suggestions=suggestions, extra_columns=extra)


def apply_mapping(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Rename chosen source columns to canonical names; keep extras as-is.

    Returns a new dataframe (the original is not modified). Columns are ordered
    with canonical fields first, then preserved extras in original order.
    """
    mapped = df.copy()
    rename = {}
    for canonical, src in mapping.items():
        if src and src in mapped.columns:
            rename[src] = canonical
    mapped = mapped.rename(columns=rename)
    ordered = [f for f in CANONICAL_FIELDS if f in mapped.columns]
    ordered += [c for c in mapped.columns if c not in ordered]
    return mapped[ordered]


def save_mapped(df: pd.DataFrame, path=None) -> Path:
    """Save the mapped dataframe to data/processed/contacts_mapped.csv by default."""
    if path is None:
        path = PROCESSED_DIR / "contacts_mapped.csv"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path
