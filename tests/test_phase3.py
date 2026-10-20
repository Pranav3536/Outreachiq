"""Phase 3 tests: designation rules, insights, selection (synthetic data only)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from outreachiq.data.designation import (
    CATEGORIES,
    CATEGORY_RULES,
    categorize,
    categorize_title,
    normalize_title,
)
from outreachiq.data.insights import (
    category_counts,
    distinct_titles,
    eligible_for_campaign,
    email_status_counts,
    kpis,
    missing_per_field,
    top_companies,
)

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "src" / "outreachiq" / "ui" / "pages"


@pytest.fixture
def contacts():
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Carol", "David", "Eve", "Frank"],
        "email": ["a@ex.com", "b@ex.com", "bad-email", "d@ex.com", "e@ex.com", "f@ex.com"],
        "title": [
            "HR Manager",
            "Talent Acquisition Specialist",
            "CEO & Founder",
            "Software Engineer",
            "Director of Engineering",
            "",
        ],
        "company": ["Acme", "Beta", "Gamma", "Acme", "Delta", "Epsilon"],
    })


# ── designation rules ─────────────────────────────────────────
def test_hr_manager():
    assert categorize_title("HR Manager") == "HR/Recruiting"


def test_talent_acquisition():
    assert categorize_title("Talent Acquisition Specialist") == "Talent Acquisition"


def test_ceo_founder():
    assert categorize_title("CEO & Founder") == "Founder/CEO/Owner"


def test_director():
    assert categorize_title("Director of Engineering") == "Director/Head"


def test_engineer_unknown():
    assert categorize_title("Software Engineer") == "Other/Unknown"


def test_empty_title_unknown():
    assert categorize_title("") == "Other/Unknown"
    assert categorize_title(None) == "Other/Unknown"


def test_abbreviation_expansion():
    assert categorize_title("HR Specialist") == "HR/Recruiting"
    assert categorize_title("VP Sales") == "Director/Head"


def test_original_title_preserved(contacts):
    df = categorize(contacts)
    assert "title" in df.columns
    assert df["title"].iloc[0] == "HR Manager"   # unchanged
    assert "title_category" in df.columns
    assert df["title_category"].iloc[0] == "HR/Recruiting"


def test_category_rules_editable():
    assert "HR/Recruiting" in CATEGORY_RULES
    assert "Talent Acquisition" in CATEGORY_RULES
    assert "Founder/CEO/Owner" in CATEGORY_RULES
    assert "Manager" in CATEGORY_RULES
    assert "Director/Head" in CATEGORY_RULES


def test_all_categories_defined():
    from outreachiq.data.designation import CATEGORIES
    assert "Other/Unknown" in CATEGORIES


# ── insights ─────────────────────────────────────────────────
def test_kpis(contacts):
    k = kpis(contacts)
    assert k["total"] == 6
    assert k["valid_emails"] == 5
    assert k["invalid_emails"] == 1
    assert k["unique_companies"] == 5


def test_top_companies(contacts):
    tc = top_companies(contacts, n=10)
    assert "company" in tc.columns
    # Acme has 2 contacts
    assert tc.loc[tc["company"] == "Acme", "count"].values[0] == 2


def test_email_status_counts(contacts):
    ec = email_status_counts(contacts)
    assert ec["valid"] == 5
    assert ec["invalid"] == 1


def test_missing_per_field(contacts):
    mf = missing_per_field(contacts)
    assert mf["name"] == 0
    assert mf["title"] == 1  # Frank has empty title


def test_category_counts(contacts):
    df = categorize(contacts)
    cc = category_counts(df)
    assert "title_category" in cc.columns
    assert "count" in cc.columns
    assert cc["count"].sum() == len(contacts)


def test_distinct_titles(contacts):
    dt = distinct_titles(contacts)
    assert "title" in dt.columns
    assert "count" in dt.columns
    # Empty string is excluded
    assert "" not in dt["title"].values


def test_eligible_excludes_invalid_and_excluded(contacts):
    from outreachiq.data.validation import validate
    from outreachiq.data.duplicates import detect
    df = validate(contacts)
    df = detect(df)
    df["excluded"] = False
    df.loc[3, "excluded"] = True  # manually exclude David
    elig, n_ex = eligible_for_campaign(df)
    assert "bad-email" not in elig["email"].values   # Carol excluded (invalid)
    assert "David" not in elig["name"].values        # excluded flag
    assert n_ex == 2


def test_eligible_count_no_deletions(contacts):
    n = len(contacts)
    elig, n_ex = eligible_for_campaign(contacts)
    assert len(contacts) == n  # input unchanged


# ── page rendering ────────────────────────────────────────────
def _run(name: str) -> AppTest:
    at = AppTest.from_file(str(PAGES_DIR / name), default_timeout=15)
    at.run()
    return at


def test_overview_renders_without_data():
    at = _run("overview.py")
    assert not at.exception, f"overview.py raised: {at.exception}"
    # With no data: shows info "Load and clean contacts"
    assert len(at.title) >= 1


def test_designation_explorer_renders_without_data():
    at = _run("designation_explorer.py")
    assert not at.exception, f"designation_explorer.py raised: {at.exception}"
    assert len(at.title) >= 1
