"""Model opener: introduces a shoe model (Cortina, Falcade) before its products.

An atmosphere photo across the top, then the model name in large type and
two columns: the description on the left, a short spec table on the right.
The materials close the page as a strip of equal, numbered swatches.
Missing photos get the studio-grey placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box
from ..models import ShoeModel
from ..surface import Align, Surface
from .base import (
    RUNNING_HEAD_BASELINE,
    RenderContext,
    draw_placeholder,
    draw_spec_table,
    fit_to_width,
    label_on,
)

HERO_BOTTOM = 470.0
LEFT_PROBE = (0.0, 0.0, 0.35, 0.12)  # top-left corner of the photo, under the running head
RIGHT_PROBE = (0.65, 0.0, 1.0, 0.12)

NAME_BASELINE = HERO_BOTTOM + 84.0
NAME_INDENT = -3.0  # optical alignment of the large capital
TEXT_BASELINE = HERO_BOTTOM + 120.0
COLUMN_GAP = 24.0

MATERIALS_LABEL = "Materiali"
MATERIALS_BASELINE = HERO_BOTTOM + 222.0
SWATCH_GAP = 12.0
SWATCH_TOP_OFFSET = 12.0  # label baseline -> swatches
SWATCH_HEIGHT = 62.0
SWATCH_NAME_OFFSET = 18.0  # swatch bottom -> number and name baseline
NUMBER_TO_NAME = 18.0
TEXT_TO_MATERIALS = 22.0  # minimum gap between the text and the materials label


@dataclass(frozen=True, slots=True)
class ModelPage:
    section_name: str
    model: ShoeModel
    number: int  # 1-based position of the model within its section

    @property
    def folio(self) -> str:
        return self.model.name

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        surface.fill_page(p.paper, g.width)

        hero = Box(0, 0, g.width, HERO_BOTTOM)
        if self.model.image is None:
            draw_placeholder(surface, ctx, hero)
        else:
            surface.image(ctx.images.filled(self.model.image, hero.width, hero.height), hero)
        x, right = g.margin_x, g.width - g.margin_x
        style = ctx.theme.type.running_head
        left_style = label_on(ctx, self.model.image, LEFT_PROBE, style)
        surface.text(self.section_name, x, RUNNING_HEAD_BASELINE, left_style)
        head = f"Il modello — {self.number:02d}"
        right_style = label_on(ctx, self.model.image, RIGHT_PROBE, style)
        surface.text(head, right, RUNNING_HEAD_BASELINE, right_style, Align.RIGHT)

        title = fit_to_width(self.model.name, t.model_title, g.content_width - NAME_INDENT)
        surface.text(self.model.name, x + NAME_INDENT, NAME_BASELINE, title)
        column = (g.content_width - COLUMN_GAP) / 2
        text_end = surface.paragraph(self.model.description, x, TEXT_BASELINE, column, t.text)
        rows = [(spec.label, spec.value) for spec in self.model.specs]
        specs_end = draw_spec_table(surface, ctx, rows, x + column + COLUMN_GAP, right, TEXT_BASELINE)
        if self.model.materials and max(text_end, specs_end) > MATERIALS_BASELINE - TEXT_TO_MATERIALS:
            raise LayoutError(f"La descrizione del modello «{self.model.name}» è troppo lunga: accorciarla.")
        self._draw_materials(surface, ctx)

    def _draw_materials(self, surface: Surface, ctx: RenderContext) -> None:
        materials = self.model.materials
        if not materials:
            return
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        surface.text(MATERIALS_LABEL, g.margin_x, MATERIALS_BASELINE, t.label)
        width = g.column_width(len(materials), SWATCH_GAP)
        top = MATERIALS_BASELINE + SWATCH_TOP_OFFSET
        for column, material in enumerate(materials):
            swatch = Box(g.column_x(column, len(materials), SWATCH_GAP), top, width, SWATCH_HEIGHT)
            if material.image is None:
                surface.rect(swatch, fill=p.studio)
            else:
                surface.image(ctx.images.cropped(material.image, swatch.width, swatch.height), swatch)
            baseline = swatch.bottom + SWATCH_NAME_OFFSET
            surface.text(f"{column + 1:02d}", swatch.x, baseline, t.number)
            surface.text(material.name, swatch.x + NUMBER_TO_NAME, baseline, t.small.with_color(p.ink))
