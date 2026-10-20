"""Labelled-data management for ML training.

Categories reuse data.designation.CATEGORIES — no duplication.
Labelled CSVs live in data/labelled/. Columns: title, label.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ..config import LABELLED_DIR
from ..data.designation import CATEGORIES

logger = logging.getLogger(__name__)

LABEL_COLUMNS = ("title", "label")


def _csv_files() -> list[Path]:
    if not LABELLED_DIR.exists():
        return []
    return sorted(LABELLED_DIR.glob("*.csv"))


def load_labelled(path=None) -> pd.DataFrame:
    """Load one labelled CSV, or merge all CSVs in data/labelled/.

    Returns a DataFrame with columns [title, label] deduplicated by title.
    Returns an empty DataFrame if nothing is found.
    """
    if path is not None:
        p = Path(path)
        if not p.exists():
            return pd.DataFrame(columns=list(LABEL_COLUMNS))
        try:
            df = pd.read_csv(p, usecols=list(LABEL_COLUMNS))
        except Exception as exc:
            logger.warning("Could not read %s: %s", p, exc)
            return pd.DataFrame(columns=list(LABEL_COLUMNS))
        return _clean(df)

    files = _csv_files()
    if not files:
        return pd.DataFrame(columns=list(LABEL_COLUMNS))
    parts = []
    for f in files:
        try:
            parts.append(pd.read_csv(f, usecols=list(LABEL_COLUMNS)))
        except Exception as exc:
            logger.warning("Skipping %s: %s", f, exc)
    if not parts:
        return pd.DataFrame(columns=list(LABEL_COLUMNS))
    merged = pd.concat(parts, ignore_index=True)
    return _clean(merged)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["title"] = df["title"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip()
    df = df[df["title"] != ""].drop_duplicates(subset=["title"])
    invalid_labels = ~df["label"].isin(CATEGORIES)
    if invalid_labels.any():
        logger.warning(
            "Dropping %d rows with invalid labels: %s",
            int(invalid_labels.sum()),
            df.loc[invalid_labels, "label"].unique().tolist(),
        )
        df = df[~invalid_labels]
    return df.reset_index(drop=True)


def append_labels(new_rows: list[dict], dest_path: Path) -> None:
    """Append reviewed label rows to a CSV file. Creates the file if needed.

    Each dict must have 'title' and 'label' keys. Only valid labels accepted.
    """
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        r for r in new_rows
        if r.get("label") in CATEGORIES and str(r.get("title", "")).strip()
    ]
    if not rows:
        return
    new_df = pd.DataFrame(rows, columns=list(LABEL_COLUMNS))
    if dest_path.exists():
        existing = pd.read_csv(dest_path, usecols=list(LABEL_COLUMNS))
        combined = pd.concat([existing, new_df], ignore_index=True).drop_duplicates(
            subset=["title"]
        )
    else:
        combined = new_df
    combined.to_csv(dest_path, index=False)


def export_labels(df: pd.DataFrame, dest_path: Path) -> None:
    """Write a labelled DataFrame to CSV."""
    dest_path = Path(dest_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    df[list(LABEL_COLUMNS)].to_csv(dest_path, index=False)
