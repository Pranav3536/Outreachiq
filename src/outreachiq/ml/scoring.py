"""Explainable priority scoring (0-100). Never called a response or hiring probability.

SCORE_WEIGHTS at the top of the file is a plain dict so the user can edit it.
Each contact gets a numeric priority_score and a human-readable reasons list.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..data.designation import CATEGORIES

# Edit these weights to tune the priority score.
SCORE_WEIGHTS: dict = {
    # Category relevance: category -> base score (0-40)
    "category_relevance": {
        "Talent Acquisition": 40,
        "HR/Recruiting": 35,
        "Director/Head": 30,
        "Founder/CEO/Owner": 28,
        "Manager": 20,
        "Other/Unknown": 5,
    },
    # Bonus for having a valid email (required for sending)
    "valid_email_bonus": 30,
    # Penalties for missing canonical fields (applied cumulatively)
    "missing_field_penalty": {
        "name": -5,
        "title": -5,
        "company": -5,
        "email": -20,
    },
    # Penalty if flagged as an excluded duplicate
    "excluded_penalty": -30,
}


@dataclass
class ScoredContact:
    index: int
    name: str
    email: str
    title: str
    company: str
    title_category: str
    priority_score: int
    reasons: list[str] = field(default_factory=list)


def score_contacts(df: pd.DataFrame) -> list[ScoredContact]:
    """Return a ScoredContact for every row. Score is always clamped to [0, 100]."""
    results = []
    for idx, row in df.iterrows():
        score = 0
        reasons: list[str] = []

        cat = str(row.get("title_category", "Other/Unknown"))
        cat_score = SCORE_WEIGHTS["category_relevance"].get(cat, 5)
        score += cat_score
        reasons.append(f"Category '{cat}': +{cat_score}")

        email_valid = row.get("email_valid")
        if email_valid is True or str(email_valid).lower() == "true":
            bonus = SCORE_WEIGHTS["valid_email_bonus"]
            score += bonus
            reasons.append(f"Valid email: +{bonus}")
        else:
            penalty = SCORE_WEIGHTS["missing_field_penalty"].get("email", -20)
            score += penalty
            reasons.append(f"Invalid/missing email: {penalty}")

        for field_name in ("name", "title", "company"):
            missing_col = f"missing_{field_name}"
            missing = row.get(missing_col)
            if missing is True or str(missing).lower() == "true":
                penalty = SCORE_WEIGHTS["missing_field_penalty"].get(field_name, -5)
                score += penalty
                reasons.append(f"Missing {field_name}: {penalty}")

        excluded = row.get("excluded")
        if excluded is True or str(excluded).lower() == "true":
            penalty = SCORE_WEIGHTS["excluded_penalty"]
            score += penalty
            reasons.append(f"Excluded duplicate: {penalty}")

        score = max(0, min(100, score))
        results.append(ScoredContact(
            index=int(idx),
            name=str(row.get("name_clean") or row.get("name", "")),
            email=str(row.get("email_clean") or row.get("email", "")),
            title=str(row.get("title", "")),
            company=str(row.get("company_clean") or row.get("company", "")),
            title_category=cat,
            priority_score=score,
            reasons=reasons,
        ))
    return results


def scores_to_dataframe(scored: list[ScoredContact]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "name": s.name,
            "email": s.email,
            "title": s.title,
            "company": s.company,
            "title_category": s.title_category,
            "priority_score": s.priority_score,
            "reasons": " | ".join(s.reasons),
        }
        for s in scored
    ])
