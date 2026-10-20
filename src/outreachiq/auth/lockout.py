"""Per-session login attempt tracking with temporary lockout.

This module is Streamlit-free so it can be unit-tested directly. The UI layer
keeps one LoginAttemptTracker instance in st.session_state per browser session.
"""
from __future__ import annotations

import time

DEFAULT_MAX_ATTEMPTS = 5
DEFAULT_LOCKOUT_SECONDS = 30


class LoginAttemptTracker:
    """Counts failed login attempts and locks temporarily after a threshold."""

    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        lockout_seconds: int = DEFAULT_LOCKOUT_SECONDS,
    ) -> None:
        self.max_attempts = max_attempts
        self.lockout_seconds = lockout_seconds
        self._attempts = 0
        self._locked_until: float | None = None

    def record_failure(self) -> None:
        self._attempts += 1
        if self._attempts >= self.max_attempts:
            self._locked_until = time.time() + self.lockout_seconds

    def record_success(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._attempts = 0
        self._locked_until = None

    def is_locked(self) -> bool:
        if self._locked_until is None:
            return False
        if time.time() >= self._locked_until:
            # Lockout expired: clear and allow retries.
            self._locked_until = None
            self._attempts = 0
            return False
        return True

    def remaining_attempts(self) -> int:
        return max(0, self.max_attempts - self._attempts)

    def lockout_remaining_seconds(self) -> int:
        if self._locked_until is None:
            return 0
        return max(0, int(self._locked_until - time.time()))
