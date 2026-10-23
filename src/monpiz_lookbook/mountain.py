"""The cover illustration: a stylised Dolomite massif drawn in ink lines only.

Two sets of strokes in a 1000 x 700 design box:
- ``SKYLINE``: the outline, made of narrow spires with sharp summits, the
  main peak in the middle and lower ridges towards the edges;
- ``SPINES``: thin lines running down the faces from the summits, which give
  the rock its volume without any fill.
``place`` maps any stroke onto the page.
Coordinates follow the design convention: origin top-left, y downwards.
"""

from __future__ import annotations

Point = tuple[float, float]
Stroke = tuple[Point, ...]

BOX_WIDTH = 1000.0
BOX_HEIGHT = 700.0

SKYLINE: Stroke = (
    # Low ridges on the left
    (0, 440), (45, 400), (70, 410), (115, 318), (135, 340),
    # Two lesser spires
    (175, 212), (200, 300), (222, 282), (262, 138), (292, 262), (312, 242),
    # Spire before the main summit
    (352, 108), (372, 182), (386, 168),
    # Main summit
    (447, 28), (500, 192), (515, 176),
    # Twin spire
    (560, 68), (598, 216), (620, 200),
    # Descending ridges on the right
    (668, 148), (705, 266), (730, 250), (780, 212), (815, 310), (850, 296),
    (900, 342), (950, 330), (1000, 366),
)  # fmt: skip

SPINES: tuple[Stroke, ...] = (
    ((175, 212), (183, 292)),
    ((262, 138), (271, 212), (263, 276)),
    ((352, 108), (361, 186)),
    ((447, 28), (456, 116), (443, 200)),
    ((560, 68), (552, 148), (566, 236)),
    ((668, 148), (676, 226)),
    ((780, 212), (773, 280)),
)  # fmt: skip


def place(points: Stroke, x: float, top: float, scale: float) -> list[Point]:
    """Map points from the design box onto the page."""
    return [(x + px * scale, top + py * scale) for px, py in points]
