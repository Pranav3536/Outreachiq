"""Phase 2b tests: validation, cleaning, duplicates, export, reports (synthetic)."""
from __future__ import annotations

import io

import pandas as pd
import pytest

from outreachiq.data.cleaning import clean
from outreachiq.data.duplicates import apply_exclude, detect
from outreachiq.data.export import (
    cleaned_csv_bytes, cleaned_subset, cleaned_xlsx_bytes, report_csv_bytes,
)
from outreachiq.data.quality_report import build_report, problem_rows
from outreachiq.data.validation import email_clean, email_issue, email_valid, validate


@pytest.fixture
def sample():
    return pd.DataFrame({
        "name": ["  Alice  Johnson ", "Bob", "", "Alice Johnson", "Carol"],
        "email": ["alice@example.com", "bob@bad", "", "alice@example.com", "carol@example.com"],
        "title": ["Engineer", "Analyst", "PM", "Engineer", ""],
        "company": ["ACME CORP", "beta llc", "Gamma", "ACME CORP", "delta"],
    })


def _pipeline(df, decision=None):
    df = validate(df)
    df, _ = clean(df)
    df = detect(df)
    if decision is not None:
        df = apply_exclude(df, {1: decision})
    return df


def test_email_valid_invalid():
    assert email_valid("alice@example.com") is True
    assert email_valid("bob@bad") is False
    assert email_valid("") is False
    assert email_valid(None) is False
    assert email_valid("notanemail") is False


def test_email_clean_and_issue():
    assert email_clean("  Alice@Example.com ") == "alice@example.com"
    assert email_clean(None) == ""
    assert email_clean("") == ""
    assert email_issue("alice@example.com") == ""
    assert "missing" in email_issue("")


def test_validate_missing_flags(sample):
    df = validate(sample)
    assert list(df["email_valid"]) == [True, False, False, True, True]
    assert list(df["missing_name"]) == [False, False, True, False, False]
    assert list(df["missing_email"]) == [False, False, True, False, False]
    assert list(df["missing_title"]) == [False, False, False, False, True]
    assert list(df["missing_company"]) == [False, False, False, False, False]


def test_cleaning_keeps_originals(sample):
    cleaned, summary = clean(sample)
    assert cleaned["name"].iloc[0] == "  Alice  Johnson "  # original unchanged
    assert cleaned["name_clean"].iloc[0] == "Alice Johnson"
    assert cleaned["company_clean"].iloc[0] == "Acme Corp"
    assert cleaned["company"].iloc[0] == "ACME CORP"
    assert summary["name"] >= 1
    assert summary["company"] >= 1


def test_duplicates_detection(sample):
    df = _pipeline(sample)
    assert list(df["is_duplicate"]) == [False, False, False, True, False]
    assert list(df["duplicate_group_id"]) == [1, 0, 0, 1, 0]


def test_exclude_flag_keep_first(sample):
    df = _pipeline(sample, decision="keep_first")
    assert int(df["excluded"].sum()) == 1
    assert df["excluded"].iloc[3] == True
    assert df["excluded"].iloc[0] == False


def test_exclude_flag_exclude_all_in_group(sample):
    df = _pipeline(sample, decision="exclude")
    assert int(df["excluded"].sum()) == 2
    assert df["excluded"].iloc[0] == True
    assert df["excluded"].iloc[3] == True


def test_exclude_flag_keep_all(sample):
    df = _pipeline(sample, decision="keep_all")
    assert int(df["excluded"].sum()) == 0


def test_no_rows_auto_deleted(sample):
    n = len(sample)
    assert len(_pipeline(sample, decision="keep_first")) == n
    assert len(_pipeline(sample, decision="exclude")) == n


def test_export_contents_default(sample):
    df = _pipeline(sample, decision="keep_first")
    subset = cleaned_subset(df, include_all=False)
    assert len(subset) == 2
    emails = subset["email_clean"].tolist()
    assert "alice@example.com" in emails
    assert "carol@example.com" in emails
    assert "bob@bad" not in emails


def test_export_contents_include_all(sample):
    df = _pipeline(sample, decision="keep_first")
    subset = cleaned_subset(df, include_all=True)
    assert len(subset) == 5
    assert "email_valid" not in subset.columns  # internal flags dropped
    assert "excluded" not in subset.columns
    assert "name_clean" in subset.columns  # data + cleaned kept


def test_export_csv_bytes(sample):
    df = _pipeline(sample, decision="keep_first")
    b = cleaned_csv_bytes(df, include_all=False)
    assert b.startswith(b"name,email,title,company")
    text = b.decode("utf-8")
    assert "carol@example.com" in text
    assert "bob@bad" not in text


def test_export_xlsx_bytes(sample):
    df = _pipeline(sample, decision="keep_first")
    b = cleaned_xlsx_bytes(df, include_all=False)
    assert b[:2] == b"PK"  # xlsx is a ZIP
    df2 = pd.read_excel(io.BytesIO(b), engine="openpyxl")
    assert len(df2) == 2


def test_report_counts(sample):
    df = _pipeline(sample, decision="keep_first")
    report = build_report(df)
    assert report["total_rows"] == 5
    assert report["valid_emails"] == 3
    assert report["invalid_emails"] == 2
    assert report["duplicate_rows"] == 1
    assert report["duplicate_groups"] == 1
    assert report["excluded_rows"] == 1
    assert report["unique_companies"] == 4
    assert report["missing"]["name"] == 1
    assert report["missing"]["email"] == 1
    assert report["missing"]["title"] == 1
    assert report["missing"]["company"] == 0


def test_problem_rows(sample):
    df = _pipeline(sample)
    probs = problem_rows(df)
    # rows 1 (invalid email), 2 (missing name+email), 3 (duplicate), 4 (missing title)
    assert len(probs) == 4


def test_report_csv_bytes(sample):
    df = _pipeline(sample)
    report = build_report(df)
    text = report_csv_bytes(report).decode("utf-8")
    assert "Total rows" in text
    assert "Valid emails" in text


def test_dirty_sample_loads_and_runs():
    """End-to-end on the synthetic dirty sample file."""
    from outreachiq.config import PROJECT_ROOT
    from outreachiq.data.column_mapping import apply_mapping, suggest_mapping
    from outreachiq.data.loader import load_dataframe

    df = load_dataframe(PROJECT_ROOT / "sample_data" / "contacts_dirty.csv")
    result = suggest_mapping(df)
    mapping = {s.canonical: s.suggested_column for s in result.suggestions}
    mapped = apply_mapping(df, mapping)
    assert "name" in mapped.columns and "email" in mapped.columns

    df = _pipeline(mapped)
    assert len(df) == len(mapped)  # no rows deleted
    report = build_report(df)
    assert report["total_rows"] == len(mapped)
    assert report["invalid_emails"] >= 3
    assert report["duplicate_rows"] >= 2
