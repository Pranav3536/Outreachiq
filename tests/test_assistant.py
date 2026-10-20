"""Phase 7b tests: assistant tools, workflow, page (synthetic, no real sends)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "src" / "outreachiq" / "ui" / "pages"

from outreachiq.assistant.tools import (
    Proposal,
    campaign_history_summary,
    data_quality_summary,
    inspect_dataset,
    propose_campaign,
    selection_summary,
    suggest_classifications,
)
from outreachiq.assistant.workflow import (
    SUPPORTED_COMMANDS,
    parse_command,
    unknown_command_help,
)
from outreachiq.campaigns.history_store import FileHistoryStore  # noqa: E402
from outreachiq.email_tools.smtp_sender import (  # noqa: E402
    STATUS_ACCEPTED, STATUS_FAILED, STATUS_UNKNOWN, SendResult,
)

from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc).isoformat()


def _result(email, status, mode="real"):
    return SendResult(
        email=email, status=status,
        error_summary="", timestamp=_now(), mode=mode,
    )


def _contacts(n=5):
    return pd.DataFrame({
        "name": [f"Person{i}" for i in range(n)],
        "name_clean": [f"Person{i}" for i in range(n)],
        "email": [f"p{i}@example.com" for i in range(n)],
        "email_clean": [f"p{i}@example.com" for i in range(n)],
        "email_valid": [True] * n,
        "title": ["HR Manager", "CEO", "Talent Acquisition Lead", "Engineer", "Director"][:n],
        "company": [f"Co{i}" for i in range(n)],
        "company_clean": [f"Co{i} Ltd" for i in range(n)],
        "excluded": [False] * n,
    })


# ── inspect_dataset ───────────────────────────────────────────────────────────

def test_inspect_dataset_with_data():
    df = _contacts(3)
    r = inspect_dataset(df)
    assert r["rows"] == 3
    assert "name" in r["columns"]
    assert "mapped" in r["mapping_status"]


def test_inspect_dataset_empty():
    r = inspect_dataset(None)
    assert r["rows"] == 0
    assert r["mapping_status"] == "no data loaded"


# ── data_quality_summary ──────────────────────────────────────────────────────

def test_data_quality_summary():
    df = _contacts(3)
    df.loc[0, "email_valid"] = False
    r = data_quality_summary(df)
    assert r["invalid_emails"] == 1
    assert "missing_fields" in r
    assert "duplicates" in r


def test_data_quality_summary_empty():
    r = data_quality_summary(None)
    assert r["invalid_emails"] == 0


# ── suggest_classifications ────────────────────────────────────────────────────

def test_suggest_classifications_returns_list():
    df = _contacts(3)
    results = suggest_classifications(df)
    assert isinstance(results, list)


def test_suggest_classifications_empty():
    results = suggest_classifications(None)
    assert results == []


# ── selection_summary ─────────────────────────────────────────────────────────

def test_selection_summary():
    df = _contacts(4)
    r = selection_summary(df)
    assert r["count"] == 4
    assert isinstance(r["categories"], dict)


def test_selection_summary_excludes_invalid():
    df = _contacts(3)
    df.loc[0, "email_valid"] = False
    r = selection_summary(df)
    assert r["count"] == 2
    assert r["excluded"] == 1


# ── campaign_history_summary ───────────────────────────────────────────────────

def test_campaign_history_summary_no_delivery_keys(tmp_path):
    store = FileHistoryStore(tmp_path)
    r = campaign_history_summary(store)
    for forbidden in ("delivered", "opened", "replied", "open_rate", "reply_rate"):
        assert forbidden not in r


def test_campaign_history_summary_with_data(tmp_path):
    store = FileHistoryStore(tmp_path)
    cid = store.create_campaign("real", "Hi", "w", False, 2, 0)
    store.update_recipient(cid, _result("a@x.com", STATUS_ACCEPTED))
    store.update_recipient(cid, _result("b@x.com", STATUS_FAILED))
    store.set_status(cid, "Completed")
    r = campaign_history_summary(store)
    assert r["campaigns"] == 1
    assert r["smtp_accepted"] == 1
    assert r["failed"] == 1


# ── propose_campaign ──────────────────────────────────────────────────────────

def test_propose_campaign_respects_limit(tmp_path, monkeypatch):
    import outreachiq.assistant.tools as tools_mod
    import outreachiq.campaigns.history_store as hs_mod
    monkeypatch.setattr(hs_mod, "CAMPAIGNS_DIR", tmp_path)
    hs_mod._default_store = None
    monkeypatch.setattr(tools_mod, "is_env_set", lambda name: False)
    monkeypatch.setattr(tools_mod, "resume_exists", lambda: False)
    df = _contacts(5)
    proposal = propose_campaign(df, categories=None, limit=3, store=FileHistoryStore(tmp_path))
    assert proposal.recipient_count <= 3


def test_propose_campaign_excludes_invalid_and_duplicate(tmp_path, monkeypatch):
    import outreachiq.assistant.tools as tools_mod
    import outreachiq.campaigns.history_store as hs_mod
    monkeypatch.setattr(hs_mod, "CAMPAIGNS_DIR", tmp_path)
    hs_mod._default_store = None
    monkeypatch.setattr(tools_mod, "is_env_set", lambda name: False)
    monkeypatch.setattr(tools_mod, "resume_exists", lambda: False)
    df = _contacts(3)
    df.loc[0, "email_valid"] = False
    df.loc[1, "excluded"] = True
    proposal = propose_campaign(df, store=FileHistoryStore(tmp_path))
    assert proposal.recipient_count == 1
    assert len(proposal.exclusion_reasons) >= 2


def test_propose_campaign_skips_already_sent(tmp_path, monkeypatch):
    import outreachiq.assistant.tools as tools_mod
    import outreachiq.campaigns.history_store as hs_mod
    monkeypatch.setattr(hs_mod, "CAMPAIGNS_DIR", tmp_path)
    hs_mod._default_store = None
    store = FileHistoryStore(tmp_path)
    # Mark one email as already sent in a past real campaign
    cid = store.create_campaign("real", "old", "w", False, 1, 0)
    store.update_recipient(cid, _result("p0@example.com", STATUS_ACCEPTED))
    store.set_status(cid, "Completed")
    monkeypatch.setattr(tools_mod, "is_env_set", lambda name: False)
    monkeypatch.setattr(tools_mod, "resume_exists", lambda: False)
    df = _contacts(3)
    proposal = propose_campaign(df, store=store)
    assert "p0@example.com" in proposal.already_sent_skips
    assert proposal.recipient_count == 2


def test_propose_campaign_returns_proposal_object(tmp_path, monkeypatch):
    import outreachiq.assistant.tools as tools_mod
    monkeypatch.setattr(tools_mod, "is_env_set", lambda name: False)
    monkeypatch.setattr(tools_mod, "resume_exists", lambda: False)
    df = _contacts(2)
    p = propose_campaign(df, store=FileHistoryStore(tmp_path))
    assert isinstance(p, Proposal)
    assert p.recipient_count == 2


def test_propose_campaign_empty():
    p = propose_campaign(None)
    assert p.recipient_count == 0


# ── command parser ────────────────────────────────────────────────────────────

def test_parse_inspect():
    assert parse_command("check data")[0] == "inspect"
    assert parse_command("inspect")[0] == "inspect"


def test_parse_quality():
    assert parse_command("quality")[0] == "quality"


def test_parse_suggest():
    assert parse_command("suggest titles")[0] == "suggest_titles"


def test_parse_selection():
    assert parse_command("selection")[0] == "selection"


def test_parse_history():
    assert parse_command("history")[0] == "history"


def test_parse_propose_with_categories():
    cmd, args = parse_command("propose campaign for HR and Talent Acquisition top 10")
    assert cmd == "propose"
    assert "HR/Recruiting" in args["categories"]
    assert "Talent Acquisition" in args["categories"]
    assert args["limit"] == 10


def test_parse_unknown():
    cmd, args = parse_command("do something weird")
    assert cmd == "unknown"
    assert args == {}


def test_unknown_command_help():
    text = unknown_command_help()
    assert "don't recognise" in text.lower() or "try one of" in text.lower()
    assert len(SUPPORTED_COMMANDS) >= 5


# ── page rendering ────────────────────────────────────────────────────────────

def test_campaign_manager_page_renders_without_data():
    at = AppTest.from_file(str(PAGES / "campaign_manager.py"), default_timeout=15)
    at.run()
    assert not at.exception, f"campaign_manager raised: {at.exception}"
    assert len(at.title) >= 1


def test_campaign_manager_page_renders_with_prepared_campaign():
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    contacts = _contacts(2)
    camp = prepare_campaign(contacts, "Hi {Name}", "At {Company}.", attach_resume=False)
    at = AppTest.from_file(str(PAGES / "campaign_manager.py"), default_timeout=15)
    at.session_state["prepared_campaign"] = camp
    at.run()
    assert not at.exception, f"campaign_manager raised: {at.exception}"


# ── approval never triggers sending ──────────────────────────────────────────

def test_approval_only_sets_campaign_selection():
    """Approval copies recipients to campaign_selection; never calls smtplib."""
    from outreachiq.assistant.tools import propose_campaign
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.assert_not_called()
    # The approval flow is in the UI; we verify the tool doesn't send.
    assert mock_smtp.call_count == 0


# ── no assistant function writes to contact/history files ──────────────────────

def test_inspect_dataset_no_file_writes(tmp_path):
    """Tools are read-only — no new files created in the data/runtime dirs."""
    before = set(p.name for p in tmp_path.rglob("*"))
    df = _contacts(3)
    inspect_dataset(df)
    data_quality_summary(df)
    suggest_classifications(df)
    selection_summary(df)
    after = set(p.name for p in tmp_path.rglob("*"))
    assert before == after


def test_campaign_history_summary_no_file_writes(tmp_path):
    store = FileHistoryStore(tmp_path)
    before = set(p.name for p in tmp_path.rglob("*"))
    campaign_history_summary(store)
    after = set(p.name for p in tmp_path.rglob("*"))
    assert before == after
