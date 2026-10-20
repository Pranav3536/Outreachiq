"""Gmail SMTP sender. Two strictly separated modes: 'test' and 'real'.

- 'test' mode: validates the message, returns status "Simulated", makes ZERO
  network calls. Results are clearly marked mode="test" and can never be
  presented as a real send outcome.
- 'real' mode: port 465 → SMTP_SSL; all other ports → SMTP + STARTTLS.
  Requires a loaded SmtpConfig with credentials. Missing credentials raise
  SmtpConfigError before any connection attempt.

Stage tracking: send_one sets a `stage` variable ("connect", "starttls",
"login", "send") before each network step. Errors at connect/starttls/login
mean the message was never sent → status "Failed" + _ConnectionFatalError
(stops the batch). Errors at "send" → "Unknown/Needs Review" (ambiguous).

SMTP accepted != delivered. Results carry this label.
No automatic retries on ambiguous failures.
Passwords NEVER appear in any log, exception, error_summary, or SendResult.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Callable

from ..config import ENV_MAX_RECIPIENTS_PER_CAMPAIGN, get_env_int
from .campaign_prep import PreparedCampaign
from .placeholders import TemplateError, ensure_sendable
from .smtp_config import SmtpConfig, SmtpConfigError

logger = logging.getLogger(__name__)

# ── Status constants ──────────────────────────────────────────────────────────
STATUS_ACCEPTED = "SMTP Accepted"
STATUS_FAILED = "Failed"
STATUS_UNKNOWN = "Unknown/Needs Review"
STATUS_SIMULATED = "Simulated"
STATUS_PENDING = "Pending"

_RATE_LIMIT_CODES = {421, 450, 451, 452, 454}
_DAILY_LIMIT_PREFIX = "5.4.5"

SMTP_TIMEOUT_SECONDS = 30
_SSL_PORT = 465


@dataclass
class SendResult:
    email: str
    status: str           # one of the STATUS_* constants
    error_summary: str    # short, NO credentials
    timestamp: str        # ISO-8601 UTC
    mode: str             # "test" or "real"
    recipient_name: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _class_name(exc: Exception) -> str:
    return type(exc).__name__


# ── Internal sentinel exceptions ─────────────────────────────────────────────

class _FatalSendError(Exception):
    """Auth failure: stop the entire batch."""


class _RateLimitError(Exception):
    """Rate-limit / quota: stop the entire batch."""


class _ConnectionFatalError(Exception):
    """Pre-send connection failure: message was never sent; stop the batch."""


# ── Single-message send ───────────────────────────────────────────────────────

def send_one(
    message: EmailMessage,
    config: SmtpConfig | None,
    mode: str,
) -> SendResult:
    """Send a single EmailMessage. mode must be 'test' or 'real'."""
    to_addr = message.get("To", "")
    if mode not in ("test", "real"):
        raise ValueError(f"mode must be 'test' or 'real', got '{mode}'.")

    # ── Test mode: zero network activity ─────────────────────────────────────
    if mode == "test":
        if not to_addr:
            return SendResult(
                email=to_addr, status=STATUS_FAILED,
                error_summary="No To address in message.",
                timestamp=_now_iso(), mode="test",
            )
        return SendResult(
            email=to_addr, status=STATUS_SIMULATED,
            error_summary="",
            timestamp=_now_iso(), mode="test",
        )

    # ── Real mode ─────────────────────────────────────────────────────────────
    if config is None:
        raise SmtpConfigError(
            "SmtpConfig is required for real mode. "
            "Load it with load_smtp_config()."
        )

    stage = "connect"
    ssl_ctx = ssl.create_default_context()
    use_ssl = (config.port == _SSL_PORT)

    try:
        if use_ssl:
            # Port 465: direct SSL, no STARTTLS
            stage = "connect"
            smtp_obj = smtplib.SMTP_SSL(
                config.host, config.port,
                timeout=SMTP_TIMEOUT_SECONDS, context=ssl_ctx,
            )
            with smtp_obj as smtp:
                smtp.ehlo()
                stage = "login"
                smtp.login(config.sender_address, config.get_password())
                stage = "send"
                smtp.send_message(message)
        else:
            # Port 587 (or other): SMTP + STARTTLS
            stage = "connect"
            with smtplib.SMTP(
                config.host, config.port, timeout=SMTP_TIMEOUT_SECONDS
            ) as smtp:
                smtp.ehlo()
                stage = "starttls"
                smtp.starttls(context=ssl_ctx)
                smtp.ehlo()
                stage = "login"
                smtp.login(config.sender_address, config.get_password())
                stage = "send"
                smtp.send_message(message)

        logger.info("SMTP accepted message for %s (accepted != delivered)", to_addr)
        return SendResult(
            email=to_addr, status=STATUS_ACCEPTED,
            error_summary="SMTP accepted (not a delivery confirmation).",
            timestamp=_now_iso(), mode="real",
        )

    # ── Auth failure: fatal regardless of stage ───────────────────────────────
    except smtplib.SMTPAuthenticationError:
        raise _FatalSendError(
            "SMTP authentication failed. "
            "Check GMAIL_ADDRESS and GMAIL_APP_PASSWORD in your .env."
        )

    # ── Rate limit / quota ────────────────────────────────────────────────────
    except smtplib.SMTPResponseException as exc:
        if stage == "send":
            code = exc.smtp_code
            if code in _RATE_LIMIT_CODES or _DAILY_LIMIT_PREFIX in str(exc.smtp_error):
                raise _RateLimitError(
                    f"Rate-limit / quota error (code {code}). "
                    "Stop sending and try again later."
                )
            return SendResult(
                email=to_addr, status=STATUS_UNKNOWN,
                error_summary=f"SMTP error at send (code {code}). Do not auto-retry.",
                timestamp=_now_iso(), mode="real",
            )
        # At connect/starttls/login: message not sent → Failed
        summary = f"Failed at {stage}: {_class_name(exc)}"
        raise _ConnectionFatalError(summary)

    # ── Recipient refused: non-fatal, this recipient only ─────────────────────
    except smtplib.SMTPRecipientsRefused:
        return SendResult(
            email=to_addr, status=STATUS_FAILED,
            error_summary="Recipient address refused by server.",
            timestamp=_now_iso(), mode="real",
        )

    # ── Connection-level errors ───────────────────────────────────────────────
    except (
        smtplib.SMTPServerDisconnected,
        smtplib.SMTPConnectError,
        TimeoutError,
        OSError,
        ssl.SSLError,
    ) as exc:
        exc_name = _class_name(exc)
        if stage == "send":
            # After DATA: ambiguous — message may have been received.
            return SendResult(
                email=to_addr, status=STATUS_UNKNOWN,
                error_summary=(
                    f"Connection error at send ({exc_name}). Do not auto-retry."
                ),
                timestamp=_now_iso(), mode="real",
            )
        # Before send: message was never sent → Failed, stop batch.
        summary = f"Failed at {stage}: {exc_name}"
        raise _ConnectionFatalError(summary)

    except Exception as exc:
        exc_name = _class_name(exc)
        if stage == "send":
            return SendResult(
                email=to_addr, status=STATUS_UNKNOWN,
                error_summary=f"Unexpected error at send ({exc_name}). Do not auto-retry.",
                timestamp=_now_iso(), mode="real",
            )
        summary = f"Failed at {stage}: {exc_name}"
        raise _ConnectionFatalError(summary)


# ── Batch runner ──────────────────────────────────────────────────────────────

def run_batch(
    prepared_campaign: PreparedCampaign,
    config: SmtpConfig | None,
    mode: str,
    delay_seconds: int | None = None,
    already_sent_keys: set | None = None,
    on_result: Callable[[SendResult], None] | None = None,
    should_stop: Callable[[], bool] | None = None,
    _sleep: Callable[[float], None] | None = None,
) -> list[SendResult]:
    """Send one email per ready recipient. Returns all SendResults.

    already_sent_keys is updated ONLY when status is SMTP Accepted or
    Unknown/Needs Review in real mode (message may have been received).
    Failed, Pending, and Simulated results never enter already_sent_keys.
    """
    from .attachments import build_attachment
    from .message_builder import build_message

    if _sleep is None:
        _sleep = time.sleep

    if already_sent_keys is None:
        already_sent_keys = set()
    results: list[SendResult] = []
    max_recip = get_env_int(ENV_MAX_RECIPIENTS_PER_CAMPAIGN, default=100) or 100

    # Pre-flight checks for real mode
    if mode == "real":
        if config is None:
            raise SmtpConfigError("SmtpConfig is required for real mode.")
        if not prepared_campaign.is_sendable:
            raise ValueError(
                "Campaign is not sendable: check resume status and recipient list."
            )
        for r in prepared_campaign.recipients_ready:
            if r.rendered is not None:
                try:
                    ensure_sendable(r.rendered)
                except TemplateError as exc:
                    raise ValueError(
                        f"Recipient {r.email} has unresolved placeholders: {exc}"
                    ) from exc

    ready = prepared_campaign.recipients_ready[:max_recip]

    attachment_data: tuple | None = None
    if prepared_campaign.attach_resume and prepared_campaign.resume_ready:
        try:
            attachment_data = build_attachment()
        except FileNotFoundError:
            attachment_data = None

    def _mark_remaining_pending(from_index: int, reason: str) -> None:
        for rem in ready[from_index:]:
            pend = SendResult(
                email=rem.email, status=STATUS_PENDING,
                error_summary=reason,
                timestamp=_now_iso(), mode=mode,
                recipient_name=rem.name,
            )
            results.append(pend)
            if on_result:
                on_result(pend)

    for i, recipient in enumerate(ready):
        if should_stop and should_stop():
            _mark_remaining_pending(i, "Batch stopped by user.")
            break

        key = recipient.email.lower().strip()
        if key in already_sent_keys:
            res = SendResult(
                email=recipient.email, status=STATUS_PENDING,
                error_summary="Skipped: already sent in this campaign.",
                timestamp=_now_iso(), mode=mode,
                recipient_name=recipient.name,
            )
            results.append(res)
            if on_result:
                on_result(res)
            continue

        rendered = recipient.rendered
        try:
            msg = build_message(
                sender_name=config.sender_name if config else "",
                sender_email=config.sender_address if config else "noreply@test.invalid",
                to_email=recipient.email,
                subject=rendered.subject if rendered else "",
                body=rendered.body if rendered else "",
                attachment=attachment_data,
            )
        except Exception as exc:
            res = SendResult(
                email=recipient.email, status=STATUS_FAILED,
                error_summary=f"Could not build message: {type(exc).__name__}",
                timestamp=_now_iso(), mode=mode,
                recipient_name=recipient.name,
            )
            results.append(res)
            if on_result:
                on_result(res)
            continue

        try:
            res = send_one(msg, config, mode)
            res.recipient_name = recipient.name

        except _FatalSendError as exc:
            fatal_res = SendResult(
                email=recipient.email, status=STATUS_FAILED,
                error_summary=str(exc),
                timestamp=_now_iso(), mode=mode,
                recipient_name=recipient.name,
            )
            results.append(fatal_res)
            if on_result:
                on_result(fatal_res)
            _mark_remaining_pending(i + 1, "Batch stopped: authentication failure.")
            break

        except _ConnectionFatalError as exc:
            fatal_res = SendResult(
                email=recipient.email, status=STATUS_FAILED,
                error_summary=str(exc),
                timestamp=_now_iso(), mode=mode,
                recipient_name=recipient.name,
            )
            results.append(fatal_res)
            if on_result:
                on_result(fatal_res)
            _mark_remaining_pending(i + 1, "Batch stopped: connection failure.")
            break

        except _RateLimitError as exc:
            rate_res = SendResult(
                email=recipient.email, status=STATUS_FAILED,
                error_summary=str(exc),
                timestamp=_now_iso(), mode=mode,
                recipient_name=recipient.name,
            )
            results.append(rate_res)
            if on_result:
                on_result(rate_res)
            _mark_remaining_pending(i + 1, "Batch stopped: rate-limit or quota error.")
            break

        results.append(res)
        if on_result:
            on_result(res)

        # Update already_sent_keys ONLY for SMTP Accepted or Unknown/Needs Review in real mode.
        # Failed, Pending, Simulated never count.
        if mode == "real" and res.status in (STATUS_ACCEPTED, STATUS_UNKNOWN):
            already_sent_keys.add(key)

        # Delay between sends (not after the last one)
        if i < len(ready) - 1:
            eff_delay = delay_seconds if delay_seconds is not None else (
                config.send_delay_seconds if config else 0
            )
            if eff_delay > 0:
                _sleep(eff_delay)

    return results
