"""Tests for the dataset loader: CSV/XLSX loading, malformed files, upload integrity.

All fixtures are synthetic and written to tmp_path. No real HR files are read.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from outreachiq.data import column_mapping as cm_mod
from outreachiq.data import loader as loader_mod
from outreachiq.data.loader import (
    SUPPORTED_EXTENSIONS,
    LoaderError,
    load_dataframe,
    save_upload,
)


def _write_csv(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_load_csv(tmp_path):
    csv = _write_csv(
        tmp_path / "contacts.csv",
        "name,email,title,company\n"
        "Alice,alice@example.com,Engineer,Acme\n"
        "Bob,bob@example.com,Analyst,Beta\n",
    )
    df = load_dataframe(csv)
    assert list(df.columns) == ["name", "email", "title", "company"]
    assert len(df) == 2
    assert df.iloc[0]["email"] == "alice@example.com"


def test_load_xlsx(tmp_path):
    xlsx = tmp_path / "contacts.xlsx"
    pd.DataFrame({
        "name": ["Alice", "Bob"],
        "email": ["alice@example.com", "bob@example.com"],
        "title": ["Engineer", "Analyst"],
        "company": ["Acme", "Beta"],
    }).to_excel(xlsx, index=False, engine="openpyxl")
    df = load_dataframe(xlsx)
    assert len(df) == 2
    assert list(df.columns)[:4] == ["name", "email", "title", "company"]


def test_empty_csv_raises_loader_error(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    with pytest.raises(LoaderError):
        load_dataframe(empty)


def test_malformed_xlsx_raises_loader_error(tmp_path):
    bad = tmp_path / "fake.xlsx"
    bad.write_bytes(b"this is not really an xlsx file")
    with pytest.raises(LoaderError):
        load_dataframe(bad)


def test_unsupported_extension_raises(tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("hello")
    with pytest.raises(LoaderError):
        load_dataframe(txt)


def test_missing_file_raises(tmp_path):
    with pytest.raises(LoaderError):
        load_dataframe(tmp_path / "doesnotexist.csv")


def test_save_upload_writes_unchanged_bytes(tmp_path, monkeypatch):
    monkeypatch.setattr(loader_mod, "UPLOADS_DIR", tmp_path / "uploads")
    raw = b"name,email\nAlice,alice@example.com\n"
    saved = save_upload("My Contacts.csv", raw)
    assert saved.exists()
    assert saved.read_bytes() == raw  # bytes unchanged
    assert saved.suffix == ".csv"
    assert saved.stem.startswith("My_Contacts")  # timestamped name keeps original stem


def test_preserves_extra_columns(tmp_path):
    csv = _write_csv(
        tmp_path / "c.csv",
        "name,email,title,company,phone,notes\n"
        "Alice,alice@example.com,Engineer,Acme,555,met\n",
    )
    df = load_dataframe(csv)
    assert set(df.columns) == {"name", "email", "title", "company", "phone", "notes"}


def test_original_upload_bytes_unchanged_after_mapping(tmp_path, monkeypatch):
    monkeypatch.setattr(loader_mod, "UPLOADS_DIR", tmp_path / "uploads")
    monkeypatch.setattr(cm_mod, "PROCESSED_DIR", tmp_path / "processed")
    raw = (b"name,email,title,company,phone\n"
           b"Alice,alice@example.com,Engineer,Acme,555\n")
    saved = save_upload("c.csv", raw)
    df = load_dataframe(saved)
    mapped = cm_mod.apply_mapping(
        df, {"name": "name", "email": "email", "title": "title", "company": "company"}
    )
    cm_mod.save_mapped(mapped)
    # The saved upload must still equal the original bytes (never mutated).
    assert saved.read_bytes() == raw


def test_supported_extensions_listed():
    assert ".csv" in SUPPORTED_EXTENSIONS
    assert ".xlsx" in SUPPORTED_EXTENSIONS
    assert ".xls" in SUPPORTED_EXTENSIONS
