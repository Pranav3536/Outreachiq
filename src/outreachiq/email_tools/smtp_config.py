"""SMTP configuration loader. Passwords are NEVER logged, printed, or exposed.

repr/str of SmtpConfig masks the app password completely.
credentials_status() returns only key names, never values.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..config import (
    ENV_GMAIL_ADDRESS,
    ENV_GMAIL_APP_PASSWORD,
    ENV_SEND_DELAY_SECONDS,
    ENV_SENDER_DISPLAY_NAME,
    ENV_SMTP_HOST,
    ENV_SMTP_PORT,
    get_env,
    get_env_int,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_REQUIRED_NAMES = (
    ENV_GMAIL_ADDRESS,
    ENV_GMAIL_APP_PASSWORD,
)


class SmtpConfigError(Exception):
    """Raised for missing or invalid SMTP configuration. Never contains the password."""


@dataclass
class SmtpConfig:
    sender_address: str
    _app_password: str          # private; never exposed via str/repr
    sender_name: str
    host: str
    port: int
    send_delay_seconds: int

    def __repr__(self) -> str:          # noqa: D105
        return (
            f"SmtpConfig(sender={self.sender_address!r}, "
            f"name={self.sender_name!r}, "
            f"host={self.host!r}, port={self.port}, "
            f"delay={self.send_delay_seconds}s, "
            f"password=<masked>)"
        )

    def __str__(self) -> str:           # noqa: D105
        return self.__repr__()

    # Access the password only through this method so callsites are explicit.
    def get_password(self) -> str:
        return self._app_password

    @property
    def from_header(self) -> str:
        if self.sender_name:
            return f"{self.sender_name} <{self.sender_address}>"
        return self.sender_address


def load_smtp_config() -> SmtpConfig:
    """Load SMTP config from environment.

    Raises SmtpConfigError if required variables are missing or the sender
    address is not a valid email. Never includes credential values in errors.
    """
    missing = [n for n in _REQUIRED_NAMES if not get_env(n)]
    if missing:
        raise SmtpConfigError(
            f"Missing required SMTP configuration: {missing}. "
            "Set them in your .env file."
        )

    address = (get_env(ENV_GMAIL_ADDRESS) or "").strip()
    if not _EMAIL_RE.match(address):
        raise SmtpConfigError(
            f"GMAIL_ADDRESS '{address}' does not look like a valid email address."
        )

    # Strip spaces from app password (common copy-paste artifact)
    raw_pw = get_env(ENV_GMAIL_APP_PASSWORD) or ""
    password = raw_pw.replace(" ", "")

    return SmtpConfig(
        sender_address=address,
        _app_password=password,
        sender_name=(get_env(ENV_SENDER_DISPLAY_NAME) or "").strip(),
        host=get_env(ENV_SMTP_HOST) or "smtp.gmail.com",
        port=get_env_int(ENV_SMTP_PORT, default=587) or 587,
        send_delay_seconds=get_env_int(ENV_SEND_DELAY_SECONDS, default=5) or 5,
    )


def credentials_status() -> dict:
    """Return configuration status using only key names, never values."""
    missing = [n for n in _REQUIRED_NAMES if not get_env(n)]
    return {
        "configured": len(missing) == 0,
        "missing": missing,
    }
