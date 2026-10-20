"""File-based campaign history store. Designed behind a HistoryStore interface
so it can be replaced by SQLite later without changing callers.

Record layout (runtime/campaigns/<id>.json):
  campaign_id, created_at, mode, subject_snippet (first 60 chars),
  template_name, resume_attached, total_ready, total_excluded,
  status (Draft|Running|Paused|Completed|Stopped), stop_reason,
  recipients: [{email, name, company, title, status, error_summary, timestamp}]

Atomic writes: write to .tmp then os.replace().
No email body text and no credentials are stored.
"""
from __future__ import annotations

import json
import os
import random
import string
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, runtime_checkable

from ..config import CAMPAIGNS_DIR
from ..email_tools.smtp_sender import (
    STATUS_ACCEPTED,
    STATUS_SIMULATED,
    STATUS_UNKNOWN,
    SendResult,
)

_REAL_SENT_STATUSES = {STATUS_ACCEPTED, STATUS_UNKNOWN}   # count toward dup-prevention


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{ts}_{rand}"


# ── Public record dataclasses (plain dicts in JSON on disk) ──────────────────

class CampaignRecord(dict):
    """Thin dict wrapper so callers get dot-style access via .get()."""


# ── HistoryStore interface ────────────────────────────────────────────────────

@runtime_checkable
class HistoryStore(Protocol):
    def create_campaign(
        self,
        mode: str,
        subject: str,
        template_name: str,
        resume_attached: bool,
        total_ready: int,
        total_excluded: int,
    ) -> str: ...

    def update_recipient(self, campaign_id: str, result: SendResult) -> None: ...

    def set_status(self, campaign_id: str, status: str, stop_reason: str = "") -> None: ...

    def list_campaigns(self) -> list[dict]: ...

    def load_campaign(self, campaign_id: str) -> dict | None: ...

    def sent_keys(self) -> set[str]: ...


# ── File-based implementation ─────────────────────────────────────────────────

class FileHistoryStore:
    """Stores one JSON file per campaign in CAMPAIGNS_DIR."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._dir = Path(base_dir) if base_dir else CAMPAIGNS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, campaign_id: str) -> Path:
        return self._dir / f"{campaign_id}.json"

    def _write(self, data: dict) -> None:
        path = self._path(data["campaign_id"])
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)

    def create_campaign(
        self,
        mode: str,
        subject: str,
        template_name: str,
        resume_attached: bool,
        total_ready: int,
        total_excluded: int,
    ) -> str:
        cid = _new_id()
        data = {
            "campaign_id": cid,
            "created_at": _now_iso(),
            "mode": mode,
            "subject_snippet": subject[:60],
            "template_name": template_name,
            "resume_attached": resume_attached,
            "total_ready": total_ready,
            "total_excluded": total_excluded,
            "status": "Running",
            "stop_reason": "",
            "recipients": [],
        }
        self._write(data)
        return cid

    def update_recipient(self, campaign_id: str, result: SendResult) -> None:
        """Append or update one recipient row. Atomic write per call."""
        data = self.load_campaign(campaign_id)
        if data is None:
            return
        recipients = data.setdefault("recipients", [])
        # Update existing row if email already present, else append.
        for row in recipients:
            if row.get("email", "").lower() == result.email.lower():
                row["status"] = result.status
                row["error_summary"] = result.error_summary
                row["timestamp"] = result.timestamp
                break
        else:
            recipients.append({
                "email": result.email,
                "name": result.recipient_name,
                "status": result.status,
                "error_summary": result.error_summary,
                "timestamp": result.timestamp,
                "mode": result.mode,
            })
        self._write(data)

    def set_status(self, campaign_id: str, status: str, stop_reason: str = "") -> None:
        data = self.load_campaign(campaign_id)
        if data is None:
            return
        data["status"] = status
        if stop_reason:
            data["stop_reason"] = stop_reason
        self._write(data)

    def list_campaigns(self) -> list[dict]:
        records = []
        for p in sorted(self._dir.glob("*.json"), reverse=True):
            if p.stem == "_working":
                continue
            try:
                records.append(json.loads(p.read_text(encoding="utf-8")))
            except Exception:
                continue
        return records

    def load_campaign(self, campaign_id: str) -> dict | None:
        path = self._path(campaign_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def sent_keys(self) -> set[str]:
        """Normalised emails that are SMTP Accepted or Unknown/Needs Review in REAL mode.

        Simulated rows and Failed rows never count (they were not sent to the server).
        """
        keys: set[str] = set()
        for record in self.list_campaigns():
            if record.get("mode") != "real":
                continue
            for row in record.get("recipients", []):
                if row.get("status") in _REAL_SENT_STATUSES:
                    keys.add(row["email"].lower().strip())
        return keys


# ── Module-level singleton (overridable for tests via monkeypatch) ────────────
_default_store: FileHistoryStore | None = None


def get_store() -> FileHistoryStore:
    global _default_store
    if _default_store is None:
        _default_store = FileHistoryStore()
    return _default_store
