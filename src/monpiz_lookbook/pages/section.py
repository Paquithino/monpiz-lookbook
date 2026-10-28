"""Section opener (Donna, Uomo).

With a photo: the photo fills the page, darkened towards the bottom, and the
section name sits on it in very large type, with the intro and the model
count below. Without a photo: the same composition on the dark forest green.
The block is laid out bottom-up, so a longer intro pushes the name upwards.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box
from ..models import Section
from ..surface import Align, Surface
from .base import RUNNING_HEAD_BASELINE, RenderContext

PHOTO_SHADE = 0.72  # darkness reached at the bottom edge
PHOTO_SHADE_START = 0.35  # fraction of the height where the darkening begins
INTRO_BASELINE = 762.0  # first line of the intro
INTRO_WIDTH = 300.0
RULE_ABOVE_INTRO = 24.0  # intro first baseline -> rule
RULE_LENGTH = 40.0
NAME_ABOVE_RULE = 38.0  # rule -> name baseline
NAME_INDENT = -8.0  # optical: the big capital's side bearing
MIN_NAME_BASELINE = 260.0


def models_label(count: int) -> str:
    return f"{count:02d} {'modello' if count == 1 else 'modelli'}"


@dataclass(frozen=True, slots=True)
class SectionPage:
    section: Section
    number: int  # 1-based position among the sections
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        x, right = g.margin_x, g.width - g.margin_x
        if self.section.photo is None:
            surface.fill_page(p.forest, g.width)
        else:
            image = ctx.images.shaded(
                self.section.photo, g.width, g.height, strength=PHOTO_SHADE, start=PHOTO_SHADE_START
            )
            surface.image(image, Box(0, 0, g.width, g.height))

        light = t.running_head.with_color(p.on_dark)
        surface.text(f"{self.number:02d}", x, RUNNING_HEAD_BASELINE, light)
        surface.text(self.section.eyebrow, right, RUNNING_HEAD_BASELINE, light, Align.RIGHT)

        intro_style = t.text.with_color(p.on_dark_muted)
        lines = surface.lines(self.section.intro, intro_style, INTRO_WIDTH) if self.section.intro else []
        rule_top = INTRO_BASELINE - RULE_ABOVE_INTRO
        name_baseline = rule_top - NAME_ABOVE_RULE
        if name_baseline < MIN_NAME_BASELINE or len(lines) > 3:
            raise LayoutError(f"Il testo della sezione «{self.section.name}» è troppo lungo.")
        surface.text(self.section.name, x + NAME_INDENT, name_baseline, t.display_xl)
        surface.hline(x, x + RULE_LENGTH, rule_top, p.on_dark, 0.8)
        if lines:
            surface.paragraph(self.section.intro, x, INTRO_BASELINE, INTRO_WIDTH, intro_style)
        surface.text(models_label(len(self.section.models)), right, INTRO_BASELINE, light, Align.RIGHT)
