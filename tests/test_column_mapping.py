"""Tests for column mapping: alternate headers, ambiguity, extra columns.

Uses synthetic dataframes and the synthetic sample_data/ files only.
"""
from __future__ import annotations

import pandas as pd

from outreachiq.config import PROJECT_ROOT
from outreachiq.data.column_mapping import (
    CANONICAL_FIELDS,
    apply_mapping,
    suggest_mapping,
)
from outreachiq.data.loader import load_dataframe

SAMPLE_DATA = PROJECT_ROOT / "sample_data"


def test_canonical_fields():
    assert CANONICAL_FIELDS == ("name", "email", "title", "company")


def test_alternate_headers_map_with_high_confidence():
    df = pd.DataFrame({
        "Full Name": ["Alice", "Bob"],
        "E-mail": ["alice@example.com", "bob@example.com"],
        "Designation": ["Engineer", "Analyst"],
        "Organisation": ["Acme", "Beta"],
    })
    result = suggest_mapping(df)
    by_field = result.as_dict()
    assert by_field["name"].suggested_column == "Full Name"
    assert by_field["name"].confidence == "high"
    assert by_field["email"].suggested_column == "E-mail"
    assert by_field["email"].confidence == "high"
    assert by_field["title"].suggested_column == "Designation"
    assert by_field["title"].confidence == "high"
    assert by_field["company"].suggested_column == "Organisation"
    assert by_field["company"].confidence == "high"
    assert all(not s.needs_confirmation for s in result.suggestions)


def test_ambiguous_email_mapping_is_flagged():
    # Two columns both match an email alias -> tie -> needs confirmation.
    df = pd.DataFrame({
        "Email": ["a@example.com", "b@example.com"],
        "Email Address": ["x@example.com", "y@example.com"],
        "Name": ["A", "B"],
        "Company": ["Acme", "Beta"],
    })
    result = suggest_mapping(df)
    email_s = result.as_dict()["email"]
    assert email_s.needs_confirmation is True


def test_missing_field_is_flagged():
    df = pd.DataFrame({
        "Name": ["Alice"],
        "Email": ["alice@example.com"],
        "Title": ["Engineer"],
        # no company column
    })
    result = suggest_mapping(df)
    company_s = result.as_dict()["company"]
    assert company_s.suggested_column is None
    assert company_s.needs_confirmation is True


def test_extra_columns_preserved_in_mapping_result():
    df = pd.DataFrame({
        "Name": ["Alice"],
        "Email": ["alice@example.com"],
        "Title": ["Engineer"],
        "Company": ["Acme"],
        "Phone": ["555"],
        "Notes": ["met"],
    })
    result = suggest_mapping(df)
    assert set(result.extra_columns) == {"Phone", "Notes"}


def test_apply_mapping_renames_and_preserves_extras():
    df = pd.DataFrame({
        "Full Name": ["Alice"],
        "E-mail": ["alice@example.com"],
        "Designation": ["Engineer"],
        "Organisation": ["Acme"],
        "Phone": ["555"],
    })
    mapping = {
        "name": "Full Name", "email": "E-mail",
        "title": "Designation", "company": "Organisation",
    }
    mapped = apply_mapping(df, mapping)
    # Canonical names first
    assert list(mapped.columns)[:4] == ["name", "email", "title", "company"]
    # Extra preserved
    assert "Phone" in mapped.columns
    assert mapped.iloc[0]["email"] == "alice@example.com"
    # Original df untouched
    assert "Full Name" in df.columns


def test_value_based_email_detection():
    # A column with no email-like header but email values.
    df = pd.DataFrame({
        "Name": ["Alice", "Bob", "Carol"],
        "Info": ["alice@example.com", "bob@example.com", "carol@example.com"],
        "Company": ["Acme", "Beta", "Gamma"],
        "Title": ["Eng", "Analyst", "PM"],
    })
    result = suggest_mapping(df)
    email_s = result.as_dict()["email"]
    assert email_s.suggested_column == "Info"
    # Value-based match is medium confidence -> needs confirmation
    assert email_s.needs_confirmation is True


def test_sample_messy_maps_cleanly():
    df = load_dataframe(SAMPLE_DATA / "contacts_messy.csv")
    result = suggest_mapping(df)
    by_field = result.as_dict()
    assert by_field["name"].suggested_column == "Full Name"
    assert by_field["name"].confidence == "high"
    assert by_field["email"].suggested_column == "E-mail"
    assert by_field["title"].suggested_column == "Designation"
    assert by_field["company"].suggested_column == "Organisation"
    # extras preserved
    assert set(result.extra_columns) == {"Phone", "Notes"}


def test_sample_alt_names_maps_cleanly():
    df = load_dataframe(SAMPLE_DATA / "contacts_alt_names.csv")
    result = suggest_mapping(df)
    by_field = result.as_dict()
    assert by_field["email"].suggested_column == "Email Address"
    assert by_field["title"].suggested_column == "Job Title"
    assert by_field["company"].suggested_column == "Company Name"
    assert by_field["name"].suggested_column == "Contact Name"
    assert all(not s.needs_confirmation for s in result.suggestions)
