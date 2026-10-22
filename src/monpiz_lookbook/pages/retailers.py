"""Retailers page: authorised stores by region, followed by the closing contacts.

Regions keep their content order and are distributed over three columns so
that the tallest column is as short as possible.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import balance_columns
from ..models import Closing, Region, Retailers
from ..surface import Surface
from .base import RenderContext, draw_header, draw_logo, logo_height

INTRO_WIDTH = 440.0
INTRO_OFFSET = 23.6  # heading baseline -> intro first baseline
COLUMNS = 3
COLUMNS_OFFSET = 38.4  # intro last baseline -> first region baseline
REGION_TO_STORE = 19.9
REGION_GAP = 30.0  # last store baseline -> next region baseline

RULE_TOP = 671.5
MIN_GAP_ABOVE_RULE = 24.0
CLOSING_TITLE_BASELINE = 711.0
CLOSING_TEXT_OFFSET = 24.5
CLOSING_TEXT_WIDTH = 205.0
CONTACTS_OFFSET = 25.8
CONTACT_SEPARATOR = " · "
LOGO_WIDTH = 54.0
LOGO_BOTTOM = 788.0


@dataclass(frozen=True, slots=True)
class RetailersPage:
    retailers: Retailers
    closing: Closing
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        surface.fill_page(p.olive, g.width)
        heading_end = draw_header(
            surface,
            ctx,
            self.retailers.eyebrow,
            self.retailers.title,
            eyebrow_color=p.on_dark_accent,
            title_color=p.on_dark,
        )
        intro_end = heading_end
        if self.retailers.intro:
            intro_end = surface.paragraph(
                self.retailers.intro,
                g.margin_x,
                heading_end + INTRO_OFFSET,
                INTRO_WIDTH,
                t.lead,
            )
        bottom = self._draw_regions(surface, ctx, intro_end + COLUMNS_OFFSET)
        if bottom > RULE_TOP - MIN_GAP_ABOVE_RULE:
            raise LayoutError("L'elenco dei rivenditori non entra nella pagina.")
        self._draw_closing(surface, ctx)

    def _region_lines(self, surface: Surface, ctx: RenderContext, region: Region) -> list[str]:
        style, width = ctx.theme.type.store, ctx.theme.grid.column_width(COLUMNS)
        return [line for store in region.stores for line in surface.lines(store.label, style, width)]

    def _draw_regions(self, surface: Surface, ctx: RenderContext, top_baseline: float) -> float:
        """Draw the region columns; returns the lowest baseline used."""
        t, g = ctx.theme.type, ctx.theme.grid
        regions = self.retailers.regions
        lines = [self._region_lines(surface, ctx, region) for region in regions]
        spans = [REGION_TO_STORE + (len(block) - 1) * t.store.leading + REGION_GAP for block in lines]

        bottom = top_baseline
        for column, indices in enumerate(balance_columns(spans, COLUMNS)):
            x = g.column_x(column, COLUMNS)
            baseline = top_baseline
            for index in indices:
                surface.text(regions[index].region, x, baseline, t.region)
                store_baseline = baseline + REGION_TO_STORE
                for line in lines[index]:
                    surface.text(line, x, store_baseline, t.store)
                    bottom = max(bottom, store_baseline)
                    store_baseline += t.store.leading
                baseline += spans[index]
        return bottom

    def _draw_closing(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        x = g.margin_x
        surface.hline(x, g.width - g.margin_x, RULE_TOP, p.olive_rule)
        surface.text(self.closing.title, x, CLOSING_TITLE_BASELINE, t.closing_title)

        end = surface.paragraph(
            self.closing.text,
            x,
            CLOSING_TITLE_BASELINE + CLOSING_TEXT_OFFSET,
            CLOSING_TEXT_WIDTH,
            t.lead,
        )
        baseline = end + CONTACTS_OFFSET
        for row in self.closing.contacts:
            surface.text(CONTACT_SEPARATOR.join(row), x, baseline, t.contact)
            baseline += t.contact.leading

        logo_x = g.width - g.margin_x - LOGO_WIDTH
        logo_top = LOGO_BOTTOM - logo_height(ctx, LOGO_WIDTH)
        draw_logo(surface, ctx, logo_x, logo_top, LOGO_WIDTH, p.on_dark)
