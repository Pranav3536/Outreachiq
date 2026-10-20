"""Title classifier: TF-IDF + LogisticRegression with rule-based fallback.

- train(labelled_df) -> saves pipeline to runtime/models/title_classifier.joblib
- predict(titles) -> list of PredictionResult
- Confidence below CONF_THRESHOLD is flagged needs_review=True
- If no trained model exists, falls back to rules and marks source="rule"
- Never presents an untrained model as if it were working
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from ..config import MODELS_DIR
from ..data.designation import CATEGORIES, categorize_title
from .features import build_feature_union

logger = logging.getLogger(__name__)

MODEL_PATH = MODELS_DIR / "title_classifier.joblib"
CONF_THRESHOLD: float = 0.6


@dataclass
class PredictionResult:
    title: str
    category: str
    confidence: float
    source: str          # "model" or "rule"
    needs_review: bool
    all_probs: dict = field(default_factory=dict)


def _build_pipeline() -> Pipeline:
    return Pipeline([
        ("features", build_feature_union()),
        ("clf", LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            solver="lbfgs",
            C=1.0,
        )),
    ])


def train(labelled_df: pd.DataFrame) -> Path:
    """Fit a new pipeline on labelled_df and save it to runtime/models/.

    Returns the path to the saved model file. Never overwrites a model
    silently if labelled_df has fewer than 2 classes.
    """
    df = labelled_df.copy()
    df = df[df["title"].astype(str).str.strip() != ""]
    df = df[df["label"].isin(CATEGORIES)]
    if len(df) < 2:
        raise ValueError("Need at least 2 labelled rows to train.")
    if df["label"].nunique() < 2:
        raise ValueError("Need at least 2 distinct categories to train.")

    X = df["title"].astype(str).tolist()
    y = df["label"].astype(str).tolist()

    pipe = _build_pipeline()
    pipe.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": pipe, "classes": pipe.classes_.tolist()}, MODEL_PATH)
    logger.info("Model saved to %s", MODEL_PATH)
    return MODEL_PATH


def _load_model() -> dict | None:
    if not MODEL_PATH.exists():
        return None
    try:
        return joblib.load(MODEL_PATH)
    except Exception as exc:
        logger.warning("Could not load model from %s: %s", MODEL_PATH, exc)
        return None


def predict(titles: list[str], threshold: float = CONF_THRESHOLD) -> list[PredictionResult]:
    """Predict category for each title. Falls back to rules if no model."""
    model_data = _load_model()

    if model_data is None:
        # Rule-based fallback; never pretend a model is working.
        return [
            PredictionResult(
                title=t,
                category=categorize_title(t),
                confidence=1.0,
                source="rule",
                needs_review=False,
            )
            for t in titles
        ]

    pipe: Pipeline = model_data["pipeline"]
    classes: list = model_data["classes"]

    proba = pipe.predict_proba(titles)
    results = []
    for t, prob_row in zip(titles, proba):
        idx = prob_row.argmax()
        cat = classes[idx]
        conf = float(prob_row[idx])
        results.append(PredictionResult(
            title=t,
            category=cat,
            confidence=conf,
            source="model",
            needs_review=conf < threshold,
            all_probs={c: round(float(p), 4) for c, p in zip(classes, prob_row)},
        ))
    return results
