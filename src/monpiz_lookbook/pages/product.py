"""Product page: the photos are the protagonists.

The colourways fill the upper part of the page edge to edge, in a grid that
depends on how many there are (see ``_photo_slots``), separated by a paper
hairline. Each photo keeps the whole shoe and extends its studio backdrop to
fill its slot, with the colour name in its top-left corner. A compact text band at the bottom
holds model, name, description and sizes. A variant without a photo gets a
studio-grey placeholder, so the layout can be reviewed early.

A product can also show a close-up (``closeup``), e.g. a special toe finish:
it takes a column on the right of the photo area, beside the master photo,
with its name in the bottom-left corner.

A product with a colour card (``colors``) is laid out differently: one master
photo on the upper half, the text band, then every colour as a named swatch.
The swatch of the master photo's colour is outlined, so the reader sees which
colour is pictured.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box
from ..models import MAX_COLORS, Closeup, Product, Swatch, Variant
from ..surface import Align, Surface
from .base import EYEBROW_BASELINE, RenderContext, draw_placeholder, photo_label_style


@dataclass(frozen=True, slots=True)
class Layout:
    photos_bottom: float  # photos occupy the page from the top edge to here
    line_baseline: float  # model family eyebrow, first line of the text band


STANDARD = Layout(photos_bottom=664.0, line_baseline=694.0)
WITH_COLORS = Layout(photos_bottom=470.0, line_baseline=500.0)

PHOTO_GAP = 4.0  # paper hairline between stacked photos
LABEL_INSET = 22.0  # colour label distance from the photo's edges
LABEL_CAP = 6.0  # cap height of the label style, to measure the inset from its top
HEADER_CLEARANCE = 22.0  # first-row labels sit this far below the running header
HERO_ROW_HEIGHT = 380.0  # with three variants: height of the top photo

NAME_OFFSET = 34.0  # eyebrow -> name baseline
DESCRIPTION_OFFSET = 24.0  # name baseline -> description
TEXT_COLUMN_WIDTH = 420.0
CONTENT_BOTTOM = 780.0

SPEC_LABEL_TO_VALUE = 18.0
SPEC_GAP = 30.0  # last value baseline -> next label

CLOSEUP_WIDTH = 220.0  # right column of the photo area
CLOSEUP_LABEL_PROBE = (0.0, 0.85, 0.7, 1.0)  # bottom-left corner of the close-up, where its name sits

COLORS_LABEL = "Colori disponibili"
COLORS_EYEBROW_BASELINE = 622.0
COLORS_TOP = 636.0
COLOR_COLUMNS = MAX_COLORS // 2
COLOR_GAP = 10.0
SWATCH_HEIGHT = 40.0
SWATCH_NAME_OFFSET = 12.5  # swatch bottom -> name baseline
COLOR_ROW_GAP = 26.0  # swatch bottom -> next row
MASTER_OUTLINE = 0.9
MASTER_OUTLINE_OFFSET = 3.0  # outside the swatch: visible on dark colours too
MIN_GAP_ABOVE_COLORS = 22.0  # text band bottom -> colours eyebrow


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
        p, g = ctx.theme.palette, ctx.theme.grid
        surface.fill_page(p.paper, g.width)

        closeup = self.product.closeup
        photos_width = g.width - CLOSEUP_WIDTH - PHOTO_GAP if closeup else g.width
        for slot, variant in zip(self._photo_slots(photos_width), self.product.variants, strict=True):
            self._draw_variant(surface, ctx, variant, slot)
        if closeup:
            self._draw_closeup(
                surface,
                ctx,
                closeup,
                Box(g.width - CLOSEUP_WIDTH, 0, CLOSEUP_WIDTH, self.layout.photos_bottom),
            )

        # Running header sits on the photos: dark on studio shots, light on dark photos.
        header = photo_label_style(ctx, self.product.variants[0].image)
        surface.text(self.section_name, g.margin_x, EYEBROW_BASELINE, header)
        counter = f"{self.index:02d} / {self.total:02d}"
        right_photo = closeup.image if closeup else self.product.variants[0].image
        counter_style = photo_label_style(ctx, right_photo, (0.6, 0.0, 1.0, 0.15))
        surface.text(counter, g.width - g.margin_x, EYEBROW_BASELINE, counter_style, Align.RIGHT)

        bottom = max(self._draw_story(surface, ctx), self._draw_specs(surface, ctx))
        limit = COLORS_EYEBROW_BASELINE - MIN_GAP_ABOVE_COLORS if self.product.colors else CONTENT_BOTTOM
        if bottom > limit:
            raise LayoutError(
                f"Il prodotto «{self.product.name}» non entra nella pagina: accorciare la descrizione."
            )
        if self.product.colors:
            self._draw_colors(surface, ctx)

    @property
    def layout(self) -> Layout:
        return WITH_COLORS if self.product.colors else STANDARD

    def _photo_slots(self, page_width: float) -> list[Box]:
        """Full-bleed slots for the variants, laid out by how many there are.

        1: the whole photo area; 2: stacked; 3: a hero on top and two side by
        side below; 4: a 2 x 2 grid. Slots are separated by a paper hairline.
        """
        gap, bottom = PHOTO_GAP, self.layout.photos_bottom
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
    def _draw_closeup(surface: Surface, ctx: RenderContext, closeup: Closeup, slot: Box) -> None:
        surface.image(ctx.images.filled(closeup.image, slot.width, slot.height), slot)
        style = photo_label_style(ctx, closeup.image, CLOSEUP_LABEL_PROBE)
        surface.text(closeup.label, slot.x + LABEL_INSET, slot.bottom - LABEL_INSET, style)

    @staticmethod
    def _draw_variant(surface: Surface, ctx: RenderContext, variant: Variant, slot: Box) -> None:
        g = ctx.theme.grid
        if variant.image is None:
            draw_placeholder(surface, ctx, slot)
        else:
            image = ctx.images.filled(variant.image, slot.width, slot.height)
            surface.image(image, slot)
        # Top-left corner: always free wall, whatever the layout. Slots on the
        # top row keep clear of the running header.
        label_x = max(slot.x + LABEL_INSET, g.margin_x)
        label_baseline = max(slot.top + LABEL_INSET + LABEL_CAP, EYEBROW_BASELINE + HEADER_CLEARANCE)
        surface.text(variant.color, label_x, label_baseline, photo_label_style(ctx, variant.image))

    def _draw_story(self, surface: Surface, ctx: RenderContext) -> float:
        """Family, name and description; returns the last baseline."""
        t, x = ctx.theme.type, ctx.theme.grid.margin_x
        line = self.layout.line_baseline
        surface.text(self.model_name, x, line, t.eyebrow)
        name_end = surface.paragraph(
            self.product.name, x, line + NAME_OFFSET, TEXT_COLUMN_WIDTH, t.product_name
        )
        return surface.paragraph(
            self.product.description, x, name_end + DESCRIPTION_OFFSET, TEXT_COLUMN_WIDTH, t.body
        )

    def _draw_specs(self, surface: Surface, ctx: RenderContext) -> float:
        """Spec list, right-aligned to the margin; returns the last baseline."""
        t, g = ctx.theme.type, ctx.theme.grid
        right = g.width - g.margin_x
        specs = [("Taglie", self.product.sizes)]
        baseline = last = self.layout.line_baseline
        for label, value in specs:
            if not value:
                continue
            surface.text(label, right, baseline, t.folio, Align.RIGHT)
            last = baseline + SPEC_LABEL_TO_VALUE
            surface.text(value, right, last, t.spec_value, Align.RIGHT)
            baseline = last + SPEC_GAP
        return last

    def _draw_colors(self, surface: Surface, ctx: RenderContext) -> None:
        """The colour card: named swatches in rows of COLOR_COLUMNS, master colour outlined."""
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        colors = self.product.colors
        surface.text(f"{COLORS_LABEL} · {len(colors)}", g.margin_x, COLORS_EYEBROW_BASELINE, t.eyebrow)
        width = g.column_width(COLOR_COLUMNS, COLOR_GAP)
        pictured = self.product.master.color.casefold()
        for index, swatch in enumerate(colors):
            row, column = divmod(index, COLOR_COLUMNS)
            top = COLORS_TOP + row * (SWATCH_HEIGHT + COLOR_ROW_GAP)
            box = Box(g.column_x(column, COLOR_COLUMNS, COLOR_GAP), top, width, SWATCH_HEIGHT)
            self._draw_swatch(surface, ctx, swatch, box)
            is_master = swatch.name.casefold() == pictured
            if is_master:
                ring = box.inset(-MASTER_OUTLINE_OFFSET)
                surface.rect(ring, stroke=p.ink, stroke_width=MASTER_OUTLINE)
            style = t.swatch_name.with_color(p.ink) if is_master else t.swatch_name
            surface.text(swatch.name, box.x, box.bottom + SWATCH_NAME_OFFSET, style)

    @staticmethod
    def _draw_swatch(surface: Surface, ctx: RenderContext, swatch: Swatch, box: Box) -> None:
        if swatch.image is None:
            surface.rect(box, fill=ctx.theme.palette.studio)
        else:
            surface.image(ctx.images.cropped(swatch.image, box.width, box.height), box)
