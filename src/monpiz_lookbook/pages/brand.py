"""Brand page: the story beside a tall heritage photo, then construction details.

The heritage photo is portrait (boots in front of an archive print), so it
takes a tall column on the right instead of a wide banner, which would cut
the boots off. The paragraphs run down the left column, beside it.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box
from ..models import Brand
from ..surface import Surface
from .base import RenderContext, draw_header

BODY_BASELINE = 134.4
PARAGRAPH_GAP = 12.0  # extra space between paragraphs, on top of the leading
PHOTO_TOP = 122.0
PHOTO_WIDTH = 262.0
PHOTO_HEIGHT = 380.0
TEXT_GAP = 26.0  # between the text column and the photo
DETAILS_EYEBROW_BASELINE = 548.0
DETAIL_IMAGE_TOP = 568.0
DETAIL_IMAGE_SIZE = 62.0
DETAIL_TITLE_BASELINE = 651.0
DETAIL_TEXT_BASELINE = 675.8
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

        photo = Box(g.width - g.margin_x - PHOTO_WIDTH, PHOTO_TOP, PHOTO_WIDTH, PHOTO_HEIGHT)
        image = ctx.images.cropped(
            self.brand.banner.path, photo.width, photo.height, self.brand.banner.focus_y
        )
        surface.image(image, photo, radius=g.radius)

        text_width = photo.x - TEXT_GAP - g.margin_x
        baseline = BODY_BASELINE
        for paragraph in self.brand.paragraphs:
            last = surface.paragraph(paragraph, g.margin_x, baseline, text_width, t.body)
            baseline = last + t.body.leading + PARAGRAPH_GAP
        if last > photo.bottom:
            raise LayoutError("Il testo della pagina del marchio è troppo lungo: accorciare i paragrafi.")

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
