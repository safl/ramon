<!--
SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>

SPDX-License-Identifier: GPL-2.0-only
-->

# ramon

[![verify](https://github.com/safl/ramon/actions/workflows/verify.yml/badge.svg)](https://github.com/safl/ramon/actions/workflows/verify.yml)
[![REUSE status](https://api.reuse.software/badge/github.com/safl/ramon)](https://api.reuse.software/info/github.com/safl/ramon)

ramon shows the GitHub state of a list of repositories in a terminal UI. For
each repository it shows the checks on the default branch, the number of open
pull requests and of those awaiting your review, the open issues, the latest
release, and when it was last pushed to. Below the table, a line shows the
highlighted repository's last commit on its default branch, or why GitHub could
not return it, and tabs list its open pull requests and issues. The title bar
shows who you are logged in as, how many repositories need attention, when the
data was fetched, and the current theme.

A repository is marked `!` when its default branch fails its checks, when a
pull request awaits your review, when one of your pull requests fails its
checks, or when GitHub could not return it.

ramon queries GitHub through `gh api graphql`, 5 repositories per query, with
up to 8 queries in flight. It needs [gh](https://cli.github.com/), logged
in with `gh auth login`, and [uv](https://docs.astral.sh/uv/).

## Running

ramon is not published to PyPI. Run it with `uvx` from this repository:

```sh
uvx --from git+https://github.com/safl/ramon ramon
```

Add `@v0.1.0` to the URL to run a given release, or `@main` for the latest
commit. To run a local clone, use a `git+file` URL; it runs what is committed
on the clone's current branch:

```sh
uvx --from git+file:///path/to/ramon ramon
```

`ramon --plain` prints the repository table once and exits, instead of
starting the terminal UI. It exits with 1 when a repository could not be
fetched.

## Configuration

ramon reads `~/.config/ramon/config.toml`, or the file named by `--config` or
`$RAMON_CONFIG`:

```toml
# Seconds between automatic refreshes, at least 30.
interval = 300

# Repositories given as "owner/name".
repos = [
    "xnvme/xnvme",
    "refenv/cijoe",
]

# Every non-archived repository of these users or organisations.
owners = []

# A Textual theme, such as "nord" or "gruvbox"; 't' in ramon steps through them.
theme = "nord"

# "nerd" shows states as Nerd Font glyphs; the terminal needs a Nerd Font.
glyphs = "text"
```

Only `repos` or `owners` is required. ramon exits with an error naming the
available themes when `theme` is not one of them.

With `glyphs = "nerd"`, ramon shows the checks, the review state and the `!`
mark as Octicons, and puts icons in front of the release and the tab labels.
With a font that is not a Nerd Font, each glyph shows as an empty box.

## Keys

| Key           | Action |
|---------------|--------|
| `up`, `down`  | Move through the repositories, or through the pull requests or issues when their table has focus |
| `left`, `right` | Show the pull requests or the issues |
| `enter`       | Open the highlighted repository, pull request or issue in the browser |
| `tab`         | Move focus between the repositories and the pull requests or issues |
| `a`           | Show only the repositories marked `!` |
| `r`           | Refresh now |
| `t`           | Switch to the next theme; its name is shown in the title bar |
| `:`           | Command palette |
| `q`, `ctrl+c` | Quit |

zellij's normal mode and Windows Terminal pass all of these keys through to
ramon. ramon binds no Alt key, no Ctrl+Shift key and none of zellij's mode
keys. For that reason Textual's command palette is on `:` rather than `ctrl+p`,
and Textual's `ctrl+q` quit is disabled. A theme chosen with `t` lasts until
ramon exits; set `theme` in the configuration to keep it.

## Development

```sh
make deps         # uv sync
make run          # uv run ramon, from the working tree
make test         # uv run pytest
make format       # pre-commit on the staged changes
make format-all   # pre-commit on every file
pre-commit install
```

A release is made by merging a pull request whose last commit is
`ver: bump to vX.Y.Z`; see `CHANGELOG.md`.
