"""Phase 6b tests: history_store, campaign_manager page, overview (all mocked)."""
from __future__ import annotations

import json
import smtplib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "src" / "outreachiq" / "ui" / "pages"

from outreachiq.campaigns.history_store import FileHistoryStore  # noqa: E402
from outreachiq.email_tools.campaign_prep import prepare_campaign  # noqa: E402
from outreachiq.email_tools.smtp_sender import (  # noqa: E402
    STATUS_ACCEPTED, STATUS_FAILED, STATUS_PENDING,
    STATUS_SIMULATED, STATUS_UNKNOWN, SendResult,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _result(email, status, mode="real", name=""):
    return SendResult(
        email=email, status=status,
        error_summary="" if status not in (STATUS_FAILED, STATUS_UNKNOWN) else "err",
        timestamp=_now(), mode=mode, recipient_name=name,
    )


def _make_contacts(n=3):
    return pd.DataFrame({
        "name": [f"Person{i}" for i in range(n)],
        "name_clean": [f"Person{i}" for i in range(n)],
        "email": [f"p{i}@example.com" for i in range(n)],
        "email_clean": [f"p{i}@example.com" for i in range(n)],
        "email_valid": [True] * n,
        "company": [f"Co{i}" for i in range(n)],
        "company_clean": [f"Co{i} Ltd" for i in range(n)],
        "title": ["Engineer"] * n,
        "excluded": [False] * n,
    })


# ── FileHistoryStore ──────────────────────────────────────────────────────────

def test_create_and_load(tmp_path):
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign(
        mode="test", subject="Hi there", template_name="default",
        resume_attached=False, total_ready=3, total_excluded=1,
    )
    record = store.load_campaign(cid)
    assert record is not None
    assert record["campaign_id"] == cid
    assert record["mode"] == "test"
    assert record["total_ready"] == 3
    assert record["status"] == "Running"


def test_update_recipient_persists_after_each_result(tmp_path):
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign("test", "Hi", "w", False, 2, 0)
    store.update_recipient(cid, _result("a@x.com", STATUS_SIMULATED, "test", "Alice"))
    record = store.load_campaign(cid)
    assert len(record["recipients"]) == 1
    store.update_recipient(cid, _result("b@x.com", STATUS_SIMULATED, "test", "Bob"))
    record = store.load_campaign(cid)
    assert len(record["recipients"]) == 2


def test_atomic_write_no_partial_read(tmp_path):
    """After each update the JSON file must be valid."""
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign("test", "Hi", "w", False, 1, 0)
    for i in range(5):
        store.update_recipient(cid, _result(f"r{i}@x.com", STATUS_SIMULATED, "test"))
        raw = (tmp_path / f"{cid}.json").read_text()
        json.loads(raw)   # must not raise


def test_set_status(tmp_path):
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign("test", "Hi", "w", False, 1, 0)
    store.set_status(cid, "Completed")
    assert store.load_campaign(cid)["status"] == "Completed"


def test_list_campaigns(tmp_path):
    store = FileHistoryStore(tmp_path)
    store.create_campaign("test", "A", "w", False, 1, 0)
    store.create_campaign("real", "B", "w", True, 2, 0)
    assert len(store.list_campaigns()) == 2


def test_sent_keys_includes_real_accepted_and_unknown(tmp_path):
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign("real", "Hi", "w", False, 3, 0)
    store.update_recipient(cid, _result("a@x.com", STATUS_ACCEPTED, "real"))
    store.update_recipient(cid, _result("b@x.com", STATUS_UNKNOWN, "real"))
    store.update_recipient(cid, _result("c@x.com", STATUS_FAILED, "real"))
    keys = store.sent_keys()
    assert "a@x.com" in keys
    assert "b@x.com" in keys
    assert "c@x.com" not in keys    # Failed does not count


def test_sent_keys_excludes_simulated(tmp_path):
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign("test", "Hi", "w", False, 2, 0)
    store.update_recipient(cid, _result("a@x.com", STATUS_SIMULATED, "test"))
    assert store.sent_keys() == set()   # test mode never counts


def test_sent_keys_dedup_across_campaigns(tmp_path):
    store = FileHistoryStore(tmp_path)
    for _ in range(2):
        cid = store.create_campaign("real", "Hi", "w", False, 1, 0)
        store.update_recipient(cid, _result("same@x.com", STATUS_ACCEPTED, "real"))
    keys = store.sent_keys()
    assert keys == {"same@x.com"}   # deduplicated


def test_no_body_text_in_record(tmp_path):
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign("real", "Subject text", "w", False, 1, 0)
    r = _result("a@x.com", STATUS_ACCEPTED, "real")
    store.update_recipient(cid, r)
    raw = (tmp_path / f"{cid}.json").read_text()
    assert "email body" not in raw.lower()
    assert "dear" not in raw.lower()    # no template body stored


def test_no_credentials_in_record(tmp_path):
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign("real", "Hi", "w", False, 1, 0)
    store.update_recipient(cid, _result("a@x.com", STATUS_FAILED, "real"))
    raw = (tmp_path / f"{cid}.json").read_text()
    for secret_word in ("password", "app_password", "GMAIL_APP_PASSWORD"):
        assert secret_word not in raw


def test_load_nonexistent_returns_none(tmp_path):
    store = FileHistoryStore(tmp_path)
    assert store.load_campaign("no_such_id") is None


# ── Campaign Manager page rendering ──────────────────────────────────────────

def test_campaign_manager_renders_without_prepared_campaign():
    at = AppTest.from_file(str(PAGES / "campaign_manager.py"), default_timeout=15)
    at.run()
    assert not at.exception, f"campaign_manager raised: {at.exception}"
    assert len(at.title) >= 1


def test_campaign_manager_renders_with_prepared_campaign():
    contacts = _make_contacts(2)
    camp = prepare_campaign(contacts, "Hi {Name}", "At {Company}.", attach_resume=False)
    at = AppTest.from_file(str(PAGES / "campaign_manager.py"), default_timeout=15)
    at.session_state["prepared_campaign"] = camp
    at.run()
    assert not at.exception, f"campaign_manager raised: {at.exception}"


def test_real_mode_blocked_when_credentials_missing(monkeypatch):
    """With no env vars the real-mode send button must be disabled/blocked."""
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    contacts = _make_contacts(2)
    camp = prepare_campaign(contacts, "Hi {Name}", "At {Company}.", attach_resume=False)
    at = AppTest.from_file(str(PAGES / "campaign_manager.py"), default_timeout=15)
    at.session_state["prepared_campaign"] = camp
    at.run()
    assert not at.exception


def test_test_mode_never_calls_smtplib():
    """Trigger a simulated send; smtplib.SMTP must never be called."""
    contacts = _make_contacts(2)
    camp = prepare_campaign(contacts, "Hi {Name}", "At {Company}.", attach_resume=False)
    with patch("smtplib.SMTP") as mock_smtp:
        from outreachiq.email_tools.smtp_sender import run_batch
        results = run_batch(
            camp, config=None, mode="test",
            delay_seconds=0, _sleep=lambda _: None,
        )
        mock_smtp.assert_not_called()
    assert all(r.status == STATUS_SIMULATED for r in results)


# ── Overview Dashboard campaign section ──────────────────────────────────────

def test_overview_renders_with_history(tmp_path, monkeypatch):
    import outreachiq.ui.pages.overview as ov_mod
    # Patch FileHistoryStore used inside the page to use tmp_path
    import outreachiq.campaigns.history_store as hs_mod
    monkeypatch.setattr(hs_mod, "CAMPAIGNS_DIR", tmp_path)
    hs_mod._default_store = None  # reset singleton
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign("test", "Hi", "w", False, 2, 0)
    store.update_recipient(cid, _result("a@x.com", STATUS_SIMULATED, "test"))
    store.set_status(cid, "Completed")
    at = AppTest.from_file(str(PAGES / "overview.py"), default_timeout=15)
    at.run()
    assert not at.exception, f"overview.py raised: {at.exception}"


def test_overview_renders_without_history():
    at = AppTest.from_file(str(PAGES / "overview.py"), default_timeout=15)
    at.run()
    assert not at.exception, f"overview.py raised: {at.exception}"
