# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only
"""ramon: monitor the GitHub state of a list of repositories from the terminal."""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from functools import partial
from importlib.metadata import version
from pathlib import Path

from rich.console import Console
from rich.table import Table

from ramon import config, github, render


def print_plain(snapshot: github.Snapshot, nerd: bool = False) -> None:
    now = datetime.now(UTC)
    table = Table(box=None, pad_edge=False)
    for col in (
        "!",
        "Repository",
        "CI",
        "PRs",
        "Review",
        "Issues",
        "Release",
        "Pushed",
    ):
        table.add_column(col, no_wrap=True)
    for repo in snapshot.repos:
        mark = render.attention(nerd) if repo.needs_attention(snapshot.viewer) else ""
        if repo.error:
            table.add_row(mark, repo.name, render.fetch_error(nerd))
            continue
        awaiting = sum(1 for pr in repo.prs if snapshot.viewer in pr.reviewers)
        table.add_row(
            mark,
            repo.name,
            render.checks(repo.checks, nerd),
            str(repo.pr_count),
            str(awaiting),
            str(repo.issue_count),
            render.release(repo.release, nerd),
            render.age(repo.pushed_at, now),
        )
    console = Console()
    console.print(table)
    for repo in snapshot.repos:
        if repo.error:
            console.print(f"[red]{repo.name}: {repo.error}[/]", soft_wrap=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ramon",
        description="Monitor the GitHub state of a list of repositories.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        default=config.default_path(),
        help="configuration file (default: %(default)s)",
    )
    parser.add_argument("--version", action="version", version=version("ramon"))
    parser.add_argument(
        "--plain",
        action="store_true",
        help="print a status table once and exit instead of starting the TUI",
    )
    args = parser.parse_args(argv)

    try:
        cfg = config.load(args.config)
    except config.ConfigError as exc:
        print(f"ramon: {exc}", file=sys.stderr)
        return 2

    fetcher = partial(github.fetch, cfg.repos, cfg.owners)

    if args.plain:
        try:
            snapshot = asyncio.run(fetcher())
        except github.GhError as exc:
            print(f"ramon: {exc}", file=sys.stderr)
            return 1
        print_plain(snapshot, cfg.glyphs == "nerd")
        return 1 if any(r.error for r in snapshot.repos) else 0

    from ramon.app import RamonApp

    app = RamonApp(fetcher, cfg.interval, nerd=cfg.glyphs == "nerd")
    if cfg.theme and cfg.theme not in app.available_themes:
        names = ", ".join(sorted(app.available_themes))
        print(f"ramon: unknown theme {cfg.theme!r}; one of: {names}", file=sys.stderr)
        return 2
    if cfg.theme:
        app.theme = cfg.theme
    app.run()
    return 0
