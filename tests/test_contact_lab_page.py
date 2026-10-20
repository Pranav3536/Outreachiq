"""Render-smoke test for the Contact Data Lab page (no-upload state).

Uses Streamlit's AppTest to run the page script in a simulated context and
confirm it renders without raising an exception. No real files are uploaded.
"""
from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

PAGE = (
    Path(__file__).resolve().parents[1]
    / "src" / "outreachiq" / "ui" / "pages" / "contact_lab.py"
)


def test_contact_lab_page_renders_without_exception():
    at = AppTest.from_file(str(PAGE), default_timeout=10)
    at.run()
    assert not at.exception, f"Contact Data Lab page raised: {at.exception}"
    # With no file uploaded, it should prompt the user to upload a file.
    assert len(at.info) >= 1
