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

## 0.1.0

The first release. ramon shows the GitHub state of the repositories listed in
`~/.config/ramon/config.toml` in a terminal UI: the checks of each default
branch, the open pull requests with their checks and review state, the open
issues, and the latest release. `ramon --plain` prints the same table once.
