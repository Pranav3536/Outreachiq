"""Dataset loading: CSV/XLSX via pandas with safe error handling.

The uploaded file's raw bytes are saved unchanged to data/uploads/ under a
timestamped name. Malformed, empty, or unsupported files raise LoaderError with
a clear message instead of crashing. All columns (including extras) are preserved.
"""
from __future__ import annotations

import datetime as _dt
import logging
from pathlib import Path

import pandas as pd

from ..config import UPLOADS_DIR

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (".csv", ".xlsx", ".xls")


class LoaderError(Exception):
    """Raised when a file cannot be loaded. Message is safe to show users."""


def _timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d_%H%M%S")


def save_upload(original_name: str, data: bytes) -> Path:
    """Save raw upload bytes unchanged under data/uploads/ with a timestamped name."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    stem = Path(original_name).stem or "upload"
    safe_stem = "".join(ch if (ch.isalnum() or ch in "-_") else "_" for ch in stem)
    suffix = Path(original_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        suffix = ".bin"
    dest = UPLOADS_DIR / f"{safe_stem}_{_timestamp()}{suffix}"
    counter = 1
    while dest.exists():
        dest = UPLOADS_DIR / f"{safe_stem}_{_timestamp()}_{counter}{suffix}"
        counter += 1
    dest.write_bytes(data)
    logger.info("Saved upload to %s", dest)
    return dest


def load_dataframe(path) -> pd.DataFrame:
    """Load a CSV/XLSX file into a DataFrame. Raises LoaderError on failure."""
    path = Path(path)
    if not path.exists():
        raise LoaderError(f"File not found: {path.name}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise LoaderError(
            f"Unsupported file type '{suffix or '(none)'}'. Please use CSV or XLSX."
        )
    if suffix == ".xls":
        # openpyxl supports .xlsx only; legacy .xls needs re-saving.
        raise LoaderError(
            "Legacy .xls files aren't supported by openpyxl. "
            "Please re-save the file as .xlsx and upload again."
        )
    try:
        if suffix == ".csv":
            try:
                df = pd.read_csv(path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="latin-1")
        else:  # .xlsx
            df = pd.read_excel(path, engine="openpyxl")
    except pd.errors.EmptyDataError:
        raise LoaderError("The file is empty or has no readable columns.")
    except UnicodeDecodeError:
        raise LoaderError("Could not decode the CSV file. Try saving it as UTF-8.")
    except Exception as exc:
        raise LoaderError(f"Could not read {path.name}: {type(exc).__name__}")
    if df is None or len(df.columns) == 0:
        raise LoaderError("No columns found in the file.")
    return df
