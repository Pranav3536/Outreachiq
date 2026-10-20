"""PDF resume management: validate, save, retrieve, delete.

build_attachment() returns the data needed by the SMTP layer (Phase 6a).
The resume content is never read for display — only existence/metadata is shown.
"""
from __future__ import annotations

import os
from pathlib import Path

from ..config import RESUME_DIR

MAX_RESUME_BYTES = 5 * 1024 * 1024          # 5 MB
_RESUME_FILENAME = "default_resume.pdf"
_PDF_MAGIC = b"%PDF"


def validate_resume(file_bytes: bytes, filename: str) -> tuple[bool, str]:
    """Return (ok, message). Checks extension, magic bytes, size, safe name."""
    # No path separators allowed in filename
    if "/" in filename or "\\" in filename or ".." in filename:
        return False, "Filename must not contain path separators."
    suffix = Path(filename).suffix.lower()
    if suffix != ".pdf":
        return False, f"Only .pdf files are accepted (got '{suffix or '(none)'}')."
    if not file_bytes[:4] == _PDF_MAGIC:
        return False, "File does not appear to be a valid PDF (missing %PDF header)."
    if len(file_bytes) > MAX_RESUME_BYTES:
        size_mb = len(file_bytes) / (1024 * 1024)
        return False, f"File is too large ({size_mb:.1f} MB). Maximum is 5 MB."
    return True, "OK"


def save_resume(file_bytes: bytes) -> Path:
    """Save bytes atomically to runtime/resume/default_resume.pdf (replaces old)."""
    RESUME_DIR.mkdir(parents=True, exist_ok=True)
    dest = RESUME_DIR / _RESUME_FILENAME
    tmp = dest.with_suffix(".tmp")
    tmp.write_bytes(file_bytes)
    tmp.replace(dest)
    return dest


def get_resume_path() -> Path:
    return RESUME_DIR / _RESUME_FILENAME


def resume_exists() -> bool:
    return get_resume_path().exists()


def resume_meta() -> dict | None:
    """Return {filename, size_bytes, mtime} or None if no resume saved."""
    p = get_resume_path()
    if not p.exists():
        return None
    stat = p.stat()
    return {
        "filename": _RESUME_FILENAME,
        "size_bytes": stat.st_size,
        "mtime": stat.st_mtime,
    }


def delete_resume() -> None:
    """Delete the saved resume. Silent no-op if not present."""
    p = get_resume_path()
    if p.exists():
        p.unlink()


def build_attachment(path: Path | None = None) -> tuple[bytes, str, str]:
    """Return (file_bytes, filename, mimetype) for SMTP use (Phase 6a).

    Raises FileNotFoundError if no resume exists at the given (or default) path.
    """
    if path is None:
        path = get_resume_path()
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Resume not found at {path}.")
    return path.read_bytes(), path.name, "application/pdf"
