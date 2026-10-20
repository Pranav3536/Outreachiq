"""Tests for the local auth module: bcrypt hashing, verify, lockout, no plaintext.

All tests use synthetic passwords and a temp credentials file so the real
runtime/auth/credentials.json is never touched.
"""
from __future__ import annotations

import json

import pytest

from outreachiq.auth import (
    LoginAttemptTracker,
    create_user,
    user_exists,
    verify,
)
from outreachiq.auth import credentials as creds_mod


@pytest.fixture
def isolated_creds(monkeypatch, tmp_path):
    """Point credentials storage at a temp file so tests never touch real data."""
    creds_file = tmp_path / "credentials.json"
    monkeypatch.setattr(creds_mod, "CREDENTIALS_FILE", creds_file)
    return creds_file


def test_create_user_then_verify(isolated_creds):
    create_user("alice", "correcthorse")
    assert user_exists("alice")
    assert verify("alice", "correcthorse") is True


def test_wrong_password_fails(isolated_creds):
    create_user("alice", "correcthorse")
    assert verify("alice", "wrongpassword") is False


def test_unknown_user_fails(isolated_creds):
    assert verify("ghost", "anything") is False


def test_short_password_rejected(isolated_creds):
    with pytest.raises(ValueError):
        create_user("bob", "short")
    assert not user_exists("bob")


def test_duplicate_user_rejected(isolated_creds):
    create_user("alice", "correcthorse")
    with pytest.raises(ValueError):
        create_user("alice", "anotherpass")


def test_empty_username_rejected(isolated_creds):
    with pytest.raises(ValueError):
        create_user("   ", "validpassword")


def test_credentials_file_has_no_plaintext(isolated_creds):
    secret = "supersecret123"
    create_user("carol", secret)
    raw = isolated_creds.read_text(encoding="utf-8")
    assert secret not in raw  # plaintext never persisted
    data = json.loads(raw)
    entry = data["users"]["carol"]
    assert "password_hash" in entry
    assert "password" not in entry  # no plaintext key
    assert entry["password_hash"].startswith("$2")  # bcrypt hash


def test_lockout_after_five_failures():
    tracker = LoginAttemptTracker(max_attempts=5, lockout_seconds=60)
    for _ in range(5):
        tracker.record_failure()
    assert tracker.is_locked() is True
    assert tracker.remaining_attempts() == 0


def test_lockout_not_triggered_below_threshold():
    tracker = LoginAttemptTracker(max_attempts=5, lockout_seconds=60)
    for _ in range(4):
        tracker.record_failure()
    assert tracker.is_locked() is False
    assert tracker.remaining_attempts() == 1


def test_success_resets_tracker():
    tracker = LoginAttemptTracker(max_attempts=5, lockout_seconds=60)
    tracker.record_failure()
    tracker.record_failure()
    tracker.record_success()
    assert tracker.is_locked() is False
    assert tracker.remaining_attempts() == 5
