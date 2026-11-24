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


def print_plain(snapshot: github.Snapshot) -> None:
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
        mark = "!" if repo.needs_attention(snapshot.viewer) else ""
        if repo.error:
            table.add_row(mark, repo.name, "[bold red]error[/]")
            continue
        awaiting = sum(1 for pr in repo.prs if snapshot.viewer in pr.reviewers)
        table.add_row(
            mark,
            repo.name,
            render.checks(repo.checks),
            str(repo.pr_count),
            str(awaiting),
            str(repo.issue_count),
            repo.release or "-",
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
        print_plain(snapshot)
        return 1 if any(r.error for r in snapshot.repos) else 0

    from ramon.app import RamonApp

    RamonApp(fetcher, cfg.interval).run()
    return 0
