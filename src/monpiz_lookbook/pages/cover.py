"""Cover: logo, the boots in front of a line-drawn Dolomite range, claim.

A white page that matches the product shot's backdrop. The massif is drawn
in flat facets of pale olive tints, outlined by a ridge line in the logo's
olive, with snowfields at its foot. The photo is blended in multiply mode, so
its white backdrop disappears and the boots stand on the snow at the foot of
the mountains. The boots are placed by the
box of the subject inside the photo, not by the photo frame.
"""

from __future__ import annotations

from dataclasses import dataclass

from reportlab.lib.colors import Color

from ..geometry import Box
from ..models import Cover
from ..mountain import MASSIF, Tone, place
from ..surface import Align, Surface, text_width
from ..theme import Palette
from .base import RenderContext

LOGO_TOP = 70.0
LOGO_WIDTH = 220.0
TAGLINE_GAP = 30.0  # logo bottom -> tagline baseline

# Placement of the 1000 x 700 design box of ``mountain.MASSIF``.
MASSIF_X = -20.0
MASSIF_TOP = 236.0
MASSIF_SCALE = 0.64
RIDGE_WIDTH = 1.2
PHOTO_WHITE_POINT = 238  # backdrop greys at or above this become pure white

BOOTS_WIDTH = 330.0  # width of the subject (the pair of boots) on the page
SOLES_Y = 700.0  # where the bottom of the subject sits

CLAIM_BASELINE = 738.0
CLAIM_WIDTH = 380.0
LABELS_BASELINE = 797.7
LABELS_GAP = 29.5


def _tone_color(palette: Palette, tone: Tone) -> Color:
    """Monochrome olive tints: the massif reads as a drawing behind the photo."""
    return {
        Tone.ROCK: palette.tint_rock,
        Tone.LIT: palette.tint_lit,
        Tone.SHADOW: palette.tint_shadow,
        Tone.SNOW: palette.white,
        Tone.SNOW_SHADE: palette.white,  # snow melts into the page: no bottom edge
    }[tone]


@dataclass(frozen=True, slots=True)
class CoverPage:
    cover: Cover
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        centre = g.width / 2
        surface.fill_page(p.white, g.width)

        facets = place(MASSIF, MASSIF_X, MASSIF_TOP, MASSIF_SCALE)
        for facet in facets:
            surface.polygon(facet.points, _tone_color(p, facet.tone))
        skyline = facets[0].points[:-2]  # the silhouette without its closing bottom edge
        surface.polyline(skyline, p.ridge, RIDGE_WIDTH)
        self._draw_boots(surface, ctx)

        logo_w, logo_h = ctx.images.size(ctx.logo)
        logo_height = LOGO_WIDTH * logo_h / logo_w
        logo_box = Box(centre - LOGO_WIDTH / 2, LOGO_TOP, LOGO_WIDTH, logo_height)
        surface.image(ctx.images.fitted(ctx.logo, logo_box.width, logo_box.height), logo_box)
        tagline_style = t.cover_label.with_color(p.ink)
        surface.text(self.cover.tagline, centre, logo_box.bottom + TAGLINE_GAP, tagline_style, Align.CENTER)

        claim_style = t.cover_claim.with_color(p.ink)
        surface.paragraph(
            self.cover.claim, centre - CLAIM_WIDTH / 2, CLAIM_BASELINE, CLAIM_WIDTH, claim_style, Align.CENTER
        )
        self._draw_highlights(surface, ctx, centre)

    def _draw_boots(self, surface: Surface, ctx: RenderContext) -> None:
        g = ctx.theme.grid
        left, _, right, bottom = ctx.images.subject_bounds(self.cover.photo)
        px_w, px_h = ctx.images.size(self.cover.photo)
        width = BOOTS_WIDTH / (right - left)
        height = width * px_h / px_w
        box = Box(g.width / 2 - (left + right) / 2 * width, SOLES_Y - bottom * height, width, height)
        photo = ctx.images.fitted(self.cover.photo, box.width, box.height, white_point=PHOTO_WHITE_POINT)
        surface.image(photo, box, multiply=True)

    def _draw_highlights(self, surface: Surface, ctx: RenderContext, centre: float) -> None:
        t = ctx.theme.type
        style = t.cover_label.with_color(ctx.theme.palette.faint)
        labels = self.cover.highlights
        if not labels:
            return
        widths = [text_width(label, style) for label in labels]
        x = centre - (sum(widths) + LABELS_GAP * (len(labels) - 1)) / 2
        for label, width in zip(labels, widths, strict=True):
            surface.text(label, x, LABELS_BASELINE, style)
            x += width + LABELS_GAP
