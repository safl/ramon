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
release, and when it was last pushed to. The highlighted repository's pull
requests and issues are listed below the table.

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

Add `@v0.1.0` to the URL to run a given release.

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
```

## Keys

| Key       | Action |
|-----------|--------|
| `r`       | Refresh now |
| `o`       | Open the highlighted repository, or pull request or issue when its table has focus, in the browser |
| `a`       | Show only the repositories marked `!` |
| `p`, `i`  | Show the pull requests or the issues |
| `tab`     | Move focus between the tables |
| `q`       | Quit |

`ramon --plain` prints the repository table once and exits. It exits with 1
when a repository could not be fetched.

## Development

```sh
make deps         # uv sync
make test         # uv run pytest
make format       # pre-commit on the staged changes
make format-all   # pre-commit on every file
pre-commit install
```

A release is made by merging a pull request whose last commit is
`ver: bump to vX.Y.Z`; see `CHANGELOG.md`.
