"""Prepare a campaign: render per-recipient emails, gate on sendability.

No emails are sent here. All gating happens before any UI "send" button.
The PreparedCampaign object is stored in st.session_state["prepared_campaign"]
by the UI layer, not here.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..config import ENV_MAX_RECIPIENTS_PER_CAMPAIGN, get_env_int
from .attachments import resume_exists
from .placeholders import RenderResult, TemplateError, ensure_sendable, render_for_contact


@dataclass
class RecipientResult:
    row_index: int
    name: str
    email: str
    rendered: RenderResult | None
    ready: bool
    exclusion_reason: str   # "" if ready


@dataclass
class PreparedCampaign:
    subject_template: str
    body_template: str
    attach_resume: bool
    resume_ready: bool          # True only when attach_resume and file exists
    recipients_ready: list[RecipientResult] = field(default_factory=list)
    recipients_excluded: list[RecipientResult] = field(default_factory=list)
    limit_exceeded: bool = False
    limit_message: str = ""

    @property
    def is_sendable(self) -> bool:
        return (
            len(self.recipients_ready) > 0
            and not self.limit_exceeded
            and (self.resume_ready or not self.attach_resume)
        )

    @property
    def ready_count(self) -> int:
        return len(self.recipients_ready)

    @property
    def excluded_count(self) -> int:
        return len(self.recipients_excluded)


def _exclusion_reason(row: pd.Series) -> str:
    """Return a non-empty string if this row should be excluded before rendering."""
    # Missing / invalid email
    email = str(row.get("email_clean") or row.get("email", "")).strip()
    if not email:
        return "Missing email"
    email_valid = row.get("email_valid")
    if email_valid is False or str(email_valid).lower() == "false":
        return f"Invalid email ({email})"
    # Excluded duplicate
    excluded = row.get("excluded")
    if excluded is True or str(excluded).lower() == "true":
        return "Excluded duplicate"
    return ""


def prepare_campaign(
    contacts_df: pd.DataFrame,
    subject: str,
    body: str,
    attach_resume: bool = True,
) -> PreparedCampaign:
    """Render per-recipient emails. Failing rows go to excluded, never to ready list.

    Enforces MAX_RECIPIENTS_PER_CAMPAIGN from config (default 100).
    """
    max_recip = get_env_int(ENV_MAX_RECIPIENTS_PER_CAMPAIGN, default=100) or 100
    resume_ready = (not attach_resume) or resume_exists()

    campaign = PreparedCampaign(
        subject_template=subject,
        body_template=body,
        attach_resume=attach_resume,
        resume_ready=resume_ready,
    )

    if contacts_df is None or len(contacts_df) == 0:
        return campaign

    if len(contacts_df) > max_recip:
        campaign.limit_exceeded = True
        campaign.limit_message = (
            f"Cannot prepare: {len(contacts_df)} recipients exceeds the "
            f"MAX_RECIPIENTS_PER_CAMPAIGN limit of {max_recip}. "
            "Reduce your selection before preparing."
        )
        return campaign

    for idx, row in contacts_df.iterrows():
        contact = row.to_dict()
        name = str(contact.get("name_clean") or contact.get("name", "")).strip()
        email = str(contact.get("email_clean") or contact.get("email", "")).strip()

        # Pre-render exclusion checks
        pre_reason = _exclusion_reason(row)
        if pre_reason:
            campaign.recipients_excluded.append(RecipientResult(
                row_index=int(idx),
                name=name,
                email=email,
                rendered=None,
                ready=False,
                exclusion_reason=pre_reason,
            ))
            continue

        # Render
        result = render_for_contact(subject, body, contact)

        # Post-render exclusion: unresolved placeholders or empty fields
        try:
            ensure_sendable(result)
        except TemplateError as exc:
            campaign.recipients_excluded.append(RecipientResult(
                row_index=int(idx),
                name=name,
                email=email,
                rendered=result,
                ready=False,
                exclusion_reason=str(exc),
            ))
            continue

        campaign.recipients_ready.append(RecipientResult(
            row_index=int(idx),
            name=name,
            email=result.subject,   # subject is rendered
            rendered=result,
            ready=True,
            exclusion_reason="",
        ))
        # Fix: store email separately
        campaign.recipients_ready[-1].email = email

    return campaign
