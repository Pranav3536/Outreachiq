"""Read-only assistant tools. Reuse existing modules; no duplication.

None of these functions send email, modify contacts, or write to history files.
propose_campaign() returns a Proposal object but stores nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from ..campaigns.history_store import FileHistoryStore
from ..campaigns.reports import campaigns_to_df, summary_stats
from ..config import ENV_MAX_RECIPIENTS_PER_CAMPAIGN, get_env_int, is_env_set, ENV_GMAIL_ADDRESS
from ..data.column_mapping import CANONICAL_FIELDS
from ..data.designation import CATEGORIES, categorize
from ..data.insights import eligible_for_campaign
from ..data.quality_report import build_report
from ..email_tools.attachments import resume_exists
from ..email_tools.placeholders import find_placeholders
from ..email_tools.templates import DEFAULT_BODY, DEFAULT_SUBJECT, load_working


@dataclass
class Proposal:
    recipient_count: int
    included: pd.DataFrame
    excluded_count: int
    exclusion_reasons: list   # list of {email, reason}
    already_sent_skips: list  # list of emails
    template_ready: bool
    resume_ready: bool
    gmail_configured: bool
    categories: list
    limit: int


# ── Tool: inspect dataset ─────────────────────────────────────────────────────

def inspect_dataset(df: pd.DataFrame | None) -> dict:
    """Return rows, columns, and mapping status."""
    if df is None or len(df) == 0:
        return {"rows": 0, "columns": [], "mapping_status": "no data loaded"}
    canonical_present = [f for f in CANONICAL_FIELDS if f in df.columns]
    missing = [f for f in CANONICAL_FIELDS if f not in df.columns]
    if missing:
        status = f"mapped: {', '.join(canonical_present)}; missing: {', '.join(missing)}"
    else:
        status = "all canonical fields mapped"
    return {
        "rows": int(len(df)),
        "columns": list(df.columns),
        "mapping_status": status,
    }


# ── Tool: data quality summary ────────────────────────────────────────────────

def data_quality_summary(df: pd.DataFrame | None) -> dict:
    """Return invalid emails, missing fields, duplicates. No delivery/open/reply."""
    if df is None or len(df) == 0:
        return {"invalid_emails": 0, "missing_fields": {}, "duplicates": 0}
    report = build_report(df)
    return {
        "invalid_emails": report.get("invalid_emails", 0),
        "missing_fields": report.get("missing", {}),
        "duplicates": report.get("duplicate_rows", 0),
    }


# ── Tool: suggest classifications ──────────────────────────────────────────────

def suggest_classifications(df: pd.DataFrame | None) -> list[dict]:
    """Return low-confidence titles with suggested category.

    Says 'rule-based' if no trained model exists.
    """
    if df is None or len(df) == 0 or "title" not in df.columns:
        return []
    from ..ml.classifier import CONF_THRESHOLD, predict

    titles = df["title"].fillna("").astype(str).tolist()
    preds = predict(titles, threshold=CONF_THRESHOLD)
    results = []
    for p in preds:
        if p.needs_review or p.confidence < 0.6:
            results.append({
                "title": p.title,
                "suggested_category": p.category,
                "confidence": round(p.confidence, 3),
                "source": p.source,
                "needs_review": p.needs_review,
            })
    return results


# ── Tool: selection summary ──────────────────────────────────────────────────

def selection_summary(df: pd.DataFrame | None) -> dict:
    """Count and breakdown of campaign_selection, excluding invalid/excluded."""
    if df is None or len(df) == 0:
        return {"count": 0, "categories": {}, "companies": {}}
    eligible, n_excluded = eligible_for_campaign(df)
    df_cat = categorize(eligible)
    cat_counts = {}
    if "title_category" in df_cat.columns:
        cat_counts = df_cat["title_category"].value_counts().to_dict()
    comp_counts = {}
    comp_col = "company_clean" if "company_clean" in df_cat.columns else "company"
    if comp_col in df_cat.columns:
        comp_counts = df_cat[comp_col].replace("", pd.NA).dropna().value_counts().head(10).to_dict()
    return {
        "count": int(len(eligible)),
        "excluded": int(n_excluded),
        "categories": {str(k): int(v) for k, v in cat_counts.items()},
        "companies": {str(k): int(v) for k, v in comp_counts.items()},
    }


# ── Tool: campaign history summary ────────────────────────────────────────────

def campaign_history_summary(store: FileHistoryStore | None = None) -> dict:
    """Totals from history. No delivery/open/reply stats."""
    store = store or FileHistoryStore()
    df, _ = campaigns_to_df(store)
    stats = summary_stats(df)
    return stats


# ── Tool: propose campaign ────────────────────────────────────────────────────

def propose_campaign(
    contacts_df: pd.DataFrame | None,
    categories: list[str] | None = None,
    limit: int | None = None,
    store: FileHistoryStore | None = None,
) -> Proposal:
    """Build a campaign proposal from filters. Stores nothing, sends nothing."""
    max_recip = get_env_int(ENV_MAX_RECIPIENTS_PER_CAMPAIGN, default=100) or 100
    if limit is None or limit > max_recip:
        limit = max_recip

    store = store or FileHistoryStore()
    past_sent = store.sent_keys()
    working = load_working()
    gmail_configured = is_env_set(ENV_GMAIL_ADDRESS)
    resume_ready = resume_exists()

    if contacts_df is None or len(contacts_df) == 0:
        return Proposal(
            recipient_count=0, included=pd.DataFrame(),
            excluded_count=0, exclusion_reasons=[],
            already_sent_skips=[], template_ready=True,
            resume_ready=resume_ready, gmail_configured=gmail_configured,
            categories=categories or [], limit=limit,
        )

    # Apply categorization for category filtering
    df_cat = categorize(contacts_df.copy())

    # Filter by categories if provided
    if categories and "title_category" in df_cat.columns:
        df_cat = df_cat[df_cat["title_category"].isin(categories)]

    # Exclude invalid emails and excluded-duplicates
    eligible, n_excluded = eligible_for_campaign(df_cat)
    exclusion_reasons = []
    excluded_mask = pd.Series(False, index=df_cat.index)
    if "email_valid" in df_cat.columns:
        excluded_mask |= ~df_cat["email_valid"].astype(bool)
    if "excluded" in df_cat.columns:
        excluded_mask |= df_cat["excluded"].astype(bool)
    excluded_rows = df_cat[excluded_mask]
    for _, row in excluded_rows.iterrows():
        reasons = []
        if not row.get("email_valid", True):
            reasons.append("invalid email")
        if row.get("excluded", False):
            reasons.append("excluded duplicate")
        exclusion_reasons.append({
            "email": str(row.get("email_clean") or row.get("email", "")),
            "reason": "; ".join(reasons) if reasons else "excluded",
        })

    # Skip already-sent
    eligible_emails = eligible.get("email_clean", eligible.get("email", pd.Series(dtype=str))).astype(str).str.lower()
    already_sent_skips = eligible_emails[eligible_emails.isin(past_sent)].tolist()
    eligible = eligible[~eligible_emails.isin(past_sent)]

    # Apply limit
    eligible = eligible.head(limit)

    # Check template readiness (no unresolved placeholders)
    template_ready = True
    phs = find_placeholders(working["subject"] + " " + working["body"])
    known = set(CANONICAL_FIELDS) | {c.lower() for c in (contacts_df.columns if contacts_df is not None else [])}
    unknown_phs = {p for p in phs if p.lower() not in known and p.lower() not in {"name", "company", "title"}}
    if unknown_phs:
        template_ready = False

    return Proposal(
        recipient_count=int(len(eligible)),
        included=eligible.reset_index(drop=True),
        excluded_count=int(n_excluded),
        exclusion_reasons=exclusion_reasons,
        already_sent_skips=already_sent_skips,
        template_ready=template_ready,
        resume_ready=resume_ready,
        gmail_configured=gmail_configured,
        categories=categories or [],
        limit=limit,
    )
