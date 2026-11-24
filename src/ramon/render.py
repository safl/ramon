# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only
"""Format repository state as styled cells for the TUI and the plain output."""

from datetime import datetime

from rich.text import Text

# Octicons as a Nerd Font provides them, by their glyph names in the font
NERD = {
    "check": "\uf42e",  # oct-check
    "x": "\uf467",  # oct-x
    "dot_fill": "\uf444",  # oct-dot_fill
    "eye": "\uf441",  # oct-eye
    "file_diff": "\uf4d2",  # oct-file_diff
    "draft": "\uf4dd",  # oct-git_pull_request_draft
    "alert": "\uf421",  # oct-alert
    "pull_request": "\uf407",  # oct-git_pull_request
    "issue": "\uf41b",  # oct-issue_opened
    "tag": "\uf412",  # oct-tag
}

# State -> (text, Nerd Font glyph, style)
CHECKS = {
    "SUCCESS": ("ok", NERD["check"], "green"),
    "FAILURE": ("fail", NERD["x"], "bold red"),
    "ERROR": ("error", NERD["x"], "bold red"),
    "PENDING": ("pend", NERD["dot_fill"], "yellow"),
    "EXPECTED": ("pend", NERD["dot_fill"], "yellow"),
}

REVIEW = {
    "APPROVED": ("approved", NERD["check"], "green"),
    "CHANGES_REQUESTED": ("changes", NERD["file_diff"], "bold red"),
    "REVIEW_REQUIRED": ("review", NERD["eye"], "yellow"),
}

DRAFT = ("draft", NERD["draft"], "dim")
UNKNOWN = ("-", "-", "dim")


def _cell(entry: tuple[str, str, str], nerd: bool) -> Text:
    label, glyph, style = entry
    return Text(glyph if nerd else label, style=style)


def checks(state: str | None, nerd: bool = False) -> Text:
    return _cell(CHECKS.get(state or "", UNKNOWN), nerd)


def review(decision: str | None, is_draft: bool, nerd: bool = False) -> Text:
    if is_draft:
        return _cell(DRAFT, nerd)
    return _cell(REVIEW.get(decision or "", UNKNOWN), nerd)


def attention(nerd: bool = False) -> Text:
    return Text(NERD["alert"] if nerd else "!", style="bold red")


def fetch_error(nerd: bool = False) -> Text:
    return Text(f"{NERD['x']} error" if nerd else "error", style="bold red")


def release(tag: str | None, nerd: bool = False) -> str:
    if not tag:
        return "-"
    return f"{NERD['tag']} {tag}" if nerd else tag


def tab_label(kind: str, total: int, nerd: bool = False) -> str:
    """Return the label of the 'prs' or the 'issues' tab."""

    text, glyph = {
        "prs": ("Pull requests", NERD["pull_request"]),
        "issues": ("Issues", NERD["issue"]),
    }[kind]
    return f"{glyph} {text} ({total})" if nerd else f"{text} ({total})"


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
