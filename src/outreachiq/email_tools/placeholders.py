"""Placeholder rendering for email templates.

Only {Word} patterns (a single identifier-like token) are treated as
placeholders. Literal braces that don't match (e.g. JSON, code snippets with
multiple words) are left untouched.

Canonical mapping (case-insensitive):
    {Name}    -> contact["name"] or contact["name_clean"]
    {Company} -> contact["company"] or contact["company_clean"]
    {Title}   -> contact["title"]

Any other {ColumnName} is looked up directly in the contact dict (case-insensitive).

Fallbacks (used when the mapped value is blank/missing):
    Name    -> "Hiring Team"
    Company -> "your organization"
    Title   -> "your role"

Unknown placeholders (not in contact dict and not in FALLBACKS) go into
RenderResult.unresolved and must NEVER be sent silently.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Configurable fallback values ──────────────────────────────────────────────
FALLBACKS: dict[str, str] = {
    "name": "Hiring Team",
    "company": "your organization",
    "title": "your role",
}

# ── Canonical column mapping (placeholder lower-case -> preferred dict key) ───
_CANONICAL = {
    "name": ["name_clean", "name"],
    "company": ["company_clean", "company"],
    "title": ["title"],
}

# Matches {Word} — a single alphanumeric/underscore token inside braces.
_PH_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class TemplateError(Exception):
    """Raised when a template cannot be safely rendered for sending."""


@dataclass
class RenderResult:
    subject: str
    body: str
    used_fallbacks: list[str] = field(default_factory=list)   # placeholder names
    unresolved: list[str] = field(default_factory=list)        # names with no value


# ── Core helpers ──────────────────────────────────────────────────────────────

def find_placeholders(text: str) -> set[str]:
    """Return the set of placeholder names (original case) found in text."""
    return set(_PH_RE.findall(text))


def _lookup(name_lower: str, contact: dict) -> str | None:
    """Look up a placeholder in the contact dict. Returns None if not found."""
    # Check canonical columns first (prefer *_clean variants)
    for key in _CANONICAL.get(name_lower, []):
        val = contact.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    # Case-insensitive scan of all keys in the contact dict
    for k, v in contact.items():
        if k.lower() == name_lower and v is not None and str(v).strip():
            return str(v).strip()
    return None


def render(text: str, contact: dict) -> tuple[str, list[str], list[str]]:
    """Replace placeholders in text using contact.

    Returns (rendered_text, used_fallbacks_list, unresolved_list).
    Unknown placeholders are left as {Name} in the output and reported in
    unresolved so the caller can decide what to do.
    """
    used_fallbacks: list[str] = []
    unresolved: list[str] = []

    def replace(match: re.Match) -> str:
        original = match.group(1)
        lower = original.lower()
        val = _lookup(lower, contact)
        if val:
            return val
        # No value found — try fallback
        if lower in FALLBACKS:
            used_fallbacks.append(original)
            return FALLBACKS[lower]
        # Truly unknown
        unresolved.append(original)
        return match.group(0)   # leave {Placeholder} intact

    rendered = _PH_RE.sub(replace, text)
    return rendered, used_fallbacks, unresolved


def render_for_contact(subject: str, body: str, contact: dict) -> RenderResult:
    """Render both subject and body. Merge fallback/unresolved from both."""
    r_subj, fb_s, unr_s = render(subject, contact)
    r_body, fb_b, unr_b = render(body, contact)
    return RenderResult(
        subject=r_subj,
        body=r_body,
        used_fallbacks=list(dict.fromkeys(fb_s + fb_b)),   # stable dedup
        unresolved=list(dict.fromkeys(unr_s + unr_b)),
    )


def ensure_sendable(result: RenderResult) -> None:
    """Raise TemplateError if the result has unresolved placeholders or empty fields."""
    if not result.subject.strip():
        raise TemplateError("Subject is empty.")
    if not result.body.strip():
        raise TemplateError("Body is empty.")
    if result.unresolved:
        raise TemplateError(
            f"Unresolved placeholder(s): {result.unresolved}. "
            "Fill them in or remove them before sending."
        )


def validate_template(
    subject: str, body: str, available_columns: list[str]
) -> list[str]:
    """Return a list of human-readable problems (empty = no problems found).

    Checks:
    - Empty subject or body.
    - Placeholders not in available_columns and not in FALLBACKS.
    """
    problems: list[str] = []
    if not subject.strip():
        problems.append("Subject is empty.")
    if not body.strip():
        problems.append("Body is empty.")
    known = {c.lower() for c in available_columns} | set(FALLBACKS.keys())
    for ph in find_placeholders(subject) | find_placeholders(body):
        if ph.lower() not in known:
            problems.append(f"Unknown placeholder: {{{ph}}} — not in contacts columns.")
    return problems
