"""Local credential storage: bcrypt-hashed passwords only.

The credentials file holds username + bcrypt hash only. Plaintext passwords
are never stored, printed, or logged.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import bcrypt

from ..config import AUTH_DIR

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 8
CREDENTIALS_FILE: Path = AUTH_DIR / "credentials.json"


def _read_credentials() -> dict:
    """Read and parse credentials.json. Returns {} if missing or malformed."""
    if not CREDENTIALS_FILE.exists():
        return {}
    try:
        with CREDENTIALS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError):
        logger.warning("credentials.json could not be read; treating as empty")
        return {}


def _write_credentials(data: dict) -> None:
    """Write credentials.json atomically; create parent dir; restrict perms."""
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = CREDENTIALS_FILE.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(CREDENTIALS_FILE)
    try:
        CREDENTIALS_FILE.chmod(0o600)
    except OSError:
        # Permission restriction is best-effort (especially on Windows).
        pass


def _users(data: dict) -> dict:
    return data.get("users", {}) if isinstance(data, dict) else {}


def user_exists(username: str) -> bool:
    """True if a user with the given username is registered locally."""
    return username in _users(_read_credentials())


def list_users() -> list[str]:
    """Return the usernames of all registered local users."""
    return list(_users(_read_credentials()).keys())


def create_user(username: str, password: str) -> None:
    """Create a user with a bcrypt-hashed password.

    Raises ValueError if the username is empty, the user already exists,
    or the password is shorter than MIN_PASSWORD_LENGTH.
    Never stores, prints, or logs the plaintext password.
    """
    if not username or not username.strip():
        raise ValueError("Username must not be empty.")
    username = username.strip()
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
        )
    data = _read_credentials()
    users = data.setdefault("users", {})
    if username in users:
        raise ValueError(f"User '{username}' already exists.")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    users[username] = {"password_hash": hashed}
    _write_credentials(data)


def verify(username: str, password: str) -> bool:
    """Return True if password matches the stored bcrypt hash.

    Pure and side-effect free (no delay, no logging). Returns False for
    unknown users or wrong passwords.
    """
    users = _users(_read_credentials())
    if username not in users:
        return False
    stored = users[username].get("password_hash", "")
    if not stored:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    except (ValueError, TypeError):
        return False
