"""Stratified train/test evaluation. Vectorizer fitted on train split only (no leakage).

Classes with < MIN_CLASS_SAMPLES are excluded from the split with a visible warning.
Returns a plain-dict report so the UI can display it without importing sklearn.
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import StratifiedShuffleSplit

from ..data.designation import CATEGORIES
from .classifier import _build_pipeline
from .labels import _clean

MIN_CLASS_SAMPLES = 5
TEST_SIZE = 0.25
LIMITATIONS_TEXT = (
    "Results are based on a small synthetic dataset and do not represent real "
    "contact data. Per-class scores may be unreliable when a class has few samples. "
    "Use these metrics only as a rough guide, not as ground truth."
)


def evaluate(labelled_df: pd.DataFrame) -> dict:
    """Run stratified evaluation. Returns a report dict.

    Keys: macro_f1, per_class (dict of class -> {precision, recall, f1, support}),
    confusion_matrix (2-D list), class_names (list), class_distribution (dict),
    limitations (str), warnings (list of str), train_size, test_size.
    """
    df = _clean(labelled_df.copy())
    report_warnings: list[str] = []

    # Class distribution before filtering
    dist_all = df["label"].value_counts().to_dict()

    # Filter classes below threshold
    small_classes = [c for c, n in dist_all.items() if n < MIN_CLASS_SAMPLES]
    if small_classes:
        msg = (
            f"Classes with fewer than {MIN_CLASS_SAMPLES} samples excluded from "
            f"stratified split: {small_classes}. Add more labelled examples."
        )
        warnings.warn(msg, UserWarning, stacklevel=2)
        report_warnings.append(msg)
        df = df[~df["label"].isin(small_classes)]

    if len(df) < 4 or df["label"].nunique() < 2:
        return {
            "macro_f1": None,
            "per_class": {},
            "confusion_matrix": [],
            "class_names": [],
            "class_distribution": dist_all,
            "limitations": LIMITATIONS_TEXT,
            "warnings": report_warnings + ["Not enough data to evaluate."],
            "train_size": 0,
            "test_size": 0,
        }

    X = df["title"].astype(str).to_numpy()
    y = df["label"].astype(str).to_numpy()

    splitter = StratifiedShuffleSplit(n_splits=1, test_size=TEST_SIZE, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y))

    X_train, X_test = X[train_idx].tolist(), X[test_idx].tolist()
    y_train, y_test = y[train_idx].tolist(), y[test_idx].tolist()

    # Fit pipeline on train only — vectorizer never sees test data.
    pipe = _build_pipeline()
    pipe.fit(X_train, y_train)
    y_pred = pipe.predict(X_test)

    class_names = sorted(set(y_test) | set(y_pred))
    cm = confusion_matrix(y_test, y_pred, labels=class_names).tolist()

    cr = classification_report(
        y_test, y_pred, labels=class_names, output_dict=True, zero_division=0
    )
    per_class = {
        c: {
            "precision": round(cr[c]["precision"], 3),
            "recall": round(cr[c]["recall"], 3),
            "f1": round(cr[c]["f1-score"], 3),
            "support": int(cr[c]["support"]),
        }
        for c in class_names
        if c in cr
    }
    macro_f1 = round(
        f1_score(y_test, y_pred, average="macro", labels=class_names, zero_division=0), 3
    )

    return {
        "macro_f1": macro_f1,
        "per_class": per_class,
        "confusion_matrix": cm,
        "class_names": class_names,
        "class_distribution": dist_all,
        "limitations": LIMITATIONS_TEXT,
        "warnings": report_warnings,
        "train_size": len(X_train),
        "test_size": len(X_test),
    }
