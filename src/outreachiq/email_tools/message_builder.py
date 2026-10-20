"""Build RFC-compliant EmailMessage objects for outreach emails.

Safety rules:
- One recipient in To only; no Cc, Bcc, or multiple addresses.
- Newlines in subject or recipient addresses are rejected (header injection).
- PDF attachment is added as application/pdf when provided.
- No credential values ever appear in this module.
"""
from __future__ import annotations

import re
from email.message import EmailMessage

_NEWLINE_RE = re.compile(r"[\r\n]")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class MessageBuildError(Exception):
    """Raised when the message cannot be built safely."""


def _reject_newlines(value: str, field_name: str) -> None:
    if _NEWLINE_RE.search(value):
        raise MessageBuildError(
            f"Header injection attempt detected: newline in {field_name}."
        )


def build_message(
    sender_name: str,
    sender_email: str,
    to_email: str,
    subject: str,
    body: str,
    attachment: tuple[bytes, str, str] | None = None,
) -> EmailMessage:
    """Build an EmailMessage.

    attachment: optional (bytes, filename, mimetype) from build_attachment().
    Raises MessageBuildError on invalid inputs.
    """
    # Validate / sanitise
    _reject_newlines(subject, "Subject")
    _reject_newlines(to_email, "To")
    _reject_newlines(sender_email, "From")

    if not subject.strip():
        raise MessageBuildError("Subject must not be empty.")
    if not body.strip():
        raise MessageBuildError("Body must not be empty.")
    if not _EMAIL_RE.match(to_email.strip()):
        raise MessageBuildError(f"Invalid recipient address: '{to_email}'.")
    if not _EMAIL_RE.match(sender_email.strip()):
        raise MessageBuildError(f"Invalid sender address: '{sender_email}'.")

    from_header = (
        f"{sender_name} <{sender_email}>" if sender_name.strip() else sender_email
    )

    msg = EmailMessage()
    msg["From"] = from_header
    msg["To"] = to_email.strip()          # exactly one recipient
    msg["Subject"] = subject.strip()
    # Explicitly no Cc or Bcc headers.
    msg.set_content(body)

    if attachment is not None:
        att_bytes, att_name, att_mime = attachment
        maintype, subtype = att_mime.split("/", 1)
        msg.add_attachment(att_bytes, maintype=maintype, subtype=subtype,
                           filename=att_name)

    return msg
