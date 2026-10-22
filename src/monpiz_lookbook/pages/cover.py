"""Cover: full-bleed dark page with the tree silhouettes, logo and claim."""

from __future__ import annotations

from dataclasses import dataclass

from ..geometry import Box
from ..models import Cover
from ..surface import Surface
from .base import RenderContext, draw_logo

FADE_START = 0.38
FADE_END_ALPHA = 0.9
LOGO_TOP = 52.3
LOGO_WIDTH = 48.0
TAGLINE_GAP = 12.6
TAGLINE_BASELINE = 65.7
RULE_TOP = 610.3
RULE_LENGTH = 40.0
TITLE_BASELINE = 668.3
CLAIM_BASELINE = 708.0
CLAIM_WIDTH = 245.0
LABELS_BASELINE = 797.7
LABELS_GAP = 29.5


@dataclass(frozen=True, slots=True)
class CoverPage:
    cover: Cover
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        x = g.margin_x

        surface.fill_page(p.forest, g.width)
        trees = ctx.images.tinted(self.cover.background_mask, p.tree_shadow, g.width, g.height)
        page = Box(0, 0, g.width, g.height)
        surface.image(trees, page)
        # Fade the trees out towards the bottom so the title block stays legible.
        surface.image(ctx.images.vertical_fade(p.forest, FADE_START, FADE_END_ALPHA), page)

        draw_logo(surface, ctx, x, LOGO_TOP, LOGO_WIDTH, p.on_dark)
        tagline_style = t.cover_label.with_color(p.on_dark)
        surface.text(self.cover.tagline, x + LOGO_WIDTH + TAGLINE_GAP, TAGLINE_BASELINE, tagline_style)

        surface.hline(x, x + RULE_LENGTH, RULE_TOP, p.cover_accent, width=1.2)
        surface.text(self.cover.title, x, TITLE_BASELINE, t.cover_title)
        surface.paragraph(self.cover.claim, x, CLAIM_BASELINE, CLAIM_WIDTH, t.cover_claim)

        label_x = x
        for label in self.cover.highlights:
            label_x += surface.text(label, label_x, LABELS_BASELINE, t.cover_label) + LABELS_GAP
