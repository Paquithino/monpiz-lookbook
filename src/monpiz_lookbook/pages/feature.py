"""Feature page: a "breathing" page between the denser ones.

One photo across the whole page, darkened at the bottom, with a small
label, a title and a line of text. It breaks the rhythm of the product
pages the way a magazine alternates spreads.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box
from ..models import Feature
from ..surface import Surface
from .base import RenderContext

SHADE = 0.62
SHADE_START = 0.55
LABEL_BASELINE = 690.0
TITLE_BASELINE = 730.0
TEXT_OFFSET = 24.0  # title baseline -> text
TEXT_WIDTH = 330.0
MAX_TEXT_LINES = 2


@dataclass(frozen=True, slots=True)
class FeaturePage:
    feature: Feature
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        f = self.feature
        image = ctx.images.shaded(
            f.image,
            g.width,
            g.height,
            strength=SHADE,
            start=SHADE_START,
            focus_y=f.focus_y,
            focus_x=f.focus_x,
        )
        surface.image(image, Box(0, 0, g.width, g.height))
        x = g.margin_x
        surface.text(f.label, x, LABEL_BASELINE, t.label.with_color(p.on_dark))
        surface.text(f.title, x - 2, TITLE_BASELINE, t.feature_title)
        if f.text:
            style = t.text.with_color(p.on_dark_muted)
            if len(surface.lines(f.text, style, TEXT_WIDTH)) > MAX_TEXT_LINES:
                raise LayoutError(f"Il testo della pagina «{f.title}» è troppo lungo: massimo due righe.")
            surface.paragraph(f.text, x, TITLE_BASELINE + TEXT_OFFSET, TEXT_WIDTH, style)
