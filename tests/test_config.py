# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only

import pytest

from ramon import config


def test_parse_dedups_repos_and_keeps_order():
    cfg = config.parse(
        'repos = ["a/b", "c/d.e", "a/b"]\nowners = ["xnvme"]\ninterval = 60'
    )
    assert cfg.repos == ["a/b", "c/d.e"]
    assert cfg.owners == ["xnvme"]
    assert cfg.interval == 60


def test_example_parses():
    assert config.parse(config.EXAMPLE).repos == ["xnvme/xnvme"]


@pytest.mark.parametrize(
    "text, message",
    [
        ('repos = ["nope"]', "not of the form"),
        ('repos = ["a/b"]\ninterval = 5', "at least 30"),
        ('repos = ["a/b"]\ninterval = true', "integer"),
        ('repos = "a/b"', "list of strings"),
        ('owners = ["bad/owner"]', "not a valid"),
        ('repos = ["a/b"]\nrepo = []', "unknown keys: repo"),
        ('repos = ["a/b"]\ntheme = 1', "'theme' must be a string"),
        ('repos = ["a/b"]\nglyphs = "emoji"', "'glyphs' must be"),
        ("", "no 'repos' or 'owners'"),
        ("repos = [", "invalid TOML"),
    ],
)
def test_parse_rejects(text, message):
    with pytest.raises(config.ConfigError, match=message):
        config.parse(text)


def test_load_missing_file_shows_example(tmp_path):
    with pytest.raises(config.ConfigError, match="(?s)does not exist.*interval = 300"):
        config.load(tmp_path / "nope.toml")


def test_default_path_honours_environment(monkeypatch, tmp_path):
    monkeypatch.delenv("RAMON_CONFIG", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config.default_path() == tmp_path / "ramon" / "config.toml"
    monkeypatch.setenv("RAMON_CONFIG", "/x.toml")
    assert str(config.default_path()) == "/x.toml"


def test_parse_theme():
    assert config.parse('repos = ["a/b"]\ntheme = "nord"').theme == "nord"
    assert config.parse('repos = ["a/b"]').theme is None


def test_parse_glyphs():
    assert config.parse('repos = ["a/b"]').glyphs == "text"
    assert config.parse('repos = ["a/b"]\nglyphs = "nerd"').glyphs == "nerd"
