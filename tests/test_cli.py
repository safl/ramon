# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only

from datetime import UTC, datetime

import ramon
from ramon import github

NAMES = ["o/ok", "o/missing", "o/red"]


def test_plain_prints_table_and_errors(payload, tmp_path, monkeypatch, capsys):
    async def fetch(repos, owners):
        assert repos == NAMES
        viewer, parsed = github.parse_response(NAMES, payload)
        return github.Snapshot(viewer, parsed, datetime.now(UTC))

    monkeypatch.setattr(github, "fetch", fetch)
    cfg = tmp_path / "config.toml"
    cfg.write_text(f"repos = {NAMES!r}".replace("'", '"'))

    assert ramon.main(["--config", str(cfg), "--plain"]) == 1
    out = capsys.readouterr().out
    assert "o/ok" in out and "v0.8.0" in out
    assert "o/missing: Could not resolve" in out


def test_missing_config_exits_2(tmp_path, capsys):
    assert ramon.main(["--config", str(tmp_path / "none.toml")]) == 2
    assert "does not exist" in capsys.readouterr().err


def test_theme_from_config(tmp_path, monkeypatch):
    from ramon.app import RamonApp

    themes = []
    monkeypatch.setattr(RamonApp, "run", lambda app: themes.append(app.theme))
    cfg = tmp_path / "config.toml"
    cfg.write_text('repos = ["a/b"]\ntheme = "nord"')
    assert ramon.main(["--config", str(cfg)]) == 0
    assert themes == ["nord"]


def test_unknown_theme_exits_2(tmp_path, capsys):
    cfg = tmp_path / "config.toml"
    cfg.write_text('repos = ["a/b"]\ntheme = "no-such-theme"')
    assert ramon.main(["--config", str(cfg)]) == 2
    assert "unknown theme 'no-such-theme'; one of:" in capsys.readouterr().err
