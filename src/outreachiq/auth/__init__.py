"""Local authentication: bcrypt hashing + per-session lockout. No remote backend.

Public API:
    user_exists(username) -> bool
    create_user(username, password) -> None  (raises ValueError on bad input)
    verify(username, password) -> bool
    list_users() -> list[str]
    LoginAttemptTracker  (per-session attempt/lockout helper)
"""
from .credentials import (
    CREDENTIALS_FILE,
    MIN_PASSWORD_LENGTH,
    create_user,
    list_users,
    user_exists,
    verify,
)
from .lockout import (
    DEFAULT_LOCKOUT_SECONDS,
    DEFAULT_MAX_ATTEMPTS,
    LoginAttemptTracker,
)

__all__ = [
    "CREDENTIALS_FILE",
    "MIN_PASSWORD_LENGTH",
    "create_user",
    "list_users",
    "user_exists",
    "verify",
    "LoginAttemptTracker",
    "DEFAULT_MAX_ATTEMPTS",
    "DEFAULT_LOCKOUT_SECONDS",
]
