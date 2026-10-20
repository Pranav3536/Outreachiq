"""Phase 5a tests: template engine + placeholder rendering (synthetic only)."""
from __future__ import annotations

import pytest

from outreachiq.email_tools.placeholders import (
    FALLBACKS,
    RenderResult,
    TemplateError,
    ensure_sendable,
    find_placeholders,
    render,
    render_for_contact,
    validate_template,
)
from outreachiq.email_tools.templates import (
    DEFAULT_BODY,
    DEFAULT_SUBJECT,
    delete_template,
    list_templates,
    load_template,
    load_working,
    save_template,
    save_working,
)


# ── default template content ─────────────────────────────────────────────────

def test_default_subject_not_empty():
    assert DEFAULT_SUBJECT.strip()


def test_default_body_contains_name_placeholder():
    assert "{Name}" in DEFAULT_BODY or "{name}" in DEFAULT_BODY.lower()


def test_default_body_contains_company_placeholder():
    assert "{Company}" in DEFAULT_BODY or "{company}" in DEFAULT_BODY.lower()


def test_default_body_mentions_pranav():
    assert "Pranav" in DEFAULT_BODY


def test_default_body_no_job_vacancy_claim():
    lower = DEFAULT_BODY.lower()
    assert "vacancy" not in lower
    assert "job opening" not in lower
    assert "job vacancy" not in lower


# ── find_placeholders ─────────────────────────────────────────────────────────

def test_find_placeholders_basic():
    phs = find_placeholders("Hello {Name}, welcome to {Company}!")
    assert phs == {"Name", "Company"}


def test_find_placeholders_empty():
    assert find_placeholders("No placeholders here.") == set()


def test_find_placeholders_literal_braces_ignored():
    # Multi-word content or numeric keys — not valid placeholders.
    phs = find_placeholders("This is not a {placeholder with spaces} or {123}.")
    assert "placeholder with spaces" not in phs
    # Single-word still matched
    assert find_placeholders("{Word}") == {"Word"}


# ── render ────────────────────────────────────────────────────────────────────

def test_render_correct_replacement():
    contact = {"name": "Alice Johnson", "company": "Acme Corp", "title": "HR Manager"}
    rendered, fallbacks, unresolved = render("Dear {Name}, at {Company}.", contact)
    assert rendered == "Dear Alice Johnson, at Acme Corp."
    assert fallbacks == []
    assert unresolved == []


def test_render_case_insensitive():
    contact = {"name": "Bob", "company": "Beta"}
    text = "Dear {NAME}, welcome to {COMPANY}."
    rendered, _, _ = render(text, contact)
    assert "Bob" in rendered
    assert "Beta" in rendered


def test_render_prefers_clean_column():
    contact = {"name": "  alice  ", "name_clean": "Alice"}
    rendered, _, _ = render("{Name}", contact)
    assert rendered == "Alice"


def test_render_fallback_used_for_blank_name():
    contact = {"name": "", "company": "Acme"}
    rendered, fallbacks, unresolved = render("Dear {Name},", contact)
    assert rendered == f"Dear {FALLBACKS['name']},"
    assert "Name" in fallbacks
    assert unresolved == []


def test_render_fallback_reported():
    contact = {"company": "Acme"}   # no name key at all
    _, fallbacks, _ = render("{Name}", contact)
    assert "Name" in fallbacks


def test_render_unknown_placeholder_in_unresolved():
    contact = {"name": "Alice", "company": "Acme"}
    rendered, fallbacks, unresolved = render("Subject: {UNKNOWN_FIELD}", contact)
    assert "UNKNOWN_FIELD" in unresolved
    assert "{UNKNOWN_FIELD}" in rendered   # left untouched
    assert fallbacks == []


def test_render_extra_column_placeholder():
    contact = {"name": "Alice", "company": "Acme", "linkedin": "linkedin.com/in/alice"}
    rendered, _, unresolved = render("Connect: {linkedin}", contact)
    assert "linkedin.com/in/alice" in rendered
    assert unresolved == []


def test_render_literal_braces_untouched():
    contact = {"name": "Alice"}
    # {123} is not a valid placeholder (starts with digit)
    text = "Value: {123} and {Name}"
    rendered, _, _ = render(text, contact)
    assert "{123}" in rendered
    assert "Alice" in rendered


# ── render_for_contact ────────────────────────────────────────────────────────

def test_render_for_contact_returns_render_result():
    contact = {"name": "Alice", "company": "Acme", "title": "Engineer"}
    result = render_for_contact("{Name}", "Dear {Name} at {Company},", contact)
    assert isinstance(result, RenderResult)
    assert "Alice" in result.subject
    assert "Alice" in result.body
    assert "Acme" in result.body


def test_render_for_contact_unresolved_aggregated():
    contact = {"name": "Alice"}
    result = render_for_contact("{BadField}", "Body {AnotherBad}", contact)
    assert "BadField" in result.unresolved or "AnotherBad" in result.unresolved


# ── ensure_sendable ───────────────────────────────────────────────────────────

def test_ensure_sendable_passes_clean():
    result = RenderResult(subject="Hello", body="Body text")
    ensure_sendable(result)   # must not raise


def test_ensure_sendable_raises_on_unresolved():
    result = RenderResult(subject="Hi", body="Body", unresolved=["UNKNOWN"])
    with pytest.raises(TemplateError):
        ensure_sendable(result)


def test_ensure_sendable_raises_on_empty_subject():
    result = RenderResult(subject="   ", body="Body text")
    with pytest.raises(TemplateError):
        ensure_sendable(result)


def test_ensure_sendable_raises_on_empty_body():
    result = RenderResult(subject="Hi", body="")
    with pytest.raises(TemplateError):
        ensure_sendable(result)


# ── validate_template ─────────────────────────────────────────────────────────

def test_validate_template_clean():
    problems = validate_template(
        "Hi {Name}", "Dear {Name}, at {Company}.",
        available_columns=["name", "company", "title"]
    )
    assert problems == []


def test_validate_template_empty_subject():
    problems = validate_template("", "Some body.", available_columns=["name"])
    assert any("Subject" in p for p in problems)


def test_validate_template_empty_body():
    problems = validate_template("Hi", "", available_columns=["name"])
    assert any("Body" in p for p in problems)


def test_validate_template_unknown_placeholder():
    problems = validate_template(
        "Hi {Name}", "See {UnknownField}.",
        available_columns=["name", "company"]
    )
    assert any("UnknownField" in p for p in problems)


# ── save / load / list / delete ───────────────────────────────────────────────

def test_save_and_load_template(tmp_path, monkeypatch):
    import outreachiq.email_tools.templates as tmpl_mod
    monkeypatch.setattr(tmpl_mod, "EMAIL_TEMPLATES_DIR", tmp_path)
    # Reload path constants that close over the module attribute
    from outreachiq.config import EMAIL_TEMPLATES_DIR as _
    save_template("My Template", "Subject here", "Body here")
    loaded = load_template("My Template")
    assert loaded["subject"] == "Subject here"
    assert loaded["body"] == "Body here"
    assert loaded["name"] == "My Template"


def test_list_templates(tmp_path, monkeypatch):
    import outreachiq.email_tools.templates as tmpl_mod
    monkeypatch.setattr(tmpl_mod, "EMAIL_TEMPLATES_DIR", tmp_path)
    assert list_templates() == []
    save_template("Alpha", "s", "b")
    save_template("Beta", "s", "b")
    names = list_templates()
    assert "Alpha" in names
    assert "Beta" in names
    assert "_working" not in names


def test_delete_template(tmp_path, monkeypatch):
    import outreachiq.email_tools.templates as tmpl_mod
    monkeypatch.setattr(tmpl_mod, "EMAIL_TEMPLATES_DIR", tmp_path)
    save_template("ToDelete", "s", "b")
    assert "ToDelete" in list_templates()
    delete_template("ToDelete")
    assert "ToDelete" not in list_templates()


def test_delete_nonexistent_template_is_silent(tmp_path, monkeypatch):
    import outreachiq.email_tools.templates as tmpl_mod
    monkeypatch.setattr(tmpl_mod, "EMAIL_TEMPLATES_DIR", tmp_path)
    delete_template("ghost")   # must not raise


def test_save_template_empty_name_raises(tmp_path, monkeypatch):
    import outreachiq.email_tools.templates as tmpl_mod
    monkeypatch.setattr(tmpl_mod, "EMAIL_TEMPLATES_DIR", tmp_path)
    with pytest.raises(ValueError):
        save_template("", "s", "b")


def test_load_missing_template_raises(tmp_path, monkeypatch):
    import outreachiq.email_tools.templates as tmpl_mod
    monkeypatch.setattr(tmpl_mod, "EMAIL_TEMPLATES_DIR", tmp_path)
    with pytest.raises(FileNotFoundError):
        load_template("nonexistent")


def test_working_copy_persists(tmp_path, monkeypatch):
    import outreachiq.email_tools.templates as tmpl_mod
    monkeypatch.setattr(tmpl_mod, "EMAIL_TEMPLATES_DIR", tmp_path)
    monkeypatch.setattr(tmpl_mod, "_WORKING_FILE", tmp_path / "_working.json")
    save_working("My subject", "My body")
    w = load_working()
    assert w["subject"] == "My subject"
    assert w["body"] == "My body"


def test_working_copy_returns_defaults_when_missing(tmp_path, monkeypatch):
    import outreachiq.email_tools.templates as tmpl_mod
    monkeypatch.setattr(tmpl_mod, "EMAIL_TEMPLATES_DIR", tmp_path)
    monkeypatch.setattr(tmpl_mod, "_WORKING_FILE", tmp_path / "_no_file.json")
    w = load_working()
    assert w["subject"] == DEFAULT_SUBJECT
    assert w["body"] == DEFAULT_BODY
