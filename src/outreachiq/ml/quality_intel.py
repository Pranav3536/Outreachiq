"""ML-layer data quality summary: reuses existing data-quality functions.

Adds low-confidence classification count to the standard quality report.
"""
from __future__ import annotations

import pandas as pd

from ..data.quality_report import build_report, problem_rows


def ml_quality_summary(
    df: pd.DataFrame,
    predictions=None,
    conf_threshold: float = 0.6,
) -> dict:
    """Merge data-quality report with ML classification quality stats.

    predictions: optional list of PredictionResult from classifier.predict().
    """
    base = build_report(df)
    low_conf = 0
    needs_review = 0
    if predictions:
        low_conf = sum(1 for p in predictions if p.confidence < conf_threshold)
        needs_review = sum(1 for p in predictions if p.needs_review)
    base["low_confidence_classifications"] = low_conf
    base["needs_review_classifications"] = needs_review
    return base
