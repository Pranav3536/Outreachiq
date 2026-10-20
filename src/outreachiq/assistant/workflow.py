"""State machine + keyword-based command parser for the Outreach Assistant.

No LLM, no external APIs. Plain Python keyword rules.
States: Inspect -> Quality -> Suggestions -> Proposal -> Awaiting approval -> Handed off.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..data.designation import CATEGORIES

SUPPORTED_COMMANDS = [
    ("check data", "Inspect dataset (rows, columns, mapping status)"),
    ("quality", "Data quality summary (invalid emails, missing fields, duplicates)"),
    ("suggest titles", "Suggest categories for uncertain titles"),
    ("selection", "Summarise current campaign selection"),
    ("history", "Campaign history summary (accepted, failed, unknown)"),
    ("propose campaign for <categories> top <N>", "Build a campaign proposal"),
]


@dataclass
class WorkflowState:
    state: str = "Inspect"
    transcript: list[str] = field(default_factory=list)

    def log(self, speaker: str, text: str) -> None:
        self.transcript.append(f"**{speaker}:** {text}")

    def user_said(self, text: str) -> None:
        self.transcript.append(f"**You:** {text}")


def parse_command(text: str) -> tuple[str, dict]:
    """Parse a user command string. Returns (command_name, args_dict).

    Unknown commands return ("unknown", {}).
    """
    lower = text.lower().strip()

    if "check data" in lower or "inspect" in lower:
        return ("inspect", {})
    if "quality" in lower:
        return ("quality", {})
    if "suggest" in lower and "title" in lower:
        return ("suggest_titles", {})
    if "selection" in lower:
        return ("selection", {})
    if "history" in lower:
        return ("history", {})

    if "propose" in lower and "campaign" in lower:
        # Extract categories by matching against CATEGORIES
        cats = []
        for cat in CATEGORIES:
            # Match by significant words in the category name
            cat_lower = cat.lower()
            if "hr" in cat_lower or "recruiting" in cat_lower:
                if "hr" in lower or "recruiting" in lower:
                    cats.append(cat)
            if "talent" in cat_lower:
                if "talent" in lower:
                    cats.append(cat)
            if "founder" in cat_lower or "ceo" in cat_lower:
                if "founder" in lower or "ceo" in lower or "owner" in lower:
                    cats.append(cat)
            if "director" in cat_lower or "head" in cat_lower:
                if "director" in lower or "head" in lower:
                    cats.append(cat)
            if "manager" in cat_lower:
                if "manager" in lower:
                    cats.append(cat)
            if "other" in cat_lower or "unknown" in cat_lower:
                pass  # "Other/Unknown" is the fallback; don't match on "unknown"

        # Extract limit: "top N" or "limit N"
        limit = None
        m = re.search(r"top\s+(\d+)", lower)
        if m:
            limit = int(m.group(1))
        else:
            m = re.search(r"limit\s+(\d+)", lower)
            if m:
                limit = int(m.group(1))

        return ("propose", {"categories": cats, "limit": limit})

    return ("unknown", {})


def unknown_command_help() -> str:
    """Return a helpful list of supported commands."""
    lines = ["I don't recognise that command. Try one of these:"]
    for cmd, desc in SUPPORTED_COMMANDS:
        lines.append(f"- `{cmd}` — {desc}")
    return "\n".join(lines)


# State transitions (informational; the UI drives the actual flow)
STATE_ORDER = [
    "Inspect", "Quality", "Suggestions",
    "Proposal", "Awaiting approval", "Handed off",
]

def next_state(current: str) -> str:
    """Return the next state in the workflow."""
    try:
        idx = STATE_ORDER.index(current)
    except ValueError:
        return "Inspect"
    if idx < len(STATE_ORDER) - 1:
        return STATE_ORDER[idx + 1]
    return current
