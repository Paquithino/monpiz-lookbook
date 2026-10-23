"""Back cover: logo, invitation and contacts, centred on the dark olive."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Closing
from ..surface import Align, Surface
from .base import RenderContext, draw_logo, logo_height

LOGO_WIDTH = 170.0
LOGO_BOTTOM = 380.0
TITLE_BASELINE = 452.0
TEXT_OFFSET = 28.0  # title baseline -> text first baseline
TEXT_WIDTH = 300.0
CONTACTS_OFFSET = 40.0  # text last baseline -> first contact row
CONTACT_SEPARATOR = "  ·  "


@dataclass(frozen=True, slots=True)
class ClosingPage:
    closing: Closing
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        centre = g.width / 2
        surface.fill_page(p.olive, g.width)

        logo_top = LOGO_BOTTOM - logo_height(ctx, LOGO_WIDTH)
        draw_logo(surface, ctx, centre - LOGO_WIDTH / 2, logo_top, LOGO_WIDTH, p.on_dark)

        surface.text(self.closing.title, centre, TITLE_BASELINE, t.closing_title, Align.CENTER)
        end = surface.paragraph(
            self.closing.text,
            centre - TEXT_WIDTH / 2,
            TITLE_BASELINE + TEXT_OFFSET,
            TEXT_WIDTH,
            t.lead,
            Align.CENTER,
        )
        baseline = end + CONTACTS_OFFSET
        for row in self.closing.contacts:
            surface.text(CONTACT_SEPARATOR.join(row), centre, baseline, t.contact, Align.CENTER)
            baseline += t.contact.leading
