"""AppTest: login screen + all 7 pages render without exceptions."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
PAGES_DIR = ROOT / "src" / "outreachiq" / "ui" / "pages"
PAGES = [
    "overview.py",
    "contact_lab.py",
    "designation_explorer.py",
    "ml_nlp.py",
    "email_studio.py",
    "campaign_manager.py",
    "history_reports.py",
]


def test_login_and_all_pages_render():
    # Login screen: no local user exists, so it shows the setup hint.
    at = AppTest.from_file(str(APP), default_timeout=10)
    at.run()
    assert not at.exception, f"Login screen raised: {at.exception}"
    assert len(at.title) >= 1, "Login screen did not render a title"

    # All 7 pages render without exception (and each shows its header title).
    for name in PAGES:
        at = AppTest.from_file(str(PAGES_DIR / name), default_timeout=10)
        at.run()
        assert not at.exception, f"{name} raised: {at.exception}"
        assert len(at.title) >= 1, f"{name} did not render a header"
