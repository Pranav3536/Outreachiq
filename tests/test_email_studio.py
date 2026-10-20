"""Phase 5b tests: attachments, campaign_prep, Email Studio page (synthetic only)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "src" / "outreachiq" / "ui" / "pages"

# Minimal valid PDF bytes: just the magic header
VALID_PDF = b"%PDF-1.4 fake pdf content for testing"
LARGE_PDF = b"%PDF" + b"x" * (5 * 1024 * 1024 + 1)


# ── validate_resume ────────────────────────────────────────────────────────────

def test_validate_resume_accepts_valid():
    from outreachiq.email_tools.attachments import validate_resume
    ok, msg = validate_resume(VALID_PDF, "my_cv.pdf")
    assert ok is True
    assert msg == "OK"


def test_validate_resume_rejects_wrong_extension():
    from outreachiq.email_tools.attachments import validate_resume
    ok, msg = validate_resume(VALID_PDF, "my_cv.docx")
    assert ok is False
    assert "pdf" in msg.lower()


def test_validate_resume_rejects_non_pdf_bytes():
    from outreachiq.email_tools.attachments import validate_resume
    ok, msg = validate_resume(b"PK\x03\x04fake zip", "cv.pdf")
    assert ok is False
    assert "PDF" in msg or "valid" in msg.lower()


def test_validate_resume_rejects_oversize():
    from outreachiq.email_tools.attachments import validate_resume
    ok, msg = validate_resume(LARGE_PDF, "cv.pdf")
    assert ok is False
    assert "large" in msg.lower() or "MB" in msg


def test_validate_resume_rejects_path_traversal():
    from outreachiq.email_tools.attachments import validate_resume
    ok, msg = validate_resume(VALID_PDF, "../etc/passwd.pdf")
    assert ok is False


# ── save / replace / delete / meta / build_attachment ─────────────────────────

def test_save_resume(tmp_path, monkeypatch):
    import outreachiq.email_tools.attachments as att_mod
    monkeypatch.setattr(att_mod, "RESUME_DIR", tmp_path)
    att_mod.save_resume(VALID_PDF)
    assert (tmp_path / "default_resume.pdf").read_bytes() == VALID_PDF


def test_replace_resume(tmp_path, monkeypatch):
    import outreachiq.email_tools.attachments as att_mod
    monkeypatch.setattr(att_mod, "RESUME_DIR", tmp_path)
    att_mod.save_resume(VALID_PDF)
    new_bytes = b"%PDF-1.5 new version"
    att_mod.save_resume(new_bytes)
    assert (tmp_path / "default_resume.pdf").read_bytes() == new_bytes


def test_delete_resume(tmp_path, monkeypatch):
    import outreachiq.email_tools.attachments as att_mod
    monkeypatch.setattr(att_mod, "RESUME_DIR", tmp_path)
    att_mod.save_resume(VALID_PDF)
    assert att_mod.resume_exists()
    att_mod.delete_resume()
    assert not att_mod.resume_exists()


def test_delete_resume_silent_when_missing(tmp_path, monkeypatch):
    import outreachiq.email_tools.attachments as att_mod
    monkeypatch.setattr(att_mod, "RESUME_DIR", tmp_path)
    att_mod.delete_resume()  # must not raise


def test_resume_meta(tmp_path, monkeypatch):
    import outreachiq.email_tools.attachments as att_mod
    monkeypatch.setattr(att_mod, "RESUME_DIR", tmp_path)
    assert att_mod.resume_meta() is None
    att_mod.save_resume(VALID_PDF)
    meta = att_mod.resume_meta()
    assert meta is not None
    assert meta["filename"] == "default_resume.pdf"
    assert meta["size_bytes"] == len(VALID_PDF)


def test_build_attachment(tmp_path, monkeypatch):
    import outreachiq.email_tools.attachments as att_mod
    monkeypatch.setattr(att_mod, "RESUME_DIR", tmp_path)
    att_mod.save_resume(VALID_PDF)
    data, name, mime = att_mod.build_attachment()
    assert data == VALID_PDF
    assert name.endswith(".pdf")
    assert mime == "application/pdf"


def test_build_attachment_raises_when_missing(tmp_path, monkeypatch):
    import outreachiq.email_tools.attachments as att_mod
    monkeypatch.setattr(att_mod, "RESUME_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        att_mod.build_attachment()


# ── prepare_campaign ──────────────────────────────────────────────────────────

@pytest.fixture
def contacts():
    return pd.DataFrame({
        "name": ["Alice", "Bob", "Carol", "David"],
        "name_clean": ["Alice", "Bob", "Carol", "David"],
        "email": ["a@ex.com", "bad-email", "c@ex.com", "d@ex.com"],
        "email_clean": ["a@ex.com", "", "c@ex.com", "d@ex.com"],
        "email_valid": [True, False, True, True],
        "title": ["HR Manager", "Engineer", "CEO", "Recruiter"],
        "company": ["Acme", "Beta", "Gamma", "Delta"],
        "company_clean": ["Acme Corp", "Beta Ltd", "Gamma Inc", "Delta Co"],
        "excluded": [False, False, False, True],
    })


def test_prepare_campaign_excludes_invalid_email(contacts):
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    camp = prepare_campaign(contacts, "Hi {Name}", "At {Company}.", attach_resume=False)
    excl_names = [r.name for r in camp.recipients_excluded]
    assert "Bob" in excl_names


def test_prepare_campaign_excludes_excluded_duplicate(contacts):
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    camp = prepare_campaign(contacts, "Hi {Name}", "At {Company}.", attach_resume=False)
    excl_names = [r.name for r in camp.recipients_excluded]
    assert "David" in excl_names
    reasons = {r.name: r.exclusion_reason for r in camp.recipients_excluded}
    assert "excluded" in reasons["David"].lower() or "duplicate" in reasons["David"].lower()


def test_prepare_campaign_excludes_missing_email():
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    df = pd.DataFrame({
        "name": ["Eve"], "name_clean": ["Eve"],
        "email": [""], "email_clean": [""],
        "email_valid": [False],
        "company": ["Acme"], "company_clean": ["Acme"],
        "title": ["HR"], "excluded": [False],
    })
    camp = prepare_campaign(df, "Hi {Name}", "At {Company}.", attach_resume=False)
    assert len(camp.recipients_excluded) == 1
    assert "email" in camp.recipients_excluded[0].exclusion_reason.lower()


def test_prepare_campaign_excludes_unresolved_placeholder(contacts):
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    # {BADFIELD} is unknown — should block every recipient
    camp = prepare_campaign(
        contacts.head(1),
        "Hi {Name}", "Please send {BADFIELD}.",
        attach_resume=False
    )
    assert len(camp.recipients_excluded) == 1
    assert "BADFIELD" in camp.recipients_excluded[0].exclusion_reason


def test_no_rendered_email_has_unresolved(contacts):
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    camp = prepare_campaign(contacts, "Hi {Name}", "At {Company}.", attach_resume=False)
    for r in camp.recipients_ready:
        assert r.rendered is not None
        assert r.rendered.unresolved == []


def test_ready_recipients_have_valid_emails(contacts):
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    camp = prepare_campaign(contacts, "Hi {Name}", "At {Company}.", attach_resume=False)
    for r in camp.recipients_ready:
        assert "@" in r.email


def test_limit_enforced(monkeypatch):
    from outreachiq.email_tools import campaign_prep as cp_mod
    monkeypatch.setattr(cp_mod, "get_env_int", lambda *a, **kw: 2)
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    df = pd.DataFrame({
        "name": ["A", "B", "C"], "name_clean": ["A", "B", "C"],
        "email": ["a@x.com", "b@x.com", "c@x.com"],
        "email_clean": ["a@x.com", "b@x.com", "c@x.com"],
        "email_valid": [True, True, True],
        "company": ["X", "Y", "Z"], "company_clean": ["X", "Y", "Z"],
        "title": ["Eng", "Eng", "Eng"], "excluded": [False, False, False],
    })
    camp = prepare_campaign(df, "Hi {Name}", "At {Company}.", attach_resume=False)
    assert camp.limit_exceeded is True
    assert camp.ready_count == 0


def test_resume_required_but_missing_blocks_readiness(tmp_path, monkeypatch):
    import outreachiq.email_tools.attachments as att_mod
    monkeypatch.setattr(att_mod, "RESUME_DIR", tmp_path)
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    df = pd.DataFrame({
        "name": ["Alice"], "name_clean": ["Alice"],
        "email": ["a@ex.com"], "email_clean": ["a@ex.com"],
        "email_valid": [True],
        "company": ["Acme"], "company_clean": ["Acme"],
        "title": ["HR"], "excluded": [False],
    })
    camp = prepare_campaign(df, "Hi {Name}", "At {Company}.", attach_resume=True)
    assert camp.resume_ready is False
    assert not camp.is_sendable


def test_exclusion_reasons_present(contacts):
    from outreachiq.email_tools.campaign_prep import prepare_campaign
    camp = prepare_campaign(contacts, "Hi {Name}", "At {Company}.", attach_resume=False)
    for r in camp.recipients_excluded:
        assert r.exclusion_reason != ""


# ── Email Studio page rendering ────────────────────────────────────────────────

def test_email_studio_page_renders_without_data():
    at = AppTest.from_file(str(PAGES_DIR / "email_studio.py"), default_timeout=15)
    at.run()
    assert not at.exception, f"email_studio.py raised: {at.exception}"
    assert len(at.title) >= 1


def test_email_studio_page_renders_with_selection():
    at = AppTest.from_file(str(PAGES_DIR / "email_studio.py"), default_timeout=15)
    # Inject a minimal campaign_selection into session state
    at.session_state["campaign_selection"] = pd.DataFrame({
        "name": ["Alice"], "name_clean": ["Alice"],
        "email": ["alice@example.com"], "email_clean": ["alice@example.com"],
        "email_valid": [True],
        "company": ["Acme"], "company_clean": ["Acme Corp"],
        "title": ["HR Manager"], "excluded": [False],
    })
    at.run()
    assert not at.exception, f"email_studio.py raised: {at.exception}"
    assert len(at.title) >= 1
