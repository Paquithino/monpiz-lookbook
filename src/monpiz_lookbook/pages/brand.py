"""Brand page: story in two columns, heritage banner, construction details."""

from __future__ import annotations

from dataclasses import dataclass

from ..geometry import Box
from ..models import Brand
from ..surface import Surface
from .base import RenderContext, draw_header

BODY_BASELINE = 134.4
BANNER_TOP = 254.4
BANNER_HEIGHT = 179.0
DETAILS_EYEBROW_BASELINE = 468.5
DETAIL_IMAGE_TOP = 490.0
DETAIL_IMAGE_SIZE = 62.0
DETAIL_TITLE_BASELINE = 573.0
DETAIL_TEXT_BASELINE = 597.8
DETAIL_COLUMNS = 4
DETAIL_GUTTER = 16.0


@dataclass(frozen=True, slots=True)
class BrandPage:
    brand: Brand

    @property
    def folio(self) -> str:
        return self.brand.folio

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        surface.fill_page(p.paper, g.width)
        draw_header(surface, ctx, self.brand.eyebrow, self.brand.title)

        column_width = g.column_width(2)
        for index, paragraph in enumerate(self.brand.paragraphs):
            surface.paragraph(paragraph, g.column_x(index, 2), BODY_BASELINE, column_width, t.body)

        banner = Box(g.margin_x, BANNER_TOP, g.content_width, BANNER_HEIGHT)
        image = ctx.images.cropped(
            self.brand.banner.path, banner.width, banner.height, self.brand.banner.focus_y
        )
        surface.image(image, banner, radius=g.radius)

        surface.text(self.brand.details_title, g.margin_x, DETAILS_EYEBROW_BASELINE, t.eyebrow)
        self._draw_details(surface, ctx)

    def _draw_details(self, surface: Surface, ctx: RenderContext) -> None:
        t, g = ctx.theme.type, ctx.theme.grid
        width = g.column_width(DETAIL_COLUMNS, DETAIL_GUTTER)
        size = DETAIL_IMAGE_SIZE
        for index, detail in enumerate(self.brand.details):
            x = g.column_x(index, DETAIL_COLUMNS, DETAIL_GUTTER)
            surface.image(ctx.images.fitted(detail.image, size, size), Box(x, DETAIL_IMAGE_TOP, size, size))
            surface.text(detail.name, x, DETAIL_TITLE_BASELINE, t.detail_title)
            surface.paragraph(detail.description, x, DETAIL_TEXT_BASELINE, width, t.detail_text)
