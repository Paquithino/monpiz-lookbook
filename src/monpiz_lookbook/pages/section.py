"""Section divider: a full dark page announcing a part of the lookbook (Donna, Uomo).

The title block is laid out bottom-up from the model count, so a longer intro
pushes the title upwards instead of running into the bottom of the page.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..models import Section
from ..surface import Align, Surface
from .base import RenderContext, draw_logo

LOGO_TOP = 52.3
LOGO_WIDTH = 48.0
EYEBROW_BASELINE = 65.7
COUNT_BASELINE = 797.7
INTRO_WIDTH = 330.0
INTRO_TO_COUNT = 52.0  # last intro baseline -> count baseline
TITLE_TO_INTRO = 46.0  # title baseline -> first intro baseline
RULE_ABOVE_TITLE = 104.0  # rule -> title baseline
RULE_LENGTH = 40.0
MIN_RULE_TOP = 200.0


def models_label(count: int) -> str:
    return f"{count:02d} {'modello' if count == 1 else 'modelli'}"


@dataclass(frozen=True, slots=True)
class SectionPage:
    section: Section
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        x, right = g.margin_x, g.width - g.margin_x

        surface.fill_page(p.forest, g.width)
        draw_logo(surface, ctx, x, LOGO_TOP, LOGO_WIDTH, p.on_dark)
        surface.text(self.section.eyebrow, right, EYEBROW_BASELINE, t.cover_label, Align.RIGHT)

        intro_lines = (
            surface.lines(self.section.intro, t.cover_claim, INTRO_WIDTH) if self.section.intro else []
        )
        intro_last = COUNT_BASELINE - INTRO_TO_COUNT
        intro_first = intro_last - (len(intro_lines) - 1) * t.cover_claim.leading
        title_baseline = intro_first - TITLE_TO_INTRO if intro_lines else intro_last
        rule_top = title_baseline - RULE_ABOVE_TITLE
        if rule_top < MIN_RULE_TOP:
            raise LayoutError(f"Il testo della sezione «{self.section.name}» è troppo lungo.")

        surface.hline(x, x + RULE_LENGTH, rule_top, p.cover_accent, width=1.2)
        surface.text(self.section.name, x, title_baseline, t.section_title)
        if intro_lines:
            surface.paragraph(self.section.intro, x, intro_first, INTRO_WIDTH, t.cover_claim)
        surface.text(models_label(len(self.section.models)), x, COUNT_BASELINE, t.cover_label)
