"""SMTP connection checker. Tests connect + STARTTLS/SSL + login ONLY.
Sends NO email. Prints "OK" or "FAILED at <stage>: <ExceptionClassName>".
NEVER prints password, address, or any secret value.

Run from the project root:
    python scripts/smtp_check.py
"""
from __future__ import annotations

import smtplib
import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from outreachiq.email_tools.smtp_config import SmtpConfigError, load_smtp_config
from outreachiq.config import ensure_dirs

_SSL_PORT = 465


def check_connection() -> None:
    ensure_dirs()
    try:
        config = load_smtp_config()
    except SmtpConfigError as exc:
        print(f"FAILED at config: {type(exc).__name__}")
        sys.exit(1)

    stage = "connect"
    ssl_ctx = ssl.create_default_context()
    use_ssl = (config.port == _SSL_PORT)

    try:
        if use_ssl:
            stage = "connect"
            smtp = smtplib.SMTP_SSL(
                config.host, config.port, timeout=30, context=ssl_ctx
            )
            with smtp:
                smtp.ehlo()
                stage = "login"
                smtp.login(config.sender_address, config.get_password())
                smtp.quit()
        else:
            stage = "connect"
            with smtplib.SMTP(config.host, config.port, timeout=30) as smtp:
                smtp.ehlo()
                stage = "starttls"
                smtp.starttls(context=ssl_ctx)
                smtp.ehlo()
                stage = "login"
                smtp.login(config.sender_address, config.get_password())
                smtp.quit()

        print("OK")

    except smtplib.SMTPAuthenticationError as exc:
        print(f"FAILED at {stage}: {type(exc).__name__}")
        sys.exit(1)

    except (
        smtplib.SMTPServerDisconnected,
        smtplib.SMTPConnectError,
        smtplib.SMTPResponseException,
        TimeoutError,
        OSError,
        ssl.SSLError,
    ) as exc:
        print(f"FAILED at {stage}: {type(exc).__name__}")
        sys.exit(1)

    except Exception as exc:
        print(f"FAILED at {stage}: {type(exc).__name__}")
        sys.exit(1)


if __name__ == "__main__":
    check_connection()
