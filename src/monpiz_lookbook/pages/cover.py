"""Cover: logo, the boots in front of a Dolomite skyline, claim.

A paper-coloured page. The mountains are ink lines only: an outline with
pointed spires and thin spines down their faces. The product shot is blended
in multiply mode: its white backdrop takes the colour of the paper, so the
boots stand in front of the mountains without any frame. The boots are placed
by the box of the subject inside the photo, not by the photo frame.
Everything is centred.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..geometry import Box
from ..models import Cover
from ..mountain import SKYLINE, SPINES, place
from ..surface import Align, Surface, text_width
from .base import RenderContext

LOGO_TOP = 70.0
LOGO_WIDTH = 220.0
TAGLINE_GAP = 30.0  # logo bottom -> tagline baseline

# Placement of the 1000 x 700 design box of ``mountain.SKYLINE``.
SKYLINE_X = -20.0
SKYLINE_TOP = 236.0
SKYLINE_SCALE = 0.64
SKYLINE_WIDTH = 1.2
SPINE_WIDTH = 0.6

BOOTS_WIDTH = 330.0  # width of the subject (the pair of boots) on the page
SOLES_Y = 700.0  # where the bottom of the subject sits
SUBJECT_MARGIN = 0.06  # photo kept around the subject, as a fraction of the photo

# Banner: a full-bleed photo across the top (the logo embossed on the tongue),
# with the printed logo below it on the paper. Its lower edge is the skyline itself, flattened:
# the paper rises into the photo as mountains, outlined in ink.
BANNER_EDGE_TOP = 238.0  # where the flattened skyline starts (its highest peak)
BANNER_EDGE_SCALE_Y = 0.24
BANNER_LOGO_TOP = 344.0  # the printed logo sits on the paper, under the photo
BANNER_LOGO_WIDTH = 140.0
BANNER_TAGLINE_GAP = 22.0
BANNER_BOOTS_WIDTH = 280.0  # boots a little smaller, to leave room for the logo
BANNER_SOLES_Y = 716.0

CLAIM_BASELINE = 738.0
CLAIM_WIDTH = 380.0
LABELS_BASELINE = 797.7
LABELS_GAP = 29.5


@dataclass(frozen=True, slots=True)
class CoverPage:
    cover: Cover
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        centre = g.width / 2
        surface.fill_page(p.paper, g.width)

        banner = self.cover.banner
        if banner is None:
            surface.polyline(place(SKYLINE, SKYLINE_X, SKYLINE_TOP, SKYLINE_SCALE), p.ink, SKYLINE_WIDTH)
            for spine in SPINES:
                surface.polyline(place(spine, SKYLINE_X, SKYLINE_TOP, SKYLINE_SCALE), p.ink, SPINE_WIDTH)
        if banner is None:
            self._draw_boots(surface, ctx, BOOTS_WIDTH, SOLES_Y)
        else:
            self._draw_boots(surface, ctx, BANNER_BOOTS_WIDTH, BANNER_SOLES_Y)

        tagline_style = t.cover_label.with_color(p.ink)
        if banner is not None:
            edge = place(SKYLINE, SKYLINE_X, BANNER_EDGE_TOP, SKYLINE_SCALE, BANNER_EDGE_SCALE_Y)
            box = Box(0, 0, g.width, max(y for _, y in edge))
            outline = [(0.0, 0.0), (g.width, 0.0), (g.width, edge[-1][1]), *reversed(edge), (0.0, edge[0][1])]
            surface.image(ctx.images.cropped(banner, box.width, box.height), box, clip=outline)
            surface.polyline(edge, p.ink, SKYLINE_WIDTH)
            logo_top, logo_width, tagline_gap = BANNER_LOGO_TOP, BANNER_LOGO_WIDTH, BANNER_TAGLINE_GAP
        else:
            logo_top, logo_width, tagline_gap = LOGO_TOP, LOGO_WIDTH, TAGLINE_GAP
        logo_w, logo_h = ctx.images.size(ctx.logo)
        logo_box = Box(centre - logo_width / 2, logo_top, logo_width, logo_width * logo_h / logo_w)
        surface.image(ctx.images.fitted(ctx.logo, logo_box.width, logo_box.height), logo_box)
        tagline_baseline = logo_box.bottom + tagline_gap
        surface.text(self.cover.tagline, centre, tagline_baseline, tagline_style, Align.CENTER)

        claim_style = t.cover_claim.with_color(p.ink)
        surface.paragraph(
            self.cover.claim, centre - CLAIM_WIDTH / 2, CLAIM_BASELINE, CLAIM_WIDTH, claim_style, Align.CENTER
        )
        self._draw_highlights(surface, ctx, centre)

    def _draw_boots(self, surface: Surface, ctx: RenderContext, boots_width: float, soles_y: float) -> None:
        """Scale the photo so the subject is ``boots_width`` wide and centred, soles on ``soles_y``.

        Only the subject plus a margin is embedded, with feathered borders.
        """
        g = ctx.theme.grid
        left, top, right, bottom = ctx.images.subject_bounds(self.cover.photo)
        px_w, px_h = ctx.images.size(self.cover.photo)
        width = boots_width / (right - left)  # page width of the whole photo
        height = width * px_h / px_w
        origin_x = g.width / 2 - (left + right) / 2 * width
        origin_y = soles_y - bottom * height

        m = SUBJECT_MARGIN
        region = (max(0.0, left - m), max(0.0, top - m), min(1.0, right + m), min(1.0, bottom + m))
        box = Box(
            origin_x + region[0] * width,
            origin_y + region[1] * height,
            (region[2] - region[0]) * width,
            (region[3] - region[1]) * height,
        )
        photo = ctx.images.on_white(self.cover.photo, box.width, box.height, region=region)
        surface.image(photo, box, multiply=True)

    def _draw_highlights(self, surface: Surface, ctx: RenderContext, centre: float) -> None:
        labels = self.cover.highlights
        if not labels:
            return
        style = ctx.theme.type.cover_label.with_color(ctx.theme.palette.faint)
        widths = [text_width(label, style) for label in labels]
        x = centre - (sum(widths) + LABELS_GAP * (len(labels) - 1)) / 2
        for label, width in zip(labels, widths, strict=True):
            surface.text(label, x, LABELS_BASELINE, style)
            x += width + LABELS_GAP
