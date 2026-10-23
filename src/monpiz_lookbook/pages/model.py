"""Model page: introduces a shoe model (Cortina, Falcade) before its products.

A full-bleed hero photo on top, then the model name, its description and a
row of material swatches (one close-up per material) anchored to the bottom.
Missing photos get the studio-grey placeholder.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box
from ..models import ShoeModel
from ..surface import Surface
from .base import EYEBROW_BASELINE, RenderContext, draw_placeholder

HERO_BOTTOM = 400.0
HERO_LABEL = "Il modello"

EYEBROW_TOP_BASELINE = 442.0
NAME_BASELINE = 500.0
DESCRIPTION_OFFSET = 32.0  # name baseline -> description
DESCRIPTION_WIDTH = 380.0

MATERIALS_LABEL = "Materiali"
MATERIALS_BASELINE = 606.0
SWATCH_TOP = 622.0
SWATCH_HEIGHT = 110.0
SWATCH_NAME_OFFSET = 20.0  # swatch bottom -> material name baseline
TEXT_TO_MATERIALS = 26.0  # minimum gap above the materials label


@dataclass(frozen=True, slots=True)
class ModelPage:
    section_name: str
    model: ShoeModel

    @property
    def folio(self) -> str:
        return self.section_name

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        surface.fill_page(p.paper, g.width)

        hero = Box(0, 0, g.width, HERO_BOTTOM)
        if self.model.image is None:
            draw_placeholder(surface, ctx, hero)
        else:
            surface.image(ctx.images.bled(self.model.image, hero.width, hero.height), hero)
        surface.text(self.section_name, g.margin_x, EYEBROW_BASELINE, t.photo_label)

        x = g.margin_x
        surface.text(HERO_LABEL, x, EYEBROW_TOP_BASELINE, t.eyebrow)
        surface.text(self.model.name, x, NAME_BASELINE, t.model_title)
        text_end = surface.paragraph(
            self.model.description, x, NAME_BASELINE + DESCRIPTION_OFFSET, DESCRIPTION_WIDTH, t.body
        )
        if self.model.materials and text_end > MATERIALS_BASELINE - TEXT_TO_MATERIALS:
            raise LayoutError(f"La descrizione del modello «{self.model.name}» è troppo lunga: accorciarla.")
        self._draw_materials(surface, ctx)

    def _draw_materials(self, surface: Surface, ctx: RenderContext) -> None:
        materials = self.model.materials
        if not materials:
            return
        t, g = ctx.theme.type, ctx.theme.grid
        surface.text(MATERIALS_LABEL, g.margin_x, MATERIALS_BASELINE, t.eyebrow)
        columns = len(materials)
        width = g.column_width(columns)
        for column, material in enumerate(materials):
            swatch = Box(g.column_x(column, columns), SWATCH_TOP, width, SWATCH_HEIGHT)
            if material.image is None:
                draw_placeholder(surface, ctx, swatch)
            else:
                image = ctx.images.cropped(material.image, swatch.width, swatch.height)
                surface.image(image, swatch)
            surface.text(material.name, swatch.x, swatch.bottom + SWATCH_NAME_OFFSET, t.detail_title)
