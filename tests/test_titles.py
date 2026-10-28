from __future__ import annotations

from pathlib import Path

import pytest

from monpiz_lookbook.fonts import register_fonts
from monpiz_lookbook.pages.base import fit_to_width
from monpiz_lookbook.surface import text_width
from monpiz_lookbook.theme import default_theme

FONTS = Path(__file__).parents[1] / "assets" / "fonts"


@pytest.fixture(autouse=True, scope="module")
def fonts() -> None:
    register_fonts(FONTS)


def test_a_short_title_keeps_its_size() -> None:
    style = default_theme().type.model_title
    assert fit_to_width("Cortina", style, 520) is style


def test_a_long_title_shrinks_to_the_width() -> None:
    style = default_theme().type.model_title
    fitted = fit_to_width("Anfibio Stringato", style, 520)
    assert fitted.size < style.size
    assert text_width("Anfibio Stringato", fitted) == pytest.approx(520, abs=0.5)
    assert fitted.leading / fitted.size == pytest.approx(style.leading / style.size)
