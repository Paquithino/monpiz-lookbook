"""Back cover.

With a photo: the photo fills the top of the page and a paper band below
holds the logo, the invitation and the contacts, all centred. Without a
photo: the same content on the dark olive.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..geometry import Box
from ..models import Closing
from ..surface import Align, Surface
from .base import RenderContext, draw_logo, logo_height

PHOTO_BOTTOM = 560.0
LOGO_WIDTH = 150.0
LOGO_TOP = 612.0  # with a photo
LOGO_BOTTOM_DARK = 380.0  # without a photo
TITLE_OFFSET = 34.0  # logo bottom -> title baseline
TEXT_OFFSET = 22.0  # title baseline -> text
TEXT_WIDTH = 300.0
RULE_OFFSET = 18.0  # text -> short rule
RULE_LENGTH = 40.0
CONTACTS_OFFSET = 26.0  # rule -> first contact row
CONTACT_SEPARATOR = "  ·  "


@dataclass(frozen=True, slots=True)
class ClosingPage:
    closing: Closing
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        centre = g.width / 2
        photo = self.closing.photo
        dark = photo is None
        if photo is None:
            surface.fill_page(p.olive, g.width)
            logo_top = LOGO_BOTTOM_DARK - logo_height(ctx, LOGO_WIDTH)
            draw_logo(surface, ctx, centre - LOGO_WIDTH / 2, logo_top, LOGO_WIDTH, p.on_dark)
        else:
            surface.fill_page(p.paper, g.width)
            band = Box(0, 0, g.width, PHOTO_BOTTOM)
            surface.image(ctx.images.cropped(photo, band.width, band.height), band)
            logo_top = LOGO_TOP
            px_w, px_h = ctx.images.size(ctx.logo)
            height = LOGO_WIDTH * px_h / px_w
            box = Box(centre - LOGO_WIDTH / 2, logo_top, LOGO_WIDTH, height)
            surface.image(ctx.images.fitted(ctx.logo, box.width, box.height), box)

        ink = p.on_dark if dark else p.ink
        soft = p.on_dark_muted if dark else p.muted
        baseline = logo_top + logo_height(ctx, LOGO_WIDTH) + TITLE_OFFSET
        surface.text(self.closing.title, centre, baseline, t.index_section.with_color(ink), Align.CENTER)
        end = surface.paragraph(
            self.closing.text,
            centre - TEXT_WIDTH / 2,
            baseline + TEXT_OFFSET,
            TEXT_WIDTH,
            t.small.with_color(soft),
            Align.CENTER,
        )
        rule = end + RULE_OFFSET
        surface.hline(centre - RULE_LENGTH / 2, centre + RULE_LENGTH / 2, rule, ink, 0.6)
        for row, contacts in enumerate(self.closing.contacts):
            line = CONTACT_SEPARATOR.join(contacts)
            surface.text(
                line, centre, rule + CONTACTS_OFFSET + row * 16, t.small.with_color(ink), Align.CENTER
            )
