<!--
SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>

SPDX-License-Identifier: GPL-2.0-only
-->

# Changelog

Each release of ramon has a section here, named by its version, such as
`## 0.1.0`. That section is the text of the release on GitHub.

A release is made by merging a pull request whose last commit is
`ver: bump to vX.Y.Z`. That commit sets `version` in `pyproject.toml` and adds
the `## X.Y.Z` section to this file. When it lands on `main`,
`.github/workflows/release.yml` checks both, and that `verify.yml` passed on
the pull request, then tags the commit and creates the GitHub release. Release
tags are not pushed by hand.

## 0.2.1

ramon starts with the gruvbox theme when the configuration sets no `theme`,
in place of Textual's textual-dark.

## 0.2.0

ramon now works inside zellij and Windows Terminal: it binds no key that
either takes for itself. Textual's command palette moves from ctrl+p to `:`,
Textual's ctrl+q quit is gone, and ctrl+c quits alongside `q`.

The arrows and enter replace `p`, `i` and `o`. Up and down move through the
focused table, left and right switch between the pull requests and the
issues, and enter opens the highlighted repository, pull request or issue in
the browser.

`t` steps through the themes and shows the current one in the title bar. The
configuration gains `theme`, to start with a given theme, and `glyphs`, which
with the value "nerd" shows the checks, review states and attention mark as
Nerd Font glyphs.

## 0.1.0

The first release. ramon shows the GitHub state of the repositories listed in
`~/.config/ramon/config.toml` in a terminal UI: the checks of each default
branch, the open pull requests with their checks and review state, the open
issues, and the latest release. `ramon --plain` prints the same table once.
