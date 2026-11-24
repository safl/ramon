# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only
"""Format repository state as styled cells for the TUI and the plain output."""

from datetime import datetime

from rich.text import Text

CHECKS = {
    "SUCCESS": ("ok", "green"),
    "FAILURE": ("fail", "bold red"),
    "ERROR": ("error", "bold red"),
    "PENDING": ("pend", "yellow"),
    "EXPECTED": ("pend", "yellow"),
}

REVIEW = {
    "APPROVED": ("approved", "green"),
    "CHANGES_REQUESTED": ("changes", "bold red"),
    "REVIEW_REQUIRED": ("review", "yellow"),
}


def checks(state: str | None) -> Text:
    label, style = CHECKS.get(state or "", ("-", "dim"))
    return Text(label, style=style)


def review(decision: str | None, is_draft: bool) -> Text:
    if is_draft:
        return Text("draft", style="dim")
    label, style = REVIEW.get(decision or "", ("-", "dim"))
    return Text(label, style=style)


def age(then: datetime | None, now: datetime) -> str:
    """Return the time from 'then' to 'now' as '45s', '12m', '5h', '3d' or '7w'."""

    if then is None:
        return "-"
    secs = max(0, int((now - then).total_seconds()))
    for unit, size in (("w", 604800), ("d", 86400), ("h", 3600), ("m", 60)):
        if secs >= size:
            return f"{secs // size}{unit}"
    return f"{secs}s"


def count(value: int, style: str = "") -> Text:
    return Text(str(value), style=style if value else "dim")
