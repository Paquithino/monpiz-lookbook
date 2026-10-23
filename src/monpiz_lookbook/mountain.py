"""The cover illustration: a stylised Dolomite massif.

The massif is drawn by hand as flat facets in a 1000 x 700 design box, in
the manner of alpine posters: a rock silhouette, sunlit faces on the left of
each tower, deep shadow on the steep right faces, snow on the lower slopes.
``place`` maps the facets onto the page; colours are chosen by the page.
Coordinates follow the design convention: origin top-left, y downwards.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

Point = tuple[float, float]

BOX_WIDTH = 1000.0
BOX_HEIGHT = 700.0


class Tone(StrEnum):
    ROCK = "rock"  # base silhouette, half light
    LIT = "lit"  # faces catching the low sun
    SHADOW = "shadow"  # steep faces turned away
    SNOW = "snow"
    SNOW_SHADE = "snow_shade"


@dataclass(frozen=True, slots=True)
class Facet:
    tone: Tone
    points: tuple[Point, ...]


def _facet(tone: Tone, *points: Point) -> Facet:
    return Facet(tone, points)


# Drawing order matters: later facets paint over earlier ones.
# Each tower is split along its spine: sunlit plane on the left, shade on the right.
MASSIF: tuple[Facet, ...] = (
    _facet(
        Tone.ROCK,
        (0, 420),
        (60, 380),
        (95, 392),
        (130, 330),
        (150, 318),
        (170, 345),
        (200, 330),
        (230, 270),
        (255, 240),
        (270, 236),
        (290, 262),
        (305, 300),
        (320, 290),
        (345, 200),
        (365, 170),
        (380, 165),
        (395, 190),
        (405, 215),
        (420, 170),
        (440, 110),
        (462, 80),
        (480, 72),
        (500, 84),
        (515, 120),
        (528, 170),
        (540, 205),
        (552, 198),
        (575, 120),
        (595, 95),
        (612, 90),
        (625, 108),
        (640, 150),
        (665, 210),
        (700, 250),
        (740, 270),
        (780, 300),
        (830, 290),
        (880, 330),
        (940, 320),
        (1000, 350),
        (1000, 700),
        (0, 700),
    ),
    # Tower A (far left)
    _facet(Tone.LIT, (60, 380), (95, 392), (130, 330), (150, 318), (140, 440), (70, 460)),
    _facet(Tone.SHADOW, (150, 318), (170, 345), (200, 330), (190, 450), (140, 440)),
    # Tower B
    _facet(Tone.LIT, (200, 330), (230, 270), (255, 240), (270, 236), (262, 330), (240, 460), (190, 450)),
    _facet(Tone.SHADOW, (270, 236), (290, 262), (305, 300), (300, 450), (262, 330)),
    # Tower C
    _facet(Tone.LIT, (320, 290), (345, 200), (365, 170), (380, 165), (372, 290), (350, 440), (300, 450)),
    _facet(Tone.SHADOW, (380, 165), (395, 190), (405, 215), (410, 430), (372, 290)),
    # Main summit D
    _facet(
        Tone.LIT, (405, 215), (420, 170), (440, 110), (462, 80), (480, 72), (470, 200), (450, 330), (410, 430)
    ),
    _facet(Tone.SHADOW, (480, 72), (500, 84), (515, 120), (528, 170), (540, 205), (520, 420), (470, 200)),
    # Tower E
    _facet(Tone.LIT, (552, 198), (575, 120), (595, 95), (612, 90), (602, 220), (585, 330), (548, 410)),
    _facet(Tone.SHADOW, (612, 90), (625, 108), (640, 150), (665, 210), (700, 250), (660, 360), (602, 220)),
    # Right shoulder
    _facet(Tone.SHADOW, (880, 330), (940, 320), (1000, 350), (1000, 440), (900, 430)),
    # Snowfield on the lower slopes, gently undulating.
    _facet(
        Tone.SNOW,
        (0, 488),
        (70, 470),
        (140, 482),
        (220, 462),
        (300, 478),
        (380, 458),
        (460, 474),
        (540, 452),
        (620, 470),
        (700, 448),
        (780, 466),
        (860, 450),
        (940, 468),
        (1000, 456),
        (1000, 700),
        (0, 700),
    ),
    _facet(
        Tone.SNOW_SHADE,
        (0, 540),
        (110, 524),
        (230, 538),
        (360, 518),
        (500, 534),
        (640, 514),
        (780, 532),
        (900, 516),
        (1000, 530),
        (1000, 700),
        (0, 700),
    ),
)


def place(facets: tuple[Facet, ...], x: float, top: float, scale: float) -> list[Facet]:
    """Map facets from the design box onto the page."""
    return [Facet(f.tone, tuple((x + px * scale, top + py * scale) for px, py in f.points)) for f in facets]
