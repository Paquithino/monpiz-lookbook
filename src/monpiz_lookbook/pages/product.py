"""Product page: the photos are the protagonists.

The colourways fill the upper part of the page edge to edge, in a grid that
depends on how many there are (see ``_photo_slots``), separated by a paper
hairline, with the colour name in the bottom-left corner of each photo.
A variant without a photo gets a studio-grey placeholder.

Below the photos, a text band: the model in small olive capitals, the product
name without the model's name (``Cortina Dakar`` -> ``Dakar``), the
description on the left and a spec table on the right.

A product can show a close-up (``closeup``), e.g. a special toe finish, in a
column on the right of the photo area.

A product with a colour card (``colors``) has one master photo and lists its
colours below. The card adapts to their number: up to four colours get large
swatches, more get a compact grid of seven per row. The pictured colour is
underlined.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..errors import LayoutError
from ..geometry import Box
from ..models import MAX_COLORS, Closeup, Product, Swatch, Variant
from ..surface import Align, Surface
from ..theme import Font
from .base import (
    RUNNING_HEAD_BASELINE,
    RenderContext,
    draw_placeholder,
    draw_spec_table,
    fit_to_width,
    label_on,
)

PHOTOS_BOTTOM = 600.0  # without a colour card
PHOTOS_BOTTOM_WITH_COLORS = 452.0
PHOTO_GAP = 4.0  # paper hairline between photos
HERO_ROW_SHARE = 0.6  # with three variants: share of the height of the top photo
LABEL_INSET = 22.0  # colour label distance from the photo's edges
LABEL_CAP = 5.0  # cap height of the label style, to measure the inset from its top
HEADER_CLEARANCE = 22.0  # top-row labels sit this far below the running head
LEFT_PROBE = (0.0, 0.0, 0.35, 0.12)
RIGHT_PROBE = (0.65, 0.0, 1.0, 0.12)
CORNER_PROBE = (0.0, 0.85, 0.45, 1.0)  # bottom-left corner of a photo
TOP_CORNER_PROBE = (0.0, 0.0, 0.45, 0.15)

EYEBROW_OFFSET = 46.0  # photos bottom -> model eyebrow baseline
TITLE_OFFSET = 92.0  # photos bottom -> product name baseline
TEXT_OFFSET = 122.0  # photos bottom -> description
SPECS_OFFSET = 56.0  # photos bottom -> first spec row
TEXT_WIDTH = 300.0
SPECS_X = 382.0
TITLE_GAP = 16.0  # the product name stops this far before the spec table
CONTENT_BOTTOM = 780.0

CLOSEUP_WIDTH = 220.0  # right column of the photo area

FEW_COLORS = 4  # up to this many colours, large swatches
FEW = {"label": 214.0, "height": 74.0, "pitch": 0.0, "name": 20.0}
MANY = {"label": 176.0, "height": 38.0, "pitch": 66.0, "name": 16.0}
COLOR_COLUMNS = MAX_COLORS // 2
SWATCH_TOP_OFFSET = 12.0  # colours label baseline -> swatches
FEW_GAP = 12.0
MANY_GAP = 8.0
MASTER_RULE = 1.4
MASTER_RULE_DROP = 4.0  # swatch bottom -> underline
TEXT_TO_COLORS = 20.0  # minimum gap between the text band and the colours label


def short_name(product: str, model: str) -> str:
    """The product name without the model's name in front: ``Cortina Dakar`` -> ``Dakar``."""
    if product.casefold().startswith(model.casefold() + " "):
        return product[len(model) + 1 :].strip()
    return product


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

    @property
    def photos_bottom(self) -> float:
        return PHOTOS_BOTTOM_WITH_COLORS if self.product.colors else PHOTOS_BOTTOM

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, g = ctx.theme.palette, ctx.theme.grid
        surface.fill_page(p.paper, g.width)

        closeup = self.product.closeup
        photos_width = g.width - CLOSEUP_WIDTH - PHOTO_GAP if closeup else g.width
        single = len(self.product.variants) == 1
        for slot, variant in zip(self._photo_slots(photos_width), self.product.variants, strict=True):
            self._draw_variant(surface, ctx, variant, slot, single=single)
        if closeup:
            slot = Box(g.width - CLOSEUP_WIDTH, 0, CLOSEUP_WIDTH, self.photos_bottom)
            self._draw_closeup(surface, ctx, closeup, slot)

        first = self.product.variants[0].image
        right_photo = closeup.image if closeup else first
        x, right = g.margin_x, g.width - g.margin_x
        head = ctx.theme.type.running_head
        surface.text(self.model_name, x, RUNNING_HEAD_BASELINE, label_on(ctx, first, LEFT_PROBE, head))
        counter = f"{self.index:02d} / {self.total:02d}"
        surface.text(
            counter, right, RUNNING_HEAD_BASELINE, label_on(ctx, right_photo, RIGHT_PROBE, head), Align.RIGHT
        )

        bottom = max(self._draw_story(surface, ctx), self._draw_specs(surface, ctx))
        limit = self._colors_label_baseline() - TEXT_TO_COLORS if self.product.colors else CONTENT_BOTTOM
        if bottom > limit:
            raise LayoutError(
                f"Il prodotto «{self.product.name}» non entra nella pagina: accorciare la descrizione."
            )
        if self.product.colors:
            self._draw_colors(surface, ctx)

    def _photo_slots(self, page_width: float) -> list[Box]:
        """Full-bleed slots for the variants, laid out by how many there are.

        1: the whole photo area; 2: stacked; 3: a hero on top and two side by
        side below; 4: a 2 x 2 grid. Slots are separated by a paper hairline.
        """
        gap, bottom = PHOTO_GAP, self.photos_bottom
        half = (page_width - gap) / 2
        match len(self.product.variants):
            case 1:
                return [Box(0, 0, page_width, bottom)]
            case 2:
                height = (bottom - gap) / 2
                return [Box(0, 0, page_width, height), Box(0, height + gap, page_width, height)]
            case 3:
                hero = round(bottom * HERO_ROW_SHARE)
                low = hero + gap
                return [
                    Box(0, 0, page_width, hero),
                    Box(0, low, half, bottom - low),
                    Box(half + gap, low, half, bottom - low),
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
        style = label_on(ctx, closeup.image, CORNER_PROBE)
        surface.text(closeup.label, slot.x + LABEL_INSET, slot.bottom - LABEL_INSET, style)

    @staticmethod
    def _draw_variant(
        surface: Surface, ctx: RenderContext, variant: Variant, slot: Box, *, single: bool
    ) -> None:
        """Photo plus colour name: on the floor (bottom-left) of a single large photo, where
        the running head leaves room; on the wall (top-left) in a grid, where small photos
        often have the shoe near their bottom edge."""
        g = ctx.theme.grid
        if variant.image is None:
            draw_placeholder(surface, ctx, slot)
        else:
            surface.image(ctx.images.filled(variant.image, slot.width, slot.height), slot)
        label_x = max(slot.x + LABEL_INSET, g.margin_x)
        if single:
            baseline, probe = slot.bottom - LABEL_INSET, CORNER_PROBE
        else:
            baseline = max(slot.top + LABEL_INSET + LABEL_CAP, RUNNING_HEAD_BASELINE + HEADER_CLEARANCE)
            probe = TOP_CORNER_PROBE
        surface.text(variant.color, label_x, baseline, label_on(ctx, variant.image, probe))

    def _draw_story(self, surface: Surface, ctx: RenderContext) -> float:
        """Model, short name and description; returns the last baseline."""
        p, t, x = ctx.theme.palette, ctx.theme.type, ctx.theme.grid.margin_x
        top = self.photos_bottom
        surface.text(self.model_name, x, top + EYEBROW_OFFSET, t.label.with_color(p.accent))
        name = short_name(self.product.name, self.model_name)
        style = t.product_name
        if name != self.product.name:  # a material variant of the model: set in italics
            style = replace(style, font=Font.DISPLAY_ITALIC)
        title = fit_to_width(name, style, SPECS_X - TITLE_GAP - x)
        surface.text(name, x - 2, top + TITLE_OFFSET, title)
        return surface.paragraph(self.product.description, x, top + TEXT_OFFSET, TEXT_WIDTH, t.text)

    def _draw_specs(self, surface: Surface, ctx: RenderContext) -> float:
        """Spec table on the right of the text band; returns the last baseline."""
        g = ctx.theme.grid
        rows = [(spec.label, spec.value) for spec in self.product.specs]
        if self.product.sizes:
            rows.append(("Taglie", self.product.sizes))
        if self.product.colors:
            rows.append(("Colori", str(len(self.product.colors))))
        baseline = self.photos_bottom + SPECS_OFFSET
        return draw_spec_table(surface, ctx, rows, SPECS_X, g.width - g.margin_x, baseline)

    def _colors_label_baseline(self) -> float:
        card = FEW if len(self.product.colors) <= FEW_COLORS else MANY
        return self.photos_bottom + card["label"]

    def _draw_colors(self, surface: Surface, ctx: RenderContext) -> None:
        """The colour card, sized by the number of colours; the pictured one is underlined."""
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        colors = self.product.colors
        few = len(colors) <= FEW_COLORS
        card, gap = (FEW, FEW_GAP) if few else (MANY, MANY_GAP)
        columns = max(3, len(colors)) if few else COLOR_COLUMNS
        label = "Colori" if few else f"{len(colors)} colori"
        baseline = self._colors_label_baseline()
        surface.text(label, g.margin_x, baseline, t.label)
        width = g.column_width(columns, gap)
        pictured = self.product.master.color.casefold()
        name_style = t.small if few else t.swatch_name
        for index, swatch in enumerate(colors):
            row, column = divmod(index, columns)
            top = baseline + SWATCH_TOP_OFFSET + row * card["pitch"]
            box = Box(g.column_x(column, columns, gap), top, width, card["height"])
            self._draw_swatch(surface, ctx, swatch, box)
            is_master = swatch.name.casefold() == pictured
            if is_master:
                surface.hline(box.x, box.right, box.bottom + MASTER_RULE_DROP, p.ink, MASTER_RULE)
            style = name_style.with_color(p.ink if is_master else p.muted)
            surface.text(swatch.name, box.x, box.bottom + card["name"], style)

    @staticmethod
    def _draw_swatch(surface: Surface, ctx: RenderContext, swatch: Swatch, box: Box) -> None:
        if swatch.image is None:
            surface.rect(box, fill=ctx.theme.palette.studio)
        else:
            surface.image(ctx.images.cropped(swatch.image, box.width, box.height), box)
