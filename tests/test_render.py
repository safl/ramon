# SPDX-FileCopyrightText: Simon A. F. Lund <os@safl.dk>
#
# SPDX-License-Identifier: GPL-2.0-only

import pytest
from rich.cells import cell_len

from ramon import render


@pytest.mark.parametrize("name, glyph", render.NERD.items())
def test_glyphs_are_one_cell_in_the_private_use_area(name, glyph):
    # A glyph Rich measured as two cells would shift every column after it
    assert len(glyph) == 1 and 0xE000 <= ord(glyph) <= 0xF8FF, name
    assert cell_len(glyph) == 1, name


@pytest.mark.parametrize("state", [*render.CHECKS, None])
def test_checks_text_and_glyph(state):
    text, glyph = render.checks(state), render.checks(state, nerd=True)
    assert text.style == glyph.style
    if state is None:
        assert str(text) == str(glyph) == "-"
    else:
        assert str(text).isalpha()
        assert str(glyph) in render.NERD.values()


@pytest.mark.parametrize(
    "decision, draft, glyph",
    [
        ("APPROVED", False, "check"),
        ("CHANGES_REQUESTED", False, "file_diff"),
        ("REVIEW_REQUIRED", False, "eye"),
        ("APPROVED", True, "draft"),
    ],
)
def test_review_glyph(decision, draft, glyph):
    assert str(render.review(decision, draft, nerd=True)) == render.NERD[glyph]
    assert str(render.review(decision, draft)).isalpha()


def test_labels():
    assert render.tab_label("prs", 3) == "Pull requests (3)"
    assert (
        render.tab_label("issues", 9, nerd=True) == f"{render.NERD['issue']} Issues (9)"
    )
    assert render.release(None, nerd=True) == "-"
    assert render.release("v1", nerd=True) == f"{render.NERD['tag']} v1"
    assert str(render.attention()) == "!"
    assert str(render.attention(nerd=True)) == render.NERD["alert"]
