"""CLI to create a local OutreachIQ user with a bcrypt-hashed password.

The password is read via getpass (hidden input). It is NEVER passed as a
command-line argument, printed, or logged. Only the bcrypt hash is stored.

Run from the project root:
    python scripts/create_user.py
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

# Make the src package importable when running this script directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outreachiq.auth import (  # noqa: E402
    MIN_PASSWORD_LENGTH,
    create_user,
    user_exists,
)
from outreachiq.config import ensure_dirs  # noqa: E402


def main() -> int:
    ensure_dirs()

    username = input("Choose a username: ").strip()
    if not username:
        print("Error: username must not be empty.")
        return 1
    if user_exists(username):
        print(f"Error: user '{username}' already exists.")
        return 1

    password = getpass.getpass(f"Choose a password (min {MIN_PASSWORD_LENGTH} chars): ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: passwords do not match.")
        return 1

    try:
        create_user(username, password)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"User '{username}' created. Hash stored in runtime/auth/credentials.json.")
    print("The password was not printed, logged, or stored in plaintext.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
