# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only
"""ramon runs inside zellij in Windows Terminal, which take a set of keys
before they reach the application. No binding may use one of them."""

from datetime import UTC, datetime

import pytest
from textual.command import CommandPalette

from ramon import github
from ramon.app import RamonApp

# zellij 0.44, normal mode: Ctrl switches mode or quits; every Alt key is
# also bound (focus, resize, layouts, tabs).
ZELLIJ = {f"ctrl+{c}" for c in "gpnbsothq"}

# Windows Terminal defaults that are not covered by the modifier rules below.
WINDOWS_TERMINAL = {
    "ctrl+tab",
    "ctrl+comma",
    "ctrl+equals_sign",
    "ctrl+minus",
    "ctrl+0",
    "ctrl+v",
    "f11",
}


def reserved(key: str) -> bool:
    mods = set(key.split("+")[:-1])
    if "alt" in mods:
        return True  # zellij Alt keys; Windows Terminal alt+arrows, alt+shift+*
    if {"ctrl", "shift"} <= mods:
        return True  # Windows Terminal ctrl+shift+* (tabs, copy, find, scroll)
    return key in ZELLIJ | WINDOWS_TERMINAL


async def fetch():
    return github.Snapshot("me", [], datetime.now(UTC))


def active_keys(app) -> set[str]:
    keys = set()
    for node in [app, app.screen, *app.screen.walk_children()]:
        keys.update(key for key, _ in node._bindings)
    return keys


@pytest.mark.parametrize("key", ["ctrl+p", "ctrl+q", "alt+left", "ctrl+shift+t"])
def test_reserved_detects(key):
    assert reserved(key)


async def test_no_binding_is_reserved():
    app = RamonApp(fetch, interval=3600)
    async with app.run_test() as pilot:
        await pilot.pause()
        keys = active_keys(app)
    assert {"left", "right", "enter", "a", "r", "t", "q", "ctrl+c", "colon"} <= keys
    assert sorted(k for k in keys if reserved(k)) == []


@pytest.mark.parametrize("key", ["q", "ctrl+c"])
async def test_quit_keys(key):
    app = RamonApp(fetch, interval=3600)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press(key)
        await pilot.pause()
        assert not app.is_running


async def test_colon_opens_command_palette():
    app = RamonApp(fetch, interval=3600)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("colon")
        await pilot.pause()
        assert isinstance(app.screen, CommandPalette)


async def test_t_cycles_themes_and_shows_the_name():
    app = RamonApp(fetch, interval=3600)
    async with app.run_test() as pilot:
        await pilot.pause()
        names = sorted(app.available_themes)
        start = names.index(app.theme)
        await pilot.press("t")
        assert app.theme == names[(start + 1) % len(names)]
        assert app.sub_title.endswith(f"| {app.theme}")
        for _ in range(len(names) - 1):
            await pilot.press("t")
        assert app.theme == names[start]


async def test_footer_has_navigation_left_and_r_t_q_right():
    app = RamonApp(fetch, interval=3600)
    async with app.run_test(size=(140, 30)) as pilot:
        await pilot.pause()
        keys = [
            (w.key, w.region.x)
            for w in app.query("SplitFooter *")
            if getattr(w, "action", None) and w.key != "colon"
        ]
        order = [k for k, _ in keys]
        assert order == ["left", "right", "enter", "a", "r", "t", "q"]
        x = dict(keys)
        gap_between = x["r"] - x["a"]
        gap_within = x["a"] - x["enter"]
        assert x["a"] < 70 < x["r"]
        assert gap_between > 3 * gap_within
        assert str(app.query_one("SplitFooter .spacer").render()) == ""


async def test_arrows_and_enter_belong_to_the_command_palette_while_open():
    app = RamonApp(fetch, interval=3600)
    opened = []
    app.open_url = lambda url, **kw: opened.append(url)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("colon", *"theme")
        await pilot.pause(0.5)
        await pilot.press("right", "enter")
        await pilot.pause(0.5)
        assert app.query_one("#tabs").active == "prs"
        assert opened == []
        # Enter chose 'Change theme', which lists the themes in a new search
        assert app.screen.query_one("Input").value == ""
