"""Product page: the photos are the protagonists.

The colourways fill the upper part of the page edge to edge, in a grid that
depends on how many there are (see ``_photo_slots``), separated by a paper
hairline. Each photo keeps the whole shoe and extends its studio backdrop to
fill its slot, with the colour name in its top-left corner. A compact text band at the bottom
holds model, name, description and sizes. A variant without a photo gets a
studio-grey placeholder, so the layout can be reviewed early.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box
from ..models import Product, Variant
from ..surface import Align, Surface
from .base import EYEBROW_BASELINE, RenderContext, draw_placeholder

PHOTOS_BOTTOM = 664.0  # photos occupy the page from the top edge to here
PHOTO_GAP = 4.0  # paper hairline between stacked photos
LABEL_INSET = 22.0  # colour label distance from the photo's edges
LABEL_CAP = 6.0  # cap height of the label style, to measure the inset from its top
HEADER_CLEARANCE = 22.0  # first-row labels sit this far below the running header
HERO_ROW_HEIGHT = 380.0  # with three variants: height of the top photo

LINE_BASELINE = 694.0  # model family eyebrow
NAME_OFFSET = 34.0  # eyebrow -> name baseline
DESCRIPTION_OFFSET = 24.0  # name baseline -> description
TEXT_COLUMN_WIDTH = 420.0
CONTENT_BOTTOM = 780.0

SPEC_LABEL_TO_VALUE = 18.0
SPEC_GAP = 30.0  # last value baseline -> next label


@dataclass(frozen=True, slots=True)
class ProductPage:
    section_name: str
    model_name: str
    product: Product
    index: int  # 1-based position within the section
    total: int

    @property
    def folio(self) -> str:
        return self.section_name

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        surface.fill_page(p.paper, g.width)

        for slot, variant in zip(self._photo_slots(g.width), self.product.variants, strict=True):
            self._draw_variant(surface, ctx, variant, slot)

        # Running header sits on the first photo (light studio backdrop).
        surface.text(self.section_name, g.margin_x, EYEBROW_BASELINE, t.photo_label)
        counter = f"{self.index:02d} / {self.total:02d}"
        surface.text(counter, g.width - g.margin_x, EYEBROW_BASELINE, t.photo_label, Align.RIGHT)

        bottom = max(self._draw_story(surface, ctx), self._draw_specs(surface, ctx))
        if bottom > CONTENT_BOTTOM:
            raise LayoutError(
                f"Il prodotto «{self.product.name}» non entra nella pagina: accorciare la descrizione."
            )

    def _photo_slots(self, page_width: float) -> list[Box]:
        """Full-bleed slots for the variants, laid out by how many there are.

        1: the whole photo area; 2: stacked; 3: a hero on top and two side by
        side below; 4: a 2 x 2 grid. Slots are separated by a paper hairline.
        """
        gap, bottom = PHOTO_GAP, PHOTOS_BOTTOM
        half = (page_width - gap) / 2
        match len(self.product.variants):
            case 1:
                return [Box(0, 0, page_width, bottom)]
            case 2:
                height = (bottom - gap) / 2
                return [Box(0, 0, page_width, height), Box(0, height + gap, page_width, height)]
            case 3:
                low = HERO_ROW_HEIGHT + gap
                height = bottom - low
                return [
                    Box(0, 0, page_width, HERO_ROW_HEIGHT),
                    Box(0, low, half, height),
                    Box(half + gap, low, half, height),
                ]
            case _:
                height = (bottom - gap) / 2
                return [
                    Box(column * (half + gap), row * (height + gap), half, height)
                    for row in range(2)
                    for column in range(2)
                ]

    @staticmethod
    def _draw_variant(surface: Surface, ctx: RenderContext, variant: Variant, slot: Box) -> None:
        t, g = ctx.theme.type, ctx.theme.grid
        if variant.image is None:
            draw_placeholder(surface, ctx, slot)
        else:
            image = ctx.images.bled(variant.image, slot.width, slot.height)
            surface.image(image, slot)
        # Top-left corner: always free wall, whatever the layout. Slots on the
        # top row keep clear of the running header.
        label_x = max(slot.x + LABEL_INSET, g.margin_x)
        label_baseline = max(slot.top + LABEL_INSET + LABEL_CAP, EYEBROW_BASELINE + HEADER_CLEARANCE)
        surface.text(variant.color, label_x, label_baseline, t.photo_label)

    def _draw_story(self, surface: Surface, ctx: RenderContext) -> float:
        """Family, name and description; returns the last baseline."""
        t, x = ctx.theme.type, ctx.theme.grid.margin_x
        surface.text(self.model_name, x, LINE_BASELINE, t.eyebrow)
        name_end = surface.paragraph(
            self.product.name, x, LINE_BASELINE + NAME_OFFSET, TEXT_COLUMN_WIDTH, t.product_name
        )
        return surface.paragraph(
            self.product.description, x, name_end + DESCRIPTION_OFFSET, TEXT_COLUMN_WIDTH, t.body
        )

    def _draw_specs(self, surface: Surface, ctx: RenderContext) -> float:
        """Spec list, right-aligned to the margin; returns the last baseline."""
        t, g = ctx.theme.type, ctx.theme.grid
        right = g.width - g.margin_x
        specs = [("Taglie", self.product.sizes)]
        baseline = last = LINE_BASELINE
        for label, value in specs:
            if not value:
                continue
            surface.text(label, right, baseline, t.folio, Align.RIGHT)
            last = baseline + SPEC_LABEL_TO_VALUE
            surface.text(value, right, last, t.spec_value, Align.RIGHT)
            baseline = last + SPEC_GAP
        return last
