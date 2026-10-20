"""Tests for config: loads without .env, exposes paths and env names, hides secrets."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def clean_env(monkeypatch):
    import outreachiq.config as cfg
    for name in cfg.ALL_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    return cfg


def test_config_loads_without_env(clean_env):
    # Non-secret keys with built-in defaults return defaults.
    assert clean_env.get_env("SMTP_HOST") == "smtp.gmail.com"
    assert clean_env.get_env("SMTP_PORT") == "587"
    assert clean_env.get_env("MAX_RECIPIENTS_PER_CAMPAIGN") == "100"
    assert clean_env.get_env("SEND_DELAY_SECONDS") == "5"
    # Unset keys without defaults return None.
    assert clean_env.get_env("GMAIL_ADDRESS") is None
    assert clean_env.get_env("GMAIL_APP_PASSWORD") is None
    assert clean_env.get_env("SENDER_DISPLAY_NAME") is None


def test_config_is_secret(clean_env):
    assert clean_env.is_secret("GMAIL_APP_PASSWORD") is True
    assert clean_env.is_secret("SMTP_HOST") is False
    assert clean_env.is_secret("GMAIL_ADDRESS") is False


def test_config_paths_are_path_objects(clean_env):
    assert isinstance(clean_env.DATA_DIR, Path)
    assert isinstance(clean_env.RUNTIME_DIR, Path)
    assert clean_env.AUTH_DIR.name == "auth"
    assert clean_env.DATA_DIR.name == "data"
    assert clean_env.RUNTIME_DIR.name == "runtime"


def test_config_env_names_listed(clean_env):
    names = set(clean_env.ALL_ENV_NAMES)
    assert "GMAIL_ADDRESS" in names
    assert "GMAIL_APP_PASSWORD" in names
    assert len(names) == 7


def test_config_get_env_int(clean_env, monkeypatch):
    monkeypatch.setenv("MAX_RECIPIENTS_PER_CAMPAIGN", "250")
    assert clean_env.get_env_int("MAX_RECIPIENTS_PER_CAMPAIGN") == 250
    monkeypatch.setenv("MAX_RECIPIENTS_PER_CAMPAIGN", "notanint")
    assert clean_env.get_env_int("MAX_RECIPIENTS_PER_CAMPAIGN", default=100) == 100
    assert clean_env.get_env_int("UNSET_VAR", default=7) == 7
