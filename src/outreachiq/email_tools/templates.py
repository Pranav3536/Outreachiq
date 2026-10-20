"""Named template persistence and the built-in default internship application template.

Templates are stored as JSON files in runtime/email_templates/.
Writes are atomic (write to .tmp, then rename).
A separate "current working template" file persists in-progress edits.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ..config import EMAIL_TEMPLATES_DIR

logger = logging.getLogger(__name__)

# ── Default internship-application template ───────────────────────────────────

DEFAULT_SUBJECT = "Application for Data & Analytics Opportunities"

DEFAULT_BODY = """\
Dear {Name},

I hope this message finds you well. I am Pranav Shrivastav, a B.Tech student in \
Computer Science with a keen interest in Data Analytics, Business Analytics, and \
Data Science. I am writing to express my interest in any suitable opportunities at \
{Company}.

Over the course of my studies I have built hands-on skills in Python, SQL, Excel, \
and Power BI, and have worked on several machine learning projects as part of my \
coursework and personal exploration. I am eager to apply these skills in a \
practical setting where I can contribute meaningfully while continuing to grow.

Please find my resume attached for your review. I would welcome the opportunity to \
discuss how my background might be a good fit for {Company}.

Best regards,
Pranav Shrivastav\
"""

# ── Internal paths ────────────────────────────────────────────────────────────

_WORKING_FILE = EMAIL_TEMPLATES_DIR / "_working.json"
_EXTENSION = ".json"


def _ensure_dir() -> None:
    EMAIL_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)


def _template_path(name: str) -> Path:
    safe = "".join(c if (c.isalnum() or c in "-_ ") else "_" for c in name).strip()
    return EMAIL_TEMPLATES_DIR / f"{safe}{_EXTENSION}"


def _atomic_write(path: Path, data: dict) -> None:
    _ensure_dir()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# ── CRUD ──────────────────────────────────────────────────────────────────────

def list_templates() -> list[str]:
    """Return template names (no extension), sorted. Excludes _working."""
    _ensure_dir()
    return sorted(
        p.stem
        for p in EMAIL_TEMPLATES_DIR.glob(f"*{_EXTENSION}")
        if p.stem != "_working"
    )


def save_template(name: str, subject: str, body: str) -> Path:
    """Save a named template. Raises ValueError if name is empty."""
    if not name or not name.strip():
        raise ValueError("Template name must not be empty.")
    path = _template_path(name)
    _atomic_write(path, {"name": name, "subject": subject, "body": body})
    return path


def load_template(name: str) -> dict:
    """Load a named template. Returns dict with keys name/subject/body.

    Raises FileNotFoundError if the template does not exist.
    """
    path = _template_path(name)
    if not path.exists():
        raise FileNotFoundError(f"Template '{name}' not found.")
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "name": data.get("name", name),
        "subject": data.get("subject", ""),
        "body": data.get("body", ""),
    }


def delete_template(name: str) -> None:
    """Delete a named template. Silent no-op if it doesn't exist."""
    path = _template_path(name)
    if path.exists():
        path.unlink()


# ── Working-copy persistence (survives session restart) ───────────────────────

def save_working(subject: str, body: str) -> None:
    """Persist the in-progress template edit (not a named template)."""
    _atomic_write(_WORKING_FILE, {"subject": subject, "body": body})


def load_working() -> dict:
    """Return the last-saved working copy, or the defaults if none exists."""
    if _WORKING_FILE.exists():
        try:
            data = json.loads(_WORKING_FILE.read_text(encoding="utf-8"))
            return {"subject": data.get("subject", DEFAULT_SUBJECT),
                    "body": data.get("body", DEFAULT_BODY)}
        except Exception:
            pass
    return {"subject": DEFAULT_SUBJECT, "body": DEFAULT_BODY}
