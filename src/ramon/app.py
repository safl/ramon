# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only
"""Textual TUI: a table of repositories with the PRs and issues of the
highlighted one below it."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import ClassVar

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding, BindingType
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Static,
    TabbedContent,
    TabPane,
)

from ramon import render
from ramon.github import GhError, Repo, Snapshot

Fetcher = Callable[[], Awaitable[Snapshot]]


# Textual's own app keys are not inherited: zellij takes ctrl+p (pane mode)
# and ctrl+q (quits the session) before they reach the app. Every key here
# must pass through zellij's normal mode and Windows Terminal; see
# tests/test_keys.py.
class RamonApp(App, inherit_bindings=False):
    TITLE = "ramon"
    ENABLE_COMMAND_PALETTE = False
    CSS = """
    #repos { height: 1fr; }
    TabbedContent { height: 1fr; }
    #detail { height: 1; padding: 0 1; }
    """
    BINDINGS: ClassVar[list[BindingType]] = [
        Binding("r", "reload", "Refresh"),
        Binding("o", "open", "Open in browser"),
        Binding("a", "toggle_attention", "Attention only"),
        Binding("p", "show_tab('prs')", "PRs"),
        Binding("i", "show_tab('issues')", "Issues"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", show=False, priority=True),
    ]

    def __init__(self, fetcher: Fetcher, interval: int) -> None:
        super().__init__()
        self.fetcher = fetcher
        self.interval = interval
        self.snapshot: Snapshot | None = None
        self.attention_only = False
        self.loading_snapshot = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="repos", cursor_type="row", zebra_stripes=True)
        yield Static(id="detail")
        with TabbedContent(id="tabs"):
            with TabPane("Pull requests", id="prs"):
                yield DataTable(id="pr-table", cursor_type="row")
            with TabPane("Issues", id="issues"):
                yield DataTable(id="issue-table", cursor_type="row")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#repos", DataTable).add_columns(
            "!",
            "Repository",
            "Branch",
            "CI",
            "PRs",
            "Review",
            "Issues",
            "Release",
            "Pushed",
        )
        self.query_one("#pr-table", DataTable).add_columns(
            "#",
            "Updated",
            "CI",
            "Review",
            "Author",
            "Title",
        )
        self.query_one("#issue-table", DataTable).add_columns(
            "#",
            "Updated",
            "Author",
            "Labels",
            "Title",
        )
        self.sub_title = "loading..."
        self.set_interval(self.interval, self.action_reload)
        self.action_reload()

    def action_reload(self) -> None:
        if not self.loading_snapshot:
            self.loading_snapshot = True
            self.run_worker(self.load_snapshot(), exclusive=True, group="fetch")

    async def load_snapshot(self) -> None:
        try:
            self.snapshot = await self.fetcher()
        except GhError as exc:
            self.sub_title = f"error: {exc}"
            self.notify(str(exc), severity="error", timeout=10)
            return
        finally:
            self.loading_snapshot = False
        self.populate_repos()

    def visible_repos(self) -> list[Repo]:
        if self.snapshot is None:
            return []
        repos = self.snapshot.repos
        if self.attention_only:
            repos = [r for r in repos if r.needs_attention(self.snapshot.viewer)]
        return repos

    def populate_repos(self) -> None:
        snap = self.snapshot
        if snap is None:
            return
        table = self.query_one("#repos", DataTable)
        selected = self.selected_repo()
        now = datetime.now(UTC)

        table.clear()
        for repo in self.visible_repos():
            mark = (
                Text("!", style="bold red") if repo.needs_attention(snap.viewer) else ""
            )
            if repo.error:
                table.add_row(
                    mark,
                    repo.name,
                    "",
                    Text("error", style="bold red"),
                    "",
                    "",
                    "",
                    "",
                    "",
                    key=repo.name,
                )
                continue
            awaiting = sum(1 for pr in repo.prs if snap.viewer in pr.reviewers)
            name = Text(repo.name, style="dim" if repo.archived else "")
            table.add_row(
                mark,
                name,
                repo.branch or "-",
                render.checks(repo.checks),
                render.count(repo.pr_count),
                render.count(awaiting, "bold yellow"),
                render.count(repo.issue_count),
                repo.release or "-",
                render.age(repo.pushed_at, now),
                key=repo.name,
            )

        if selected and selected.name in table.rows:
            table.move_cursor(row=table.get_row_index(selected.name))
        self.populate_details()

        flagged = sum(1 for r in snap.repos if r.needs_attention(snap.viewer))
        local = snap.fetched_at.astimezone().strftime("%H:%M:%S")
        shown = "attention only, " if self.attention_only else ""
        self.sub_title = (
            f"{snap.viewer} | {len(snap.repos)} repos, {flagged} need attention"
            f" | {shown}updated {local}"
        )

    def selected_repo(self) -> Repo | None:
        table = self.query_one("#repos", DataTable)
        if self.snapshot is None or table.row_count == 0:
            return None
        key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        return next((r for r in self.snapshot.repos if r.name == key), None)

    def populate_details(self) -> None:
        repo = self.selected_repo()
        viewer = self.snapshot.viewer if self.snapshot else ""
        now = datetime.now(UTC)
        prs = self.query_one("#pr-table", DataTable)
        issues = self.query_one("#issue-table", DataTable)
        detail = self.query_one("#detail", Static)
        prs.clear()
        issues.clear()
        if repo is None:
            detail.update("")
            return
        if repo.error:
            detail.update(Text(repo.error, style="red"))
        else:
            detail.update(Text(f"{repo.branch}: {repo.head_headline}", style="dim"))

        for pr in repo.prs:
            title = Text(pr.title)
            if viewer in pr.reviewers:
                title.stylize("bold yellow")
            prs.add_row(
                str(pr.number),
                render.age(pr.updated_at, now),
                render.checks(pr.checks),
                render.review(pr.review_decision, pr.is_draft),
                pr.author,
                title,
                key=pr.url,
            )
        for issue in repo.issues:
            issues.add_row(
                str(issue.number),
                render.age(issue.updated_at, now),
                issue.author,
                ", ".join(issue.labels),
                issue.title,
                key=issue.url,
            )

        tabs = self.query_one("#tabs", TabbedContent)
        tabs.get_tab("prs").label = f"Pull requests ({repo.pr_count})"
        tabs.get_tab("issues").label = f"Issues ({repo.issue_count})"

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if event.data_table.id == "repos":
            self.populate_details()

    def action_toggle_attention(self) -> None:
        self.attention_only = not self.attention_only
        if self.snapshot is not None:
            self.populate_repos()

    def action_show_tab(self, tab: str) -> None:
        self.query_one("#tabs", TabbedContent).active = tab

    def url_under_cursor(self) -> str | None:
        """Return the URL of the PR or issue when a detail table has focus,
        else the URL of the highlighted repository."""

        focused = self.focused
        if isinstance(focused, DataTable) and focused.id != "repos":
            if focused.row_count == 0:
                return None
            cell = focused.coordinate_to_cell_key(focused.cursor_coordinate)
            return cell.row_key.value
        repo = self.selected_repo()
        return repo.url if repo and repo.url else None

    def action_open(self) -> None:
        if url := self.url_under_cursor():
            self.open_url(url)
