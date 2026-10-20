"""Phase 7a tests: reports logic, filters, exports, review notes, page (synthetic)."""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "src" / "outreachiq" / "ui" / "pages"

from outreachiq.campaigns.history_store import FileHistoryStore  # noqa: E402
from outreachiq.campaigns.reports import (  # noqa: E402
    campaigns_to_df,
    export_csv_bytes,
    export_xlsx_bytes,
    filter_campaigns,
    filter_recipients,
    load_review_notes,
    recipients_df,
    save_review_note,
    summary_stats,
)
from outreachiq.email_tools.smtp_sender import (  # noqa: E402
    STATUS_ACCEPTED, STATUS_FAILED, STATUS_PENDING,
    STATUS_SIMULATED, STATUS_UNKNOWN, SendResult,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _now():
    return datetime.now(timezone.utc).isoformat()


def _result(email, status, mode="real", name=""):
    return SendResult(
        email=email, status=status,
        error_summary="" if status not in (STATUS_FAILED, STATUS_UNKNOWN) else "err",
        timestamp=_now(), mode=mode, recipient_name=name,
    )


def _make_store(tmp_path):
    return FileHistoryStore(tmp_path)


def _populate(store, n_campaigns=2, mode="real"):
    for c in range(n_campaigns):
        cid = store.create_campaign(
            mode=mode, subject=f"Subject {c}", template_name="w",
            resume_attached=False, total_ready=3, total_excluded=1,
        )
        store.update_recipient(cid, _result(f"a{c}@x.com", STATUS_ACCEPTED, mode))
        store.update_recipient(cid, _result(f"b{c}@x.com", STATUS_FAILED, mode))
        store.update_recipient(cid, _result(f"c{c}@x.com", STATUS_UNKNOWN, mode))
        store.set_status(cid, "Completed")
    return store


# ── campaigns_to_df ──────────────────────────────────────────────────────────

def test_campaigns_to_df_has_expected_columns(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1)
    df, warns = campaigns_to_df(store)
    expected = {
        "campaign_id", "created_at", "mode", "subject", "total",
        "simulated", "smtp_accepted", "failed", "unknown_needs_review",
        "pending", "status", "stop_reason",
    }
    assert expected.issubset(set(df.columns))
    assert len(df) == 1
    assert warns == []


def test_campaigns_to_df_counts_correct(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1)
    df, _ = campaigns_to_df(store)
    row = df.iloc[0]
    assert row["smtp_accepted"] == 1
    assert row["failed"] == 1
    assert row["unknown_needs_review"] == 1
    assert row["simulated"] == 0
    assert row["total"] == 3


def test_campaigns_to_df_skips_corrupt_json(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1)
    # Write a corrupt JSON
    (tmp_path / "corrupt.json").write_text("{not valid json")
    df, warns = campaigns_to_df(store)
    assert len(df) == 1          # only the valid campaign
    assert "corrupt.json" in warns


def test_campaigns_to_df_skips_review_notes_file(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1)
    (tmp_path / "review_notes.json").write_text("{}")
    df, _ = campaigns_to_df(store)
    assert len(df) == 1   # review_notes excluded


# ── recipients_df ─────────────────────────────────────────────────────────────

def test_recipients_df_all_campaigns(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 2)
    rdf = recipients_df(store=store)
    assert len(rdf) == 6    # 2 campaigns × 3 recipients
    assert "campaign_id" in rdf.columns
    assert "status" in rdf.columns


def test_recipients_df_single_campaign(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 2)
    campaigns = store.list_campaigns()
    cid = campaigns[0]["campaign_id"]
    rdf = recipients_df(campaign_id=cid, store=store)
    assert len(rdf) == 3
    assert (rdf["campaign_id"] == cid).all()


# ── filters ────────────────────────────────────────────────────────────────────

def test_filter_campaigns_by_mode(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1, mode="real")
    _populate(store, 1, mode="test")
    df, _ = campaigns_to_df(store)
    real = filter_campaigns(df, mode="real")
    test = filter_campaigns(df, mode="test")
    assert len(real) == 1
    assert (real["mode"] == "real").all()
    assert len(test) == 1
    assert (test["mode"] == "test").all()


def test_filter_campaigns_by_status(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1)
    store.set_status(store.list_campaigns()[0]["campaign_id"], "Stopped")
    df, _ = campaigns_to_df(store)
    stopped = filter_campaigns(df, status="Stopped")
    assert len(stopped) == 1
    assert (stopped["status"] == "Stopped").all()


def test_filter_campaigns_by_search(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1)
    df, _ = campaigns_to_df(store)
    result = filter_campaigns(df, search="Subject 0")
    assert len(result) == 1
    result_none = filter_campaigns(df, search="zzzz")
    assert len(result_none) == 0


def test_filter_recipients_by_mode(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1, mode="real")
    _populate(store, 1, mode="test")
    rdf = recipients_df(store=store)
    real = filter_recipients(rdf, mode="real")
    assert (real["mode"] == "real").all()
    assert len(real) == 3


def test_filter_recipients_by_search(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1)
    rdf = recipients_df(store=store)
    found = filter_recipients(rdf, search="a0@x.com")
    assert len(found) == 1


# ── summary_stats ─────────────────────────────────────────────────────────────

def test_summary_stats_no_delivery_keys(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 2)
    df, _ = campaigns_to_df(store)
    stats = summary_stats(df)
    assert stats["campaigns"] == 2
    assert stats["smtp_accepted"] == 2
    assert stats["failed"] == 2
    assert stats["unknown_needs_review"] == 2
    # Must NOT have any delivery/open/reply keys
    for forbidden in ("delivered", "opened", "replied", "open_rate", "reply_rate", "delivery_rate"):
        assert forbidden not in stats


def test_summary_stats_empty():
    stats = summary_stats(pd.DataFrame())
    assert stats["campaigns"] == 0
    assert stats["smtp_accepted"] == 0


# ── exports ───────────────────────────────────────────────────────────────────

def test_export_csv_bytes(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1)
    df, _ = campaigns_to_df(store)
    b = export_csv_bytes(df)
    assert b.startswith(b"campaign_id")
    text = b.decode("utf-8")
    assert "Subject 0" in text


def test_export_xlsx_bytes(tmp_path):
    store = _make_store(tmp_path)
    _populate(store, 1)
    df, _ = campaigns_to_df(store)
    b = export_xlsx_bytes(df)
    assert b[:2] == b"PK"   # ZIP / xlsx signature
    df2 = pd.read_excel(io.BytesIO(b), engine="openpyxl")
    assert len(df2) == 1


# ── review notes ──────────────────────────────────────────────────────────────

def test_save_and_load_review_note(tmp_path, monkeypatch):
    import outreachiq.campaigns.reports as rep_mod
    monkeypatch.setattr(rep_mod, "REVIEW_NOTES_FILE", tmp_path / "review_notes.json")
    save_review_note("camp_001", "user@x.com", "Check Sent folder")
    notes = load_review_notes()
    key = "camp_001|user@x.com"
    assert key in notes
    assert notes[key]["note"] == "Check Sent folder"


def test_load_review_notes_empty(tmp_path, monkeypatch):
    import outreachiq.campaigns.reports as rep_mod
    monkeypatch.setattr(rep_mod, "REVIEW_NOTES_FILE", tmp_path / "nonexistent.json")
    assert load_review_notes() == {}


def test_review_note_overwrite(tmp_path, monkeypatch):
    import outreachiq.campaigns.reports as rep_mod
    monkeypatch.setattr(rep_mod, "REVIEW_NOTES_FILE", tmp_path / "review_notes.json")
    save_review_note("c1", "a@x.com", "first note")
    save_review_note("c1", "a@x.com", "second note")
    notes = load_review_notes()
    assert notes["c1|a@x.com"]["note"] == "second note"


# ── page rendering ────────────────────────────────────────────────────────────

def test_history_reports_page_renders_without_campaigns():
    at = AppTest.from_file(str(PAGES / "history_reports.py"), default_timeout=15)
    at.run()
    assert not at.exception, f"history_reports.py raised: {at.exception}"
    assert len(at.title) >= 1


def test_history_reports_page_renders_with_campaigns(tmp_path, monkeypatch):
    import outreachiq.campaigns.history_store as hs_mod
    import outreachiq.campaigns.reports as rep_mod
    monkeypatch.setattr(hs_mod, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(rep_mod, "CAMPAIGNS_DIR", tmp_path)
    monkeypatch.setattr(rep_mod, "REVIEW_NOTES_FILE", tmp_path / "review_notes.json")
    hs_mod._default_store = None
    store = FileHistoryStore(tmp_path)
    _populate(store, 2)
    at = AppTest.from_file(str(PAGES / "history_reports.py"), default_timeout=15)
    at.run()
    assert not at.exception, f"history_reports.py raised: {at.exception}"
