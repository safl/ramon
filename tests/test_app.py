# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only

from datetime import UTC, datetime

from textual.widgets import DataTable, Static, TabbedContent

from ramon import github
from ramon.app import RamonApp

NAMES = ["o/ok", "o/missing", "o/red"]


def make_app(payload, opened=None):
    calls = []

    async def fetcher():
        calls.append(1)
        viewer, repos = github.parse_response(NAMES, payload)
        return github.Snapshot(viewer, repos, datetime.now(UTC))

    app = RamonApp(fetcher, interval=3600)
    if opened is not None:
        app.open_url = lambda url, **kw: opened.append(url)
    return app, calls


async def test_repos_and_details(payload):
    app, calls = make_app(payload)
    async with app.run_test() as pilot:
        await pilot.pause()
        repos = app.query_one("#repos", DataTable)
        prs = app.query_one("#pr-table", DataTable)
        assert repos.row_count == 3
        assert prs.row_count == 2
        assert "3 repos, 3 need attention" in app.sub_title

        await pilot.press("down", "down")
        assert app.selected_repo().name == "o/red"
        assert prs.row_count == 0

        await pilot.press("r")
        await pilot.pause()
        assert len(calls) == 2
        # The refresh keeps the highlighted repository
        assert app.selected_repo().name == "o/red"


async def test_attention_filter(payload):
    app, _ = make_app(payload)
    async with app.run_test() as pilot:
        await pilot.pause()
        repos = app.query_one("#repos", DataTable)
        await pilot.press("a")
        # 'o/ok' needs attention too: a PR awaits the viewer's review
        assert repos.row_count == 3
        payload["data"]["r0"]["pullRequests"]["nodes"].pop()
        await pilot.press("r")
        await pilot.pause()
        assert [str(k.value) for k in repos.rows] == ["o/missing", "o/red"]
        await pilot.press("a")
        assert repos.row_count == 3


async def test_open_repo_and_pr(payload):
    opened = []
    app, _ = make_app(payload, opened)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.press("tab")
        await pilot.press("down", "enter")
    assert opened == ["https://github.com/o/ok", "https://github.com/o/r/pull/2"]


async def test_fetch_error_is_shown():
    async def fetcher():
        raise github.GhError("gh auth login")

    app = RamonApp(fetcher, interval=3600)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.sub_title.startswith("error: gh auth login | ")
        assert app.query_one("#repos", DataTable).row_count == 0


async def test_detail_line_shows_head_commit_or_error(payload):
    app, _ = make_app(payload)
    async with app.run_test() as pilot:
        await pilot.pause()
        detail = app.query_one("#detail", Static)
        assert str(detail.render()) == "main: docs: a change"
        await pilot.press("down")
        assert str(detail.render()).startswith("Could not resolve")


async def test_left_right_switch_tabs_and_keep_focus_in_details(payload):
    app, _ = make_app(payload)
    async with app.run_test() as pilot:
        await pilot.pause()
        tabs = app.query_one("#tabs", TabbedContent)
        repos = app.query_one("#repos", DataTable)
        await pilot.press("right")
        assert tabs.active == "issues"
        assert app.focused is repos
        await pilot.press("left")
        assert tabs.active == "prs"

        await pilot.press("tab")
        assert app.focused.id == "pr-table"
        await pilot.press("right")
        assert tabs.active == "issues"
        assert app.focused.id == "issue-table"

        # up and down move within the focused table, the repositories first
        await pilot.press("shift+tab")
        await pilot.press("down")
        assert app.selected_repo().name == "o/missing"
