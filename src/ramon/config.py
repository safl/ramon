# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only
"""Load the list of repositories to monitor from a TOML file."""

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO_PATTERN = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
OWNER_PATTERN = re.compile(r"^[A-Za-z0-9-]+$")

EXAMPLE = """\
# Seconds between automatic refreshes.
interval = 300

# Repositories given as "owner/name".
repos = [
    "xnvme/xnvme",
]

# Every non-archived repository of these users or organisations.
owners = []

# A Textual theme; 't' in ramon steps through them. The default is "gruvbox".
# theme = "nord"

# "nerd" shows states as Nerd Font glyphs; the terminal needs a Nerd Font.
# glyphs = "text"
"""


class ConfigError(Exception):
    pass


@dataclass
class Config:
    repos: list[str] = field(default_factory=list)
    owners: list[str] = field(default_factory=list)
    interval: int = 300
    theme: str | None = None
    glyphs: str = "text"


def default_path() -> Path:
    """Return $RAMON_CONFIG, else $XDG_CONFIG_HOME/ramon/config.toml."""

    if env := os.environ.get("RAMON_CONFIG"):
        return Path(env)
    base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / "ramon" / "config.toml"


def parse(text: str) -> Config:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML: {exc}") from exc

    unknown = set(data) - {"repos", "owners", "interval", "theme", "glyphs"}
    if unknown:
        raise ConfigError(f"unknown keys: {', '.join(sorted(unknown))}")

    repos = data.get("repos", [])
    owners = data.get("owners", [])
    interval = data.get("interval", 300)
    theme = data.get("theme")
    glyphs = data.get("glyphs", "text")

    if not isinstance(repos, list) or not all(isinstance(r, str) for r in repos):
        raise ConfigError("'repos' must be a list of strings")
    if not isinstance(owners, list) or not all(isinstance(o, str) for o in owners):
        raise ConfigError("'owners' must be a list of strings")
    if not isinstance(interval, int) or isinstance(interval, bool) or interval < 30:
        raise ConfigError("'interval' must be an integer of at least 30 seconds")
    if theme is not None and not isinstance(theme, str):
        raise ConfigError("'theme' must be a string")
    if glyphs not in ("text", "nerd"):
        raise ConfigError('\'glyphs\' must be "text" or "nerd"')

    for repo in repos:
        if not REPO_PATTERN.match(repo):
            raise ConfigError(f"repository {repo!r} is not of the form 'owner/name'")
    for owner in owners:
        if not OWNER_PATTERN.match(owner):
            raise ConfigError(f"owner {owner!r} is not a valid user or organisation")
    if not repos and not owners:
        raise ConfigError("no 'repos' or 'owners' given")

    return Config(
        repos=list(dict.fromkeys(repos)),
        owners=owners,
        interval=interval,
        theme=theme,
        glyphs=glyphs,
    )


def load(path: Path) -> Config:
    try:
        text = path.read_text()
    except FileNotFoundError:
        raise ConfigError(
            f"{path} does not exist; create it, for example:\n\n{EXAMPLE}"
        ) from None
    try:
        return parse(text)
    except ConfigError as exc:
        raise ConfigError(f"{path}: {exc}") from None
