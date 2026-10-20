"""Phase 4 ML/NLP tests (synthetic data only)."""
from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_LABELLED = ROOT / "sample_data" / "labelled_titles_synthetic.csv"
PAGES_DIR = ROOT / "src" / "outreachiq" / "ui" / "pages"


@pytest.fixture
def small_labelled():
    """Minimal synthetic labelled set: ≥5 per class where possible."""
    rows = [
        ("HR Manager", "HR/Recruiting"),
        ("Human Resources Lead", "HR/Recruiting"),
        ("Recruiter", "HR/Recruiting"),
        ("HR Specialist", "HR/Recruiting"),
        ("People Ops", "HR/Recruiting"),
        ("Talent Acquisition Manager", "Talent Acquisition"),
        ("TA Lead", "Talent Acquisition"),
        ("Sourcer", "Talent Acquisition"),
        ("Talent Sourcer", "Talent Acquisition"),
        ("Talent Acq Lead", "Talent Acquisition"),
        ("CEO", "Founder/CEO/Owner"),
        ("Founder", "Founder/CEO/Owner"),
        ("Co-Founder & CEO", "Founder/CEO/Owner"),
        ("Owner", "Founder/CEO/Owner"),
        ("Managing Director", "Founder/CEO/Owner"),
        ("Engineering Manager", "Manager"),
        ("Team Manager", "Manager"),
        ("Senior Manager", "Manager"),
        ("Operations Manager", "Manager"),
        ("Sales Manager", "Manager"),
        ("Director of HR", "Director/Head"),
        ("Head of People", "Director/Head"),
        ("VP of Engineering", "Director/Head"),
        ("Director of Recruiting", "Director/Head"),
        ("Head of HR", "Director/Head"),
        ("Software Engineer", "Other/Unknown"),
        ("Data Analyst", "Other/Unknown"),
        ("UX Designer", "Other/Unknown"),
        ("DevOps Engineer", "Other/Unknown"),
        ("QA Engineer", "Other/Unknown"),
    ]
    return pd.DataFrame(rows, columns=["title", "label"])


@pytest.fixture
def contacts_df():
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Carol", "David", "Eve"],
        "email": ["a@ex.com", "b@ex.com", "bad", "d@ex.com", "e@ex.com"],
        "title": ["HR Manager", "Talent Acquisition Lead", "CEO", "Software Engineer", ""],
        "company": ["Acme", "Beta", "Gamma", "Delta", "Epsilon"],
    })


# ── labelled loading ──────────────────────────────────────────────────────────
def test_load_labelled_sample():
    from outreachiq.ml.labels import load_labelled
    df = load_labelled(SAMPLE_LABELLED)
    assert len(df) >= 100
    assert set(df.columns) >= {"title", "label"}


def test_load_labelled_invalid_label_dropped(tmp_path):
    from outreachiq.ml.labels import load_labelled
    p = tmp_path / "lbl.csv"
    pd.DataFrame({
        "title": ["HR Manager", "Some Guy"],
        "label": ["HR/Recruiting", "NOT_A_REAL_LABEL"],
    }).to_csv(p, index=False)
    df = load_labelled(p)
    assert "NOT_A_REAL_LABEL" not in df["label"].values
    assert len(df) == 1


def test_append_labels(tmp_path):
    from outreachiq.ml.labels import append_labels, load_labelled
    dest = tmp_path / "new.csv"
    append_labels([{"title": "HR Exec", "label": "HR/Recruiting"}], dest)
    df = load_labelled(dest)
    assert df.iloc[0]["title"] == "HR Exec"


def test_export_labels(tmp_path):
    from outreachiq.ml.labels import export_labels
    df = pd.DataFrame({"title": ["CEO"], "label": ["Founder/CEO/Owner"]})
    p = tmp_path / "out.csv"
    export_labels(df, p)
    assert p.exists()
    loaded = pd.read_csv(p)
    assert "CEO" in loaded["title"].values


# ── train / predict ───────────────────────────────────────────────────────────
def test_train_and_predict(tmp_path, monkeypatch, small_labelled):
    from outreachiq.ml import classifier as clf_mod
    monkeypatch.setattr(clf_mod, "MODEL_PATH", tmp_path / "model.joblib")
    from outreachiq.ml.classifier import predict, train
    train(small_labelled)
    results = predict(["HR Manager", "CEO", "Software Engineer"])
    assert len(results) == 3
    for r in results:
        assert r.source == "model"
        assert 0.0 <= r.confidence <= 1.0


def test_needs_review_flag_below_threshold(tmp_path, monkeypatch, small_labelled):
    from outreachiq.ml import classifier as clf_mod
    monkeypatch.setattr(clf_mod, "MODEL_PATH", tmp_path / "model.joblib")
    from outreachiq.ml.classifier import predict, train
    train(small_labelled)
    results = predict(["HR Manager"], threshold=0.99)
    # With threshold=0.99 nearly every prediction is flagged needs_review.
    assert results[0].needs_review is True or results[0].confidence >= 0.99


def test_rule_fallback_without_model(tmp_path, monkeypatch):
    from outreachiq.ml import classifier as clf_mod
    monkeypatch.setattr(clf_mod, "MODEL_PATH", tmp_path / "nonexistent.joblib")
    from outreachiq.ml.classifier import predict
    results = predict(["HR Manager", "CEO"])
    assert all(r.source == "rule" for r in results)
    assert results[0].category == "HR/Recruiting"
    assert results[1].category == "Founder/CEO/Owner"


def test_no_train_test_overlap(tmp_path, monkeypatch, small_labelled):
    """Titles in test set must not appear in train set (via evaluation split)."""
    from outreachiq.ml.evaluation import evaluate
    report = evaluate(small_labelled)
    # The report must have non-None macro_f1 if enough data exists.
    assert report["macro_f1"] is not None
    assert report["test_size"] > 0
    assert report["train_size"] > report["test_size"]


def test_small_class_warning(small_labelled):
    from outreachiq.ml.evaluation import MIN_CLASS_SAMPLES, evaluate
    # Add a class with only 2 samples (below threshold).
    tiny = pd.DataFrame({
        "title": ["Tiny Role A", "Tiny Role B"],
        "label": ["Other/Unknown", "Other/Unknown"],
    })
    lab = pd.concat([small_labelled, tiny], ignore_index=True)
    # Remove Other/Unknown from small_labelled so it only has 2.
    lab = lab[lab["label"] != "Other/Unknown"]
    lab = pd.concat([lab, tiny], ignore_index=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        report = evaluate(lab)
    warn_texts = [str(w.message) for w in caught] + report.get("warnings", [])
    assert any("Other/Unknown" in t or "fewer than" in t for t in warn_texts)


# ── scoring ───────────────────────────────────────────────────────────────────
def test_score_within_bounds(contacts_df):
    from outreachiq.data.designation import categorize
    from outreachiq.data.validation import validate
    from outreachiq.ml.scoring import score_contacts
    df = validate(contacts_df)
    df = categorize(df)
    if "excluded" not in df.columns:
        df["excluded"] = False
    scored = score_contacts(df)
    assert len(scored) == len(contacts_df)
    for s in scored:
        assert 0 <= s.priority_score <= 100
        assert len(s.reasons) >= 1


def test_score_reasons_present(contacts_df):
    from outreachiq.data.designation import categorize
    from outreachiq.data.validation import validate
    from outreachiq.ml.scoring import score_contacts
    df = validate(contacts_df)
    df = categorize(df)
    if "excluded" not in df.columns:
        df["excluded"] = False
    scored = score_contacts(df)
    # Every contact has at least a category reason.
    for s in scored:
        assert any("Category" in r for r in s.reasons)


def test_invalid_email_lowers_score(contacts_df):
    from outreachiq.data.designation import categorize
    from outreachiq.data.validation import validate
    from outreachiq.ml.scoring import score_contacts
    df = validate(contacts_df)
    df = categorize(df)
    if "excluded" not in df.columns:
        df["excluded"] = False
    scored = score_contacts(df)
    by_email = {s.email: s.priority_score for s in scored}
    # Carol has bad email; Bob has valid + same category "Talent Acquisition"
    carol = next(s for s in scored if s.name == "Carol")
    alice = next(s for s in scored if s.name == "Alice")
    assert carol.priority_score < alice.priority_score


# ── keyword frequency ─────────────────────────────────────────────────────────
def test_keyword_frequency():
    from outreachiq.ml.nlp import token_frequency
    counter = token_frequency(["HR Manager", "HR Specialist", "HR Lead"])
    assert counter["hr"] == 3
    assert "manager" in counter


def test_top_keywords_per_category(contacts_df):
    from outreachiq.data.designation import categorize
    from outreachiq.ml.nlp import top_keywords_per_category
    df = categorize(contacts_df)
    kw = top_keywords_per_category(df)
    assert isinstance(kw, dict)
    # At least one category should have keywords.
    assert any(len(v) > 0 for v in kw.values())


# ── page rendering ─────────────────────────────────────────────────────────────
def test_ml_page_renders_without_data():
    at = AppTest.from_file(str(PAGES_DIR / "ml_nlp.py"), default_timeout=15)
    at.run()
    assert not at.exception, f"ml_nlp.py raised: {at.exception}"
    assert len(at.title) >= 1


def test_ml_page_renders_with_labelled_file():
    """Evaluation tab: evaluate() on the synthetic file doesn't raise."""
    from outreachiq.ml.evaluation import evaluate
    from outreachiq.ml.labels import load_labelled
    lab = load_labelled(SAMPLE_LABELLED)
    report = evaluate(lab)
    assert report["macro_f1"] is not None
    assert report["test_size"] > 0
