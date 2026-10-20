"""Category-to-template-name suggestion map (suggestion only, never auto-applied).

Edit CATEGORY_TEMPLATE_MAP to associate a saved template filename with each
category. Lookup returns None if no suggestion exists for a category.
"""
from __future__ import annotations

# Map category -> template filename (relative to runtime/templates/).
# These are suggestions only; they are NEVER automatically applied.
CATEGORY_TEMPLATE_MAP: dict[str, str | None] = {
    "HR/Recruiting": None,
    "Talent Acquisition": None,
    "Founder/CEO/Owner": None,
    "Director/Head": None,
    "Manager": None,
    "Other/Unknown": None,
}


def suggest_template(category: str) -> str | None:
    """Return the suggested template filename for a category, or None."""
    return CATEGORY_TEMPLATE_MAP.get(category)
