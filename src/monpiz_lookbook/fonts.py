"""Registration of the embedded fonts."""

from __future__ import annotations

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from .errors import ContentError
from .theme import Font


def register_fonts(fonts_dir: Path) -> None:
    """Register every :class:`Font` from ``<fonts_dir>/<name>.ttf``. Idempotent."""
    registered = set(pdfmetrics.getRegisteredFontNames())
    for font in Font:
        if font.value in registered:
            continue
        path = fonts_dir / f"{font.value}.ttf"
        if not path.is_file():
            raise ContentError(f"Font mancante: {path}")
        pdfmetrics.registerFont(TTFont(font.value, str(path)))
