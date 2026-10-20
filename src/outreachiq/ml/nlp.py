"""Token frequency analysis for job titles.

Small built-in stopword list; no external NLP libraries.
Returns top keywords per category and overall.
"""
from __future__ import annotations

import re
from collections import Counter

import pandas as pd

from ..data.designation import CATEGORIES

_STOPWORDS = frozenset({
    "of", "and", "the", "a", "an", "in", "at", "for", "to", "with",
    "by", "on", "or", "is", "amp", "sr", "jr", "senior", "junior",
    "associate", "assistant", "specialist", "executive", "lead", "head",
})


def _tokenize(text: str) -> list[str]:
    text = re.sub(r"[^a-z0-9\s]", " ", str(text).lower())
    return [t for t in text.split() if t not in _STOPWORDS and len(t) >= 2]


def token_frequency(titles: list[str]) -> Counter:
    """Overall token frequency across all titles."""
    counts: Counter = Counter()
    for t in titles:
        counts.update(_tokenize(t))
    return counts


def top_keywords_per_category(
    df: pd.DataFrame,
    title_col: str = "title",
    category_col: str = "title_category",
    top_n: int = 10,
) -> dict[str, list[tuple[str, int]]]:
    """Return {category: [(token, count), ...]} for each category present."""
    result: dict = {}
    if title_col not in df.columns or category_col not in df.columns:
        return result
    for cat in CATEGORIES:
        subset = df[df[category_col] == cat][title_col].astype(str).tolist()
        if not subset:
            continue
        counter = token_frequency(subset)
        result[cat] = counter.most_common(top_n)
    return result
