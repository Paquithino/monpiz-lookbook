"""Thin drawing layer over the ReportLab canvas.

It exposes the handful of primitives the pages need, in the design
coordinate system (origin top-left, y downwards), so page modules read like
the layout spec instead of being littered with ``page_height - y``.
"""

from __future__ import annotations

from enum import StrEnum

from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas

from .geometry import Box, wrap_text
from .theme import TextStyle


class Align(StrEnum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


def _display(text: str, style: TextStyle) -> str:
    return text.upper() if style.uppercase else text


def text_width(text: str, style: TextStyle) -> float:
    """Advance width of ``text`` rendered in ``style``, tracking included."""
    shown = _display(text, style)
    width = float(stringWidth(shown, style.font, style.size))
    return width + style.tracking * max(len(shown) - 1, 0)


class Surface:
    def __init__(self, canvas: Canvas, page_height: float) -> None:
        self._canvas = canvas
        self._height = page_height

    def _y(self, top: float) -> float:
        return self._height - top

    # -- shapes -------------------------------------------------------------

    def fill_page(self, color: Color, width: float) -> None:
        self.rect(Box(0, 0, width, self._height), fill=color)

    def rect(
        self,
        box: Box,
        *,
        fill: Color | None = None,
        stroke: Color | None = None,
        stroke_width: float = 0.75,
        radius: float = 0.0,
    ) -> None:
        c = self._canvas
        c.saveState()
        if fill is not None:
            c.setFillColor(fill)
        if stroke is not None:
            c.setStrokeColor(stroke)
            c.setLineWidth(stroke_width)
        args = (box.x, self._y(box.bottom), box.width, box.height)
        draw = {"fill": int(fill is not None), "stroke": int(stroke is not None)}
        if radius:
            c.roundRect(*args, radius, **draw)
        else:
            c.rect(*args, **draw)
        c.restoreState()

    def hline(self, x0: float, x1: float, top: float, color: Color, width: float = 0.75) -> None:
        c = self._canvas
        c.saveState()
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.line(x0, self._y(top), x1, self._y(top))
        c.restoreState()

    # -- images -------------------------------------------------------------

    def image(self, image: ImageReader, box: Box, *, radius: float = 0.0) -> None:
        c = self._canvas
        c.saveState()
        if radius:
            path = c.beginPath()
            path.roundRect(box.x, self._y(box.bottom), box.width, box.height, radius)
            c.clipPath(path, stroke=0, fill=0)
        c.drawImage(image, box.x, self._y(box.bottom), box.width, box.height, mask="auto")
        c.restoreState()

    # -- text ---------------------------------------------------------------

    def text(
        self,
        text: str,
        x: float,
        baseline: float,
        style: TextStyle,
        align: Align = Align.LEFT,
    ) -> float:
        """Draw a single line; ``x`` is the left edge, centre or right edge per ``align``.

        Returns the advance width of the line.
        """
        shown = _display(text, style)
        width = text_width(text, style)
        offsets = {Align.LEFT: 0.0, Align.CENTER: width / 2, Align.RIGHT: width}
        left = x - offsets[align]
        t = self._canvas.beginText(left, self._y(baseline))
        t.setFont(style.font, style.size)
        t.setFillColor(style.color)
        t.setCharSpace(style.tracking)
        t.textOut(shown)
        self._canvas.drawText(t)
        return width

    def lines(self, text: str, style: TextStyle, width: float) -> list[str]:
        return wrap_text(_display(text, style), lambda s: text_width(s, style), width)

    def paragraph(
        self,
        text: str,
        x: float,
        baseline: float,
        width: float,
        style: TextStyle,
        align: Align = Align.LEFT,
    ) -> float:
        """Draw wrapped text starting at ``baseline``; returns the last baseline."""
        lines = self.lines(text, style, width)
        anchor = {Align.LEFT: x, Align.CENTER: x + width / 2, Align.RIGHT: x + width}[align]
        for index, line in enumerate(lines):
            self.text(line, anchor, baseline + index * style.leading, style, align)
        return baseline + (len(lines) - 1) * style.leading
