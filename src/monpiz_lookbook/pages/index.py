"""Contents page: the sections and their models with page numbers.

The entries are computed by the builder from the pages it composed, so the
numbers are always right. An optional photo takes a tall column on the right.
Rows tighten when the list is long, down to a minimum pitch.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box
from ..models import Index
from ..surface import Align, Surface
from .base import RenderContext

PHOTO_WIDTH = 232.0
PHOTO_GAP = 34.0  # list -> photo
EYEBROW_BASELINE = 74.0
EYEBROW = "Collezione"
TITLE_BASELINE = 150.0
LIST_TOP = 214.0
LIST_BOTTOM = 790.0
HEAD_RULE_DROP = 10.0  # section name baseline -> its rule
HEAD_TO_FIRST = 22.0  # section rule -> first entry baseline
ENTRY_RULE_DROP = 8.0
ENTRY_PITCH = 25.0
MIN_ENTRY_PITCH = 18.0
SECTION_GAP = 26.0


@dataclass(frozen=True, slots=True)
class IndexEntry:
    title: str
    page: int
    children: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class IndexPage:
    index: Index
    entries: tuple[IndexEntry, ...]
    eyebrow: str = EYEBROW
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        surface.fill_page(p.paper, g.width)
        right = g.width - g.margin_x
        if self.index.photo is not None:
            photo = Box(g.width - PHOTO_WIDTH, 0, PHOTO_WIDTH, g.height)
            surface.image(ctx.images.cropped(self.index.photo, photo.width, photo.height), photo)
            right = photo.x - PHOTO_GAP

        x = g.margin_x
        surface.text(self.eyebrow, x, EYEBROW_BASELINE, t.label.with_color(p.faint))
        surface.text(self.index.title, x, TITLE_BASELINE, t.model_title)

        pitch = self._entry_pitch()
        y = LIST_TOP
        for entry in self.entries:
            surface.text(entry.title, x, y, t.index_section)
            surface.text(f"{entry.page:02d}", right, y, t.number, Align.RIGHT)
            y += HEAD_RULE_DROP
            surface.hline(x, right, y, p.ink, 0.6)
            if not entry.children:
                y += SECTION_GAP
                continue
            y += HEAD_TO_FIRST
            for name, page in entry.children:
                surface.text(name, x, y, t.index_entry)
                surface.text(f"{page:02d}", right, y, t.small, Align.RIGHT)
                surface.hline(x, right, y + ENTRY_RULE_DROP, p.rule, 0.4)
                y += pitch
            y += SECTION_GAP

    def _entry_pitch(self) -> float:
        fixed = sum(HEAD_RULE_DROP + SECTION_GAP + (HEAD_TO_FIRST if e.children else 0) for e in self.entries)
        rows = sum(len(e.children) for e in self.entries)
        if not rows:
            return ENTRY_PITCH
        pitch = min(ENTRY_PITCH, (LIST_BOTTOM - LIST_TOP - fixed) / rows)
        if pitch < MIN_ENTRY_PITCH:
            raise LayoutError("L'indice non entra in una pagina: troppi modelli.")
        return pitch
