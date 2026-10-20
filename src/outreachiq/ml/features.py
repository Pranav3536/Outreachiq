"""Text features for ML title classification.

Pipeline: normalize -> TF-IDF word (1-2 grams) + char n-grams (2-4).
Both vectorizers are combined with FeatureUnion. This module only handles
feature construction; no model state lives here.
"""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import FeatureUnion

from ..data.designation import normalize_title


def _normalizer(title: str) -> str:
    """Wrapper for use inside TfidfVectorizer with analyzer='word'."""
    return normalize_title(title)


def build_feature_union() -> FeatureUnion:
    """Return an unfitted FeatureUnion of word and char TF-IDF vectorizers."""
    word_tfidf = TfidfVectorizer(
        analyzer="word",
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
        preprocessor=_normalizer,
        token_pattern=r"(?u)\b[a-zA-Z]\w*\b",
    )
    char_tfidf = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        sublinear_tf=True,
        min_df=1,
        preprocessor=_normalizer,
    )
    return FeatureUnion([("word", word_tfidf), ("char", char_tfidf)])
