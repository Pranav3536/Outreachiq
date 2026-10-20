"""Campaign history reports: dataframes, filters, summary, exports.

Read-only. Reuses FileHistoryStore. Corrupt JSON files are skipped with a
warning list — never crashes. No open/reply/delivery stats; only what the app
actually knows (attempted, SMTP Accepted, Failed, Unknown/Needs Review,
Simulated, Pending).
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pandas as pd

from ..config import CAMPAIGNS_DIR
from ..email_tools.smtp_sender import (
    STATUS_ACCEPTED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_SIMULATED,
    STATUS_UNKNOWN,
)
from .history_store import FileHistoryStore

REVIEW_NOTES_FILE = CAMPAIGNS_DIR / "review_notes.json"

_STATUS_COLS = {
    STATUS_ACCEPTED, STATUS_FAILED, STATUS_UNKNOWN,
    STATUS_SIMULATED, STATUS_PENDING,
}


# ── Dataframe builders ────────────────────────────────────────────────────────

def campaigns_to_df(store: FileHistoryStore | None = None) -> tuple[pd.DataFrame, list[str]]:
    """One row per campaign. Returns (df, warnings) where warnings lists corrupt
    file names that were skipped."""
    store = store or FileHistoryStore()
    warnings: list[str] = []
    rows = []
    for p in sorted(store._dir.glob("*.json"), reverse=True):
        if p.stem == "_working" or p.name == "review_notes.json":
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            warnings.append(p.name)
            continue
        recips = data.get("recipients", [])
        statuses = [r.get("status", "") for r in recips]
        rows.append({
            "campaign_id": data.get("campaign_id", ""),
            "created_at": data.get("created_at", ""),
            "mode": data.get("mode", ""),
            "subject": data.get("subject_snippet", ""),
            "total": data.get("total_ready", len(recips)),
            "simulated": sum(1 for s in statuses if s == STATUS_SIMULATED),
            "smtp_accepted": sum(1 for s in statuses if s == STATUS_ACCEPTED),
            "failed": sum(1 for s in statuses if s == STATUS_FAILED),
            "unknown_needs_review": sum(1 for s in statuses if s == STATUS_UNKNOWN),
            "pending": sum(1 for s in statuses if s == STATUS_PENDING),
            "status": data.get("status", ""),
            "stop_reason": data.get("stop_reason", ""),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["created_at_dt"] = pd.to_datetime(df["created_at"], errors="coerce", utc=True)
    return df, warnings


def recipients_df(
    campaign_id: str | None = None,
    store: FileHistoryStore | None = None,
) -> pd.DataFrame:
    """Per-recipient rows across all campaigns, or one campaign if campaign_id given."""
    store = store or FileHistoryStore()
    rows = []
    campaigns = store.list_campaigns() if campaign_id is None else []
    if campaign_id is not None:
        c = store.load_campaign(campaign_id)
        if c is not None:
            campaigns = [c]
    for c in campaigns:
        cid = c.get("campaign_id", "")
        mode = c.get("mode", "")
        subject = c.get("subject_snippet", "")
        for r in c.get("recipients", []):
            rows.append({
                "campaign_id": cid,
                "mode": r.get("mode", mode),
                "email": r.get("email", ""),
                "name": r.get("name", ""),
                "company": r.get("company", ""),
                "title": r.get("title", ""),
                "subject": subject,
                "status": r.get("status", ""),
                "error_summary": r.get("error_summary", ""),
                "timestamp": r.get("timestamp", ""),
            })
    return pd.DataFrame(rows)


# ── Filters ───────────────────────────────────────────────────────────────────

def filter_campaigns(
    df: pd.DataFrame,
    date_from: str | None = None,
    date_to: str | None = None,
    mode: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if date_from and "created_at_dt" in out:
        out = out[out["created_at_dt"] >= pd.to_datetime(date_from, utc=True, errors="coerce")]
    if date_to and "created_at_dt" in out:
        out = out[out["created_at_dt"] <= pd.to_datetime(date_to, utc=True, errors="coerce")]
    if mode and mode != "All":
        out = out[out["mode"] == mode]
    if status and status != "All":
        out = out[out["status"] == status]
    if search:
        q = search.lower()
        mask = (
            out["subject"].astype(str).str.lower().str.contains(q, na=False)
            | out["campaign_id"].astype(str).str.lower().str.contains(q, na=False)
        )
        out = out[mask]
    return out


def filter_recipients(
    df: pd.DataFrame,
    mode: str | None = None,
    status: str | None = None,
    search: str | None = None,
) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    if mode and mode != "All":
        out = out[out["mode"] == mode]
    if status and status != "All":
        out = out[out["status"] == status]
    if search:
        q = search.lower()
        cols = ["email", "company", "title", "subject", "name"]
        mask = pd.Series(False, index=out.index)
        for c in cols:
            if c in out.columns:
                mask |= out[c].astype(str).str.lower().str.contains(q, na=False)
        out = out[mask]
    return out


# ── Summary ───────────────────────────────────────────────────────────────────

def summary_stats(camp_df: pd.DataFrame) -> dict:
    """Aggregate counts across filtered campaign rows. No delivery/open/reply."""
    if camp_df.empty:
        return {
            "campaigns": 0, "attempted": 0, "smtp_accepted": 0,
            "failed": 0, "unknown_needs_review": 0,
            "simulated": 0, "pending": 0,
        }
    return {
        "campaigns": int(len(camp_df)),
        "attempted": int(camp_df["total"].sum()),
        "smtp_accepted": int(camp_df["smtp_accepted"].sum()),
        "failed": int(camp_df["failed"].sum()),
        "unknown_needs_review": int(camp_df["unknown_needs_review"].sum()),
        "simulated": int(camp_df["simulated"].sum()),
        "pending": int(camp_df["pending"].sum()),
    }


# ── Exports ───────────────────────────────────────────────────────────────────

def export_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def export_xlsx_bytes(df: pd.DataFrame) -> bytes:
    # Excel does not support timezone-aware datetimes; drop the helper column.
    out = df.drop(columns=["created_at_dt"], errors="ignore")
    buf = BytesIO()
    out.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


# ── Review notes (Needs Review tab) ──────────────────────────────────────────

def save_review_note(campaign_id: str, email: str, note: str) -> None:
    """Append/update a manual review note for a recipient. Atomic write."""
    CAMPAIGNS_DIR.mkdir(parents=True, exist_ok=True)
    notes = load_review_notes()
    key = f"{campaign_id}|{email.lower()}"
    notes[key] = {
        "campaign_id": campaign_id,
        "email": email,
        "note": note,
        "updated_at": datetime.now().isoformat(),
    }
    tmp = REVIEW_NOTES_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(notes, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, REVIEW_NOTES_FILE)


def load_review_notes() -> dict:
    """Return {key: {campaign_id, email, note, updated_at}} or {} if missing."""
    if not REVIEW_NOTES_FILE.exists():
        return {}
    try:
        return json.loads(REVIEW_NOTES_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
