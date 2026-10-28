"""Thin drawing layer over the ReportLab canvas.

It exposes the handful of primitives the pages need, in the design
coordinate system (origin top-left, y downwards), so page modules read like
the layout spec instead of being littered with ``page_height - y``.

Coordinates are relative to the trimmed page. For print, anything that
touches a trim edge (a page fill, a full-bleed photo) is extended into the
``bleed`` beyond it automatically, so a slightly imprecise cut never leaves
a white hairline. Page modules simply draw up to the page edge.
"""

from __future__ import annotations

from collections.abc import Sequence
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


EDGE_TOLERANCE = 0.5  # pt: a box this close to a trim edge counts as touching it


class Surface:
    def __init__(
        self, canvas: Canvas, page_height: float, *, page_width: float = 0.0, bleed: float = 0.0
    ) -> None:
        self._canvas = canvas
        self._height = page_height
        self._width = page_width
        self._bleed = bleed

    def _y(self, top: float) -> float:
        return self._height - top

    def bled(self, box: Box) -> Box:
        """``box`` with every side that touches a trim edge pushed out into the bleed."""
        if not self._bleed or not self._width:
            return box
        b, tol = self._bleed, EDGE_TOLERANCE
        left = box.x - b if box.x <= tol else box.x
        top = box.top - b if box.top <= tol else box.top
        right = box.right + b if box.right >= self._width - tol else box.right
        bottom = box.bottom + b if box.bottom >= self._height - tol else box.bottom
        return Box(left, top, right - left, bottom - top)

    def _bled_point(self, point: tuple[float, float]) -> tuple[float, float]:
        x, y = point
        if not self._bleed or not self._width:
            return point
        b, tol = self._bleed, EDGE_TOLERANCE
        x = x - b if x <= tol else (x + b if x >= self._width - tol else x)
        y = y - b if y <= tol else (y + b if y >= self._height - tol else y)
        return x, y

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
            if stroke is None:
                box = self.bled(box)
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

    def polyline(self, points: Sequence[tuple[float, float]], color: Color, width: float) -> None:
        """Stroke an open polyline with round joins and caps (design coordinates)."""
        if len(points) < 2:
            return
        c = self._canvas
        c.saveState()
        c.setStrokeColor(color)
        c.setLineWidth(width)
        c.setLineJoin(1)
        c.setLineCap(1)
        path = c.beginPath()
        (x, y), *rest = points
        path.moveTo(x, self._y(y))
        for x, y in rest:
            path.lineTo(x, self._y(y))
        c.drawPath(path, stroke=1, fill=0)
        c.restoreState()

    def dot(self, centre: tuple[float, float], radius: float, color: Color) -> None:
        """A filled circle (design coordinates)."""
        c = self._canvas
        c.saveState()
        c.setFillColor(color)
        c.circle(centre[0], self._y(centre[1]), radius, stroke=0, fill=1)
        c.restoreState()

    # -- images -------------------------------------------------------------

    def image(
        self,
        image: ImageReader,
        box: Box,
        *,
        radius: float = 0.0,
        multiply: bool = False,
        clip: Sequence[tuple[float, float]] | None = None,
    ) -> None:
        """Draw ``image`` into ``box``.

        A box touching a trim edge is extended into the bleed: the image is
        scaled up uniformly (never stretched) to cover the larger box.
        ``multiply`` blends it with what is underneath: white becomes fully
        transparent, so a product shot on white can sit over a drawing.
        ``clip`` (a closed polygon) keeps only the part of the image inside it.
        """
        c = self._canvas
        c.saveState()
        if multiply:
            c.setBlendMode("Multiply")
        if radius:
            path = c.beginPath()
            path.roundRect(box.x, self._y(box.bottom), box.width, box.height, radius)
            c.clipPath(path, stroke=0, fill=0)
        if clip:
            path = c.beginPath()
            (x0, y0), *rest = (self._bled_point(point) for point in clip)
            path.moveTo(x0, self._y(y0))
            for x, y in rest:
                path.lineTo(x, self._y(y))
            path.close()
            c.clipPath(path, stroke=0, fill=0)
        target = self.bled(box)
        if target != box:
            frame = c.beginPath()
            frame.rect(target.x, self._y(target.bottom), target.width, target.height)
            c.clipPath(frame, stroke=0, fill=0)
            scale = max(target.width / box.width, target.height / box.height)
            cx, cy = target.x + target.width / 2, target.top + target.height / 2
            box = Box(
                cx - box.width * scale / 2, cy - box.height * scale / 2, box.width * scale, box.height * scale
            )
        c.drawImage(image, box.x, self._y(box.bottom), box.width, box.height, mask="auto")
        c.restoreState()

    # -- links --------------------------------------------------------------

    def link(self, url: str, box: Box) -> None:
        """Make ``box`` a clickable area opening ``url`` in PDF viewers."""
        rect = (box.x, self._y(box.bottom), box.right, self._y(box.top))
        self._canvas.linkURL(url, rect, relative=0, thickness=0)

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
