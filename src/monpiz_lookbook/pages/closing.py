"""Back cover.

With a photo: the photo fills the top of the page and a paper band below
holds the invitation ("Il tuo viaggio inizia con..."), the logo that answers
it, the text and the contacts, all centred. Without a
photo: the same content on the dark olive.
"""

from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib.colors import Color

from ..contacts import contact_list
from ..geometry import Box
from ..i18n import tr
from ..models import Closing
from ..surface import Align, Surface
from .base import RenderContext, draw_logo, logo_height

PHOTO_BOTTOM = 560.0
LOGO_WIDTH = 150.0
BLOCK_TOP = 600.0  # with a photo: top of the title
LOGO_BOTTOM_DARK = 380.0  # without a photo
TITLE_CAP = 22.0  # top of the title -> its baseline
TITLE_TO_LOGO = 18.0  # title baseline -> logo top
LOGO_TO_TEXT = 26.0  # logo bottom -> text
TEXT_WIDTH = 300.0
RULE_OFFSET = 18.0  # text -> short rule
RULE_LENGTH = 40.0
CONTACTS_OFFSET = 30.0  # rule -> contact labels
CONTACT_VALUE_DROP = 14.0  # label baseline -> value baseline
CONTACT_COLUMN = 128.0  # width of each contact column


@dataclass(frozen=True, slots=True)
class ClosingPage:
    closing: Closing
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        """The invitation first, then the logo as its answer, then the text and contacts."""
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        centre = g.width / 2
        photo = self.closing.photo
        dark = photo is None
        logo_h = logo_height(ctx, LOGO_WIDTH)
        if photo is None:
            surface.fill_page(p.olive, g.width)
            top = LOGO_BOTTOM_DARK - logo_h - TITLE_TO_LOGO - TITLE_CAP
        else:
            surface.fill_page(p.paper, g.width)
            band = Box(0, 0, g.width, PHOTO_BOTTOM)
            surface.image(ctx.images.cropped(photo, band.width, band.height), band)
            top = BLOCK_TOP

        ink = p.on_dark if dark else p.ink
        soft = p.on_dark_muted if dark else p.muted
        title = top + TITLE_CAP
        surface.text(self.closing.title, centre, title, t.index_section.with_color(ink), Align.CENTER)

        logo_top = title + TITLE_TO_LOGO
        if dark:
            draw_logo(surface, ctx, centre - LOGO_WIDTH / 2, logo_top, LOGO_WIDTH, p.on_dark)
        else:
            box = Box(centre - LOGO_WIDTH / 2, logo_top, LOGO_WIDTH, logo_h)
            surface.image(ctx.images.fitted(ctx.logo, box.width, box.height), box)

        end = surface.paragraph(
            self.closing.text,
            centre - TEXT_WIDTH / 2,
            logo_top + logo_h + LOGO_TO_TEXT,
            TEXT_WIDTH,
            t.small.with_color(soft),
            Align.CENTER,
        )
        rule = end + RULE_OFFSET
        surface.hline(centre - RULE_LENGTH / 2, centre + RULE_LENGTH / 2, rule, ink, 0.6)
        self._draw_contacts(surface, ctx, rule + CONTACTS_OFFSET, ink, soft)

    def _draw_contacts(
        self, surface: Surface, ctx: RenderContext, top: float, ink: Color, soft: Color
    ) -> None:
        """One column per contact, label above value, thin rules between: Instagram first."""
        t, g = ctx.theme.type, ctx.theme.grid
        items = sorted(contact_list(self.closing.contacts), key=lambda k: k.kind != "instagram")
        if not items:
            return
        width = min(CONTACT_COLUMN, g.content_width / len(items))
        left = g.width / 2 - width * len(items) / 2
        label = t.label.with_color(soft)
        value = t.small.with_color(ink)
        for index, item in enumerate(items):
            x = left + index * width + width / 2
            name = tr("Tel. · WhatsApp") if item.whatsapp else item.label  # shorter in print
            if name:
                surface.text(name, x, top, label, Align.CENTER)
            surface.text(item.text, x, top + CONTACT_VALUE_DROP, value, Align.CENTER)
            if index:
                rule_x = left + index * width
                surface.vline(rule_x, top - 8, top + CONTACT_VALUE_DROP + 2, soft, 0.25)
