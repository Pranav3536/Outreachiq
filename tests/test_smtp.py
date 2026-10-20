"""Phase 6a tests: SMTP config, message builder, sender (mock only, no real sends)."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage
from unittest.mock import MagicMock, call, patch

import pandas as pd
import pytest

from outreachiq.email_tools.campaign_prep import prepare_campaign
from outreachiq.email_tools.message_builder import MessageBuildError, build_message
from outreachiq.email_tools.smtp_config import (
    SmtpConfig,
    SmtpConfigError,
    credentials_status,
    load_smtp_config,
)
from outreachiq.email_tools.smtp_sender import (
    STATUS_ACCEPTED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SIMULATED,
    STATUS_UNKNOWN,
    SendResult,
    _FatalSendError,
    _RateLimitError,
    run_batch,
    send_one,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_config(addr="sender@example.com", pw="testpass", name="Test Sender"):
    return SmtpConfig(
        sender_address=addr,
        _app_password=pw,
        sender_name=name,
        host="smtp.gmail.com",
        port=587,
        send_delay_seconds=0,
    )


def _make_message(to="recv@example.com", subject="Hi", body="Hello!"):
    return build_message("Sender", "sender@example.com", to, subject, body)


def _minimal_contacts(n=2, all_valid=True):
    return pd.DataFrame({
        "name": [f"Contact{i}" for i in range(n)],
        "name_clean": [f"Contact{i}" for i in range(n)],
        "email": [f"c{i}@example.com" for i in range(n)],
        "email_clean": [f"c{i}@example.com" for i in range(n)],
        "email_valid": [True] * n,
        "company": [f"Corp{i}" for i in range(n)],
        "company_clean": [f"Corp{i} Ltd" for i in range(n)],
        "title": ["Engineer"] * n,
        "excluded": [False] * n,
    })


# ── smtp_config ───────────────────────────────────────────────────────────────

def test_credentials_missing_when_no_env(monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    status = credentials_status()
    assert status["configured"] is False
    assert "GMAIL_ADDRESS" in status["missing"]
    assert "GMAIL_APP_PASSWORD" in status["missing"]


def test_load_smtp_config_raises_when_missing(monkeypatch):
    monkeypatch.delenv("GMAIL_ADDRESS", raising=False)
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    with pytest.raises(SmtpConfigError):
        load_smtp_config()


def test_load_smtp_config_success(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "user@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "a b c d")  # with spaces
    monkeypatch.setenv("SENDER_DISPLAY_NAME", "Pranav")
    cfg = load_smtp_config()
    assert cfg.sender_address == "user@gmail.com"
    assert cfg.get_password() == "abcd"          # spaces stripped
    assert cfg.sender_name == "Pranav"


def test_password_not_in_repr(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "user@gmail.com")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "supersecretpassword")
    cfg = load_smtp_config()
    assert "supersecretpassword" not in repr(cfg)
    assert "supersecretpassword" not in str(cfg)


def test_password_not_in_error_message(monkeypatch):
    monkeypatch.setenv("GMAIL_ADDRESS", "not-an-email")
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "supersecretpassword")
    try:
        load_smtp_config()
    except SmtpConfigError as exc:
        assert "supersecretpassword" not in str(exc)


def test_real_mode_refuses_without_config():
    msg = _make_message()
    with pytest.raises(SmtpConfigError):
        send_one(msg, config=None, mode="real")


# ── message_builder ───────────────────────────────────────────────────────────

def test_message_has_one_to_no_cc_bcc():
    msg = _make_message()
    assert msg["To"] == "recv@example.com"
    assert msg["Cc"] is None
    assert msg["Bcc"] is None


def test_message_attachment_present():
    att = (b"%PDF fake", "cv.pdf", "application/pdf")
    msg = build_message("S", "s@e.com", "r@e.com", "Hi", "Body", attachment=att)
    payloads = msg.get_payload()
    assert isinstance(payloads, list)
    assert len(payloads) == 2  # text + attachment


def test_header_injection_subject_rejected():
    with pytest.raises(MessageBuildError):
        build_message("S", "s@e.com", "r@e.com", "Hi\nBcc:evil@e.com", "body")


def test_header_injection_to_rejected():
    with pytest.raises(MessageBuildError):
        build_message("S", "s@e.com", "r@e.com\nbcc:evil@e.com", "Hi", "body")


def test_empty_subject_rejected():
    with pytest.raises(MessageBuildError):
        build_message("S", "s@e.com", "r@e.com", "  ", "body")


def test_empty_body_rejected():
    with pytest.raises(MessageBuildError):
        build_message("S", "s@e.com", "r@e.com", "Hi", "  ")


# ── send_one test mode ────────────────────────────────────────────────────────

def test_test_mode_returns_simulated():
    msg = _make_message()
    result = send_one(msg, config=None, mode="test")
    assert result.status == STATUS_SIMULATED
    assert result.mode == "test"


def test_test_mode_makes_zero_smtplib_calls():
    msg = _make_message()
    with patch("smtplib.SMTP") as mock_smtp:
        send_one(msg, config=None, mode="test")
        mock_smtp.assert_not_called()


# ── send_one real mode (mocked smtplib) ──────────────────────────────────────

def test_real_mode_success():
    msg = _make_message()
    cfg = _make_config()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_ctx = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        result = send_one(msg, config=cfg, mode="real")
    assert result.status == STATUS_ACCEPTED
    assert result.mode == "real"


def test_real_mode_auth_error_raises_fatal():
    msg = _make_message()
    cfg = _make_config()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_ctx = MagicMock()
        mock_ctx.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Bad creds")
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        with pytest.raises(_FatalSendError):
            send_one(msg, config=cfg, mode="real")


def test_real_mode_recipient_refused_returns_failed():
    msg = _make_message()
    cfg = _make_config()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_ctx = MagicMock()
        mock_ctx.send_message.side_effect = smtplib.SMTPRecipientsRefused({})
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        result = send_one(msg, config=cfg, mode="real")
    assert result.status == STATUS_FAILED
    assert result.mode == "real"


def test_real_mode_rate_limit_raises():
    msg = _make_message()
    cfg = _make_config()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_ctx = MagicMock()
        mock_ctx.send_message.side_effect = smtplib.SMTPResponseException(421, b"rate limit")
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        with pytest.raises(_RateLimitError):
            send_one(msg, config=cfg, mode="real")


def test_real_mode_timeout_returns_unknown():
    msg = _make_message()
    cfg = _make_config()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_ctx = MagicMock()
        mock_ctx.send_message.side_effect = TimeoutError("connection timed out")
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_ctx)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)
        result = send_one(msg, config=cfg, mode="real")
    assert result.status == STATUS_UNKNOWN


def test_real_mode_timeout_no_retry():
    """send_one is called exactly once — no automatic retry on timeout."""
    msg = _make_message()
    cfg = _make_config()
    call_count = 0

    def _smtp_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.send_message.side_effect = TimeoutError("timed out")
        return m

    with patch("smtplib.SMTP", side_effect=_smtp_side_effect):
        send_one(msg, config=cfg, mode="real")

    assert call_count == 1


# ── run_batch ─────────────────────────────────────────────────────────────────

def _make_campaign(n=3):
    df = _minimal_contacts(n)
    return prepare_campaign(df, "Hi {Name}", "Working at {Company}.", attach_resume=False)


def test_run_batch_test_mode_all_simulated():
    camp = _make_campaign(3)
    cfg = _make_config()
    results = run_batch(camp, cfg, mode="test", delay_seconds=0, _sleep=lambda _: None)
    assert all(r.status == STATUS_SIMULATED for r in results)
    assert all(r.mode == "test" for r in results)


def test_run_batch_on_result_called_per_recipient():
    camp = _make_campaign(3)
    cfg = _make_config()
    collected = []
    run_batch(
        camp, cfg, mode="test", delay_seconds=0,
        on_result=collected.append, _sleep=lambda _: None,
    )
    assert len(collected) == 3


def test_run_batch_delay_called_between_sends():
    camp = _make_campaign(3)
    cfg = _make_config()
    sleep_calls = []
    run_batch(
        camp, cfg, mode="test", delay_seconds=2,
        _sleep=lambda s: sleep_calls.append(s),
    )
    # 3 sends -> 2 delays between them
    assert sleep_calls == [2, 2]


def test_run_batch_already_sent_keys_skipped():
    camp = _make_campaign(3)
    cfg = _make_config()
    already = {"c0@example.com"}
    results = run_batch(
        camp, cfg, mode="test", delay_seconds=0,
        already_sent_keys=already, _sleep=lambda _: None,
    )
    statuses = {r.email: r.status for r in results}
    assert statuses["c0@example.com"] == STATUS_PENDING   # skipped


def test_run_batch_auth_error_stops_and_leaves_rest_pending():
    camp = _make_campaign(3)
    cfg = _make_config()
    call_count = 0

    def _smtp_side(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad")
        return m

    with patch("smtplib.SMTP", side_effect=_smtp_side):
        results = run_batch(camp, cfg, mode="real", delay_seconds=0, _sleep=lambda _: None)

    pending = [r for r in results if r.status == STATUS_PENDING]
    failed = [r for r in results if r.status == STATUS_FAILED]
    assert len(pending) >= 1          # rest marked Pending
    assert len(failed) >= 1           # first one Failed


def test_run_batch_rate_limit_stops_and_leaves_rest_pending():
    camp = _make_campaign(3)
    cfg = _make_config()

    def _smtp_side(*args, **kwargs):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.send_message.side_effect = smtplib.SMTPResponseException(421, b"rate")
        return m

    with patch("smtplib.SMTP", side_effect=_smtp_side):
        results = run_batch(camp, cfg, mode="real", delay_seconds=0, _sleep=lambda _: None)

    pending = [r for r in results if r.status == STATUS_PENDING]
    assert len(pending) >= 2


def test_run_batch_recipient_refused_continues():
    camp = _make_campaign(3)
    cfg = _make_config()
    call_count = 0

    def _smtp_side(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        if call_count == 1:
            m.send_message.side_effect = smtplib.SMTPRecipientsRefused({})
        return m

    with patch("smtplib.SMTP", side_effect=_smtp_side):
        results = run_batch(camp, cfg, mode="real", delay_seconds=0, _sleep=lambda _: None)

    statuses = [r.status for r in results]
    assert STATUS_FAILED in statuses
    assert STATUS_ACCEPTED in statuses or STATUS_SIMULATED in statuses


def test_run_batch_cap_of_100_enforced(monkeypatch):
    import outreachiq.email_tools.smtp_sender as sender_mod
    monkeypatch.setattr(sender_mod, "get_env_int", lambda *a, **kw: 2)
    # Campaign already at 3 — cap should limit to 2
    camp = _make_campaign(3)
    cfg = _make_config()
    results = run_batch(camp, cfg, mode="test", delay_seconds=0, _sleep=lambda _: None)
    assert len(results) == 2


def test_should_stop_leaves_remaining_pending():
    camp = _make_campaign(3)
    cfg = _make_config()
    call_count = [0]

    def _stop():
        call_count[0] += 1
        return call_count[0] >= 2   # stop after first send

    results = run_batch(
        camp, cfg, mode="test", delay_seconds=0,
        should_stop=_stop, _sleep=lambda _: None,
    )
    pending = [r for r in results if r.status == STATUS_PENDING]
    assert len(pending) >= 1


# ── Phase 6a fix: stage tracking, SMTP_SSL, _ConnectionFatalError ─────────────

def _smtp_side_raises(exc_factory, at_stage="connect"):
    """Return a mock SMTP class that raises exc at the given stage."""
    def _side(*args, **kwargs):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        if at_stage == "connect":
            raise exc_factory()
        if at_stage == "starttls":
            m.starttls.side_effect = exc_factory()
        if at_stage == "login":
            m.login.side_effect = exc_factory()
        return m
    return _side


def test_disconnect_at_connect_returns_failed_with_stage():
    msg = _make_message()
    cfg = _make_config()
    from outreachiq.email_tools.smtp_sender import _ConnectionFatalError
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPServerDisconnected()):
        with pytest.raises(_ConnectionFatalError) as exc_info:
            send_one(msg, config=cfg, mode="real")
    assert "connect" in str(exc_info.value)
    assert "SMTPServerDisconnected" in str(exc_info.value)


def test_disconnect_at_starttls_returns_failed_with_stage():
    msg = _make_message()
    cfg = _make_config()
    from outreachiq.email_tools.smtp_sender import _ConnectionFatalError

    def _side(*a, **kw):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.starttls.side_effect = smtplib.SMTPServerDisconnected()
        return m

    with patch("smtplib.SMTP", side_effect=_side):
        with pytest.raises(_ConnectionFatalError) as exc_info:
            send_one(msg, config=cfg, mode="real")
    assert "starttls" in str(exc_info.value)


def test_disconnect_at_login_returns_failed_with_stage():
    msg = _make_message()
    cfg = _make_config()
    from outreachiq.email_tools.smtp_sender import _ConnectionFatalError

    def _side(*a, **kw):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.login.side_effect = smtplib.SMTPServerDisconnected()
        return m

    with patch("smtplib.SMTP", side_effect=_side):
        with pytest.raises(_ConnectionFatalError) as exc_info:
            send_one(msg, config=cfg, mode="real")
    assert "login" in str(exc_info.value)


def test_disconnect_at_send_returns_unknown_needs_review():
    msg = _make_message()
    cfg = _make_config()

    def _side(*a, **kw):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.send_message.side_effect = smtplib.SMTPServerDisconnected()
        return m

    with patch("smtplib.SMTP", side_effect=_side):
        result = send_one(msg, config=cfg, mode="real")
    assert result.status == STATUS_UNKNOWN


def test_disconnect_at_send_no_retry():
    """send_one must be called exactly once — no retry on disconnect during send."""
    msg = _make_message()
    cfg = _make_config()
    call_count = 0

    def _side(*a, **kw):
        nonlocal call_count
        call_count += 1
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.send_message.side_effect = smtplib.SMTPServerDisconnected()
        return m

    with patch("smtplib.SMTP", side_effect=_side):
        send_one(msg, config=cfg, mode="real")
    assert call_count == 1


def test_port_465_uses_smtp_ssl():
    msg = _make_message()
    cfg = _make_config()
    object.__setattr__(cfg, "port", 465)

    with patch("smtplib.SMTP_SSL") as mock_ssl, patch("smtplib.SMTP") as mock_plain:
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        mock_ssl.return_value = ctx
        send_one(msg, config=cfg, mode="real")
        mock_ssl.assert_called_once()
        mock_plain.assert_not_called()


def test_port_587_uses_plain_smtp_with_starttls():
    msg = _make_message()
    cfg = _make_config()   # default port 587

    with patch("smtplib.SMTP_SSL") as mock_ssl, patch("smtplib.SMTP") as mock_plain:
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=ctx)
        ctx.__exit__ = MagicMock(return_value=False)
        mock_plain.return_value = ctx
        send_one(msg, config=cfg, mode="real")
        mock_plain.assert_called_once()
        mock_ssl.assert_not_called()


def test_connection_fatal_at_connect_stops_batch_rest_pending():
    camp = _make_campaign(3)
    cfg = _make_config()

    with patch("smtplib.SMTP", side_effect=smtplib.SMTPServerDisconnected()):
        results = run_batch(camp, cfg, mode="real", delay_seconds=0, _sleep=lambda _: None)

    failed = [r for r in results if r.status == STATUS_FAILED]
    pending = [r for r in results if r.status == STATUS_PENDING]
    assert len(failed) == 1
    assert "connect" in failed[0].error_summary
    assert len(pending) == 2


def test_connection_fatal_at_login_stops_batch_rest_pending():
    camp = _make_campaign(3)
    cfg = _make_config()

    def _side(*a, **kw):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.login.side_effect = smtplib.SMTPServerDisconnected()
        return m

    with patch("smtplib.SMTP", side_effect=_side):
        results = run_batch(camp, cfg, mode="real", delay_seconds=0, _sleep=lambda _: None)

    failed = [r for r in results if r.status == STATUS_FAILED]
    pending = [r for r in results if r.status == STATUS_PENDING]
    assert len(failed) == 1
    assert "login" in failed[0].error_summary
    assert len(pending) == 2


def test_failed_result_does_not_enter_already_sent_keys():
    camp = _make_campaign(2)
    cfg = _make_config()
    sent_keys: set = set()

    def _side(*a, **kw):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.send_message.side_effect = smtplib.SMTPRecipientsRefused({})
        return m

    with patch("smtplib.SMTP", side_effect=_side):
        run_batch(
            camp, cfg, mode="real", delay_seconds=0,
            already_sent_keys=sent_keys, _sleep=lambda _: None,
        )
    # Recipient refused → Failed → must NOT be in sent_keys
    assert len(sent_keys) == 0


def test_unknown_needs_review_enters_already_sent_keys_in_real_mode():
    camp = _make_campaign(1)
    cfg = _make_config()
    sent_keys: set = set()

    def _side(*a, **kw):
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.send_message.side_effect = smtplib.SMTPServerDisconnected()
        return m

    with patch("smtplib.SMTP", side_effect=_side):
        results = run_batch(
            camp, cfg, mode="real", delay_seconds=0,
            already_sent_keys=sent_keys, _sleep=lambda _: None,
        )
    assert results[0].status == STATUS_UNKNOWN
    assert len(sent_keys) == 1


def test_simulated_never_enters_already_sent_keys():
    camp = _make_campaign(2)
    sent_keys: set = set()
    run_batch(
        camp, config=None, mode="test", delay_seconds=0,
        already_sent_keys=sent_keys, _sleep=lambda _: None,
    )
    assert len(sent_keys) == 0
