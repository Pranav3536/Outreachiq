"""Central configuration: project paths and environment-variable access.

Never prints or logs secret values. The app starts fine when .env is missing
(python-dotenv's load_dotenv is a no-op in that case).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = .../outreach-iq (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Load .env if present; no error if missing.
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# --- Paths ---
DATA_DIR = PROJECT_ROOT / "data"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
UPLOADS_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
LABELLED_DIR = DATA_DIR / "labelled"
CAMPAIGNS_DIR = RUNTIME_DIR / "campaigns"
RESUME_DIR = RUNTIME_DIR / "resume"
MODELS_DIR = RUNTIME_DIR / "models"
LOGS_DIR = RUNTIME_DIR / "logs"
AUTH_DIR = RUNTIME_DIR / "auth"
EMAIL_TEMPLATES_DIR = RUNTIME_DIR / "email_templates"

# --- Environment variable names ---
ENV_GMAIL_ADDRESS = "GMAIL_ADDRESS"
ENV_GMAIL_APP_PASSWORD = "GMAIL_APP_PASSWORD"
ENV_SENDER_DISPLAY_NAME = "SENDER_DISPLAY_NAME"
ENV_SMTP_HOST = "SMTP_HOST"
ENV_SMTP_PORT = "SMTP_PORT"
ENV_MAX_RECIPIENTS_PER_CAMPAIGN = "MAX_RECIPIENTS_PER_CAMPAIGN"
ENV_SEND_DELAY_SECONDS = "SEND_DELAY_SECONDS"

ALL_ENV_NAMES = (
    ENV_GMAIL_ADDRESS,
    ENV_GMAIL_APP_PASSWORD,
    ENV_SENDER_DISPLAY_NAME,
    ENV_SMTP_HOST,
    ENV_SMTP_PORT,
    ENV_MAX_RECIPIENTS_PER_CAMPAIGN,
    ENV_SEND_DELAY_SECONDS,
)

# Keys whose values are secrets and must never be printed or logged.
SECRET_NAMES = frozenset({ENV_GMAIL_APP_PASSWORD})

# Non-secret defaults (stored as strings; convert at call sites as needed).
_DEFAULTS = {
    ENV_SMTP_HOST: "smtp.gmail.com",
    ENV_SMTP_PORT: "587",
    ENV_MAX_RECIPIENTS_PER_CAMPAIGN: "100",
    ENV_SEND_DELAY_SECONDS: "5",
}


def ensure_dirs() -> None:
    """Create runtime and data directories if they are missing."""
    for d in (
        UPLOADS_DIR, PROCESSED_DIR, LABELLED_DIR,
        CAMPAIGNS_DIR, RESUME_DIR, MODELS_DIR, LOGS_DIR, AUTH_DIR,
        EMAIL_TEMPLATES_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)


def is_secret(name: str) -> bool:
    """True if the named env var holds a secret that must never be logged."""
    return name in SECRET_NAMES


def get_env(name: str, default: str | None = None) -> str | None:
    """Return an env var value, applying built-in defaults for non-secrets."""
    if default is None and not is_secret(name) and name in _DEFAULTS:
        default = _DEFAULTS[name]
    return os.environ.get(name, default)


def get_env_int(name: str, default: int | None = None) -> int | None:
    """Return an env var as int, or default if missing/invalid."""
    raw = get_env(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def is_env_set(name: str) -> bool:
    return bool(os.environ.get(name))
