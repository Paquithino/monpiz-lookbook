"""Retailers pages: authorised stores by region, as cards flowing in newspaper columns.

Each region opens with a ruled header (name, store count); its stores follow
as cards with address, phone and two clickable buttons: the map and, when
the store has one, its online shop. Regions run down the first column, then
the next one, then onto the next page, so small regions fill the gaps left
by big ones and the list stays compact.

The layout is computed up front by ``paginate``, from text measurements
only, so the builder knows how many pages there are before drawing any of
them. A region header is never left alone at the bottom of a column: it
moves on with its first card. A region that breaks across columns repeats
its header, marked as continued.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box, wrap_text
from ..models import Region, Retailers, Store
from ..surface import Surface, text_width
from ..theme import TextStyle, Theme
from .base import EYEBROW_BASELINE, HEADING_BASELINE, RenderContext, draw_header

INTRO_WIDTH = 440.0
INTRO_OFFSET = 26.0  # heading baseline -> intro first baseline
CONTENT_OFFSET = 26.0  # intro last baseline -> first region header
CONTINUED_TOP = 74.0  # content top on the pages after the first
CONTENT_BOTTOM = 776.0

COLUMNS = 3
COLUMN_GAP = 14.0
CARD_GAP = 6.0
REGION_HEIGHT = 41.0  # ruled header with name and count; cards start below it
REGION_NAME_OFFSET = 19.0  # rule -> region name baseline
REGION_COUNT_OFFSET = 31.0  # rule -> count baseline
REGION_GAP = 10.0  # after the last card of a region
CONTINUED_LABEL = "segue"

CARD_PAD_TOP = 8.0
CARD_PAD_BOTTOM = 8.0
CARD_PAD_LEFT = 13.0
CARD_PAD_RIGHT = 9.0
CARD_BORDER = 2.5
NAME_TO_TEXT = 3.0
TEXT_TO_BUTTONS = 6.0
BUTTON_HEIGHT = 14.0
BUTTON_PAD_X = 8.0
BUTTON_GAP = 5.0
BUTTON_BASELINE = 9.6  # from the top of the button
MAP_LABEL = "Mappa"
SHOP_LABEL = "Negozio online"


@dataclass(frozen=True, slots=True)
class RegionHeader:
    region: Region
    box: Box
    continued: bool


@dataclass(frozen=True, slots=True)
class Card:
    store: Store
    box: Box


Block = RegionHeader | Card


@dataclass(frozen=True, slots=True)
class RetailersPage:
    retailers: Retailers
    blocks: tuple[Block, ...]
    first: bool
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        surface.fill_page(p.paper, g.width)
        if self.first:
            heading_end = draw_header(surface, ctx, self.retailers.eyebrow, self.retailers.title)
            if self.retailers.intro:
                baseline = heading_end + INTRO_OFFSET
                surface.paragraph(self.retailers.intro, g.margin_x, baseline, INTRO_WIDTH, t.body)
        else:
            surface.text(self.retailers.eyebrow, g.margin_x, EYEBROW_BASELINE, t.eyebrow)

        for block in self.blocks:
            if isinstance(block, RegionHeader):
                _draw_region_header(surface, ctx, block)
            else:
                _draw_card(surface, ctx, block)


def retailer_pages(retailers: Retailers, theme: Theme, folio: str | None = None) -> list[RetailersPage]:
    """The retailers section, split into pages."""
    pages = paginate(retailers, theme)
    return [RetailersPage(retailers, tuple(blocks), index == 0, folio) for index, blocks in enumerate(pages)]


def paginate(retailers: Retailers, theme: Theme) -> list[list[Block]]:
    """Place headers and cards down the columns, moving to the next column or page when one is full."""
    g = theme.grid
    width = _column_width(theme)
    first_top = _first_content_top(retailers, theme)
    pages: list[list[Block]] = [[]]
    column = 0
    top = first_top
    column_is_empty = True

    def next_column() -> None:
        nonlocal column, top, column_is_empty
        column += 1
        if column == COLUMNS:
            pages.append([])
            column = 0
        top = first_top if len(pages) == 1 else CONTINUED_TOP
        column_is_empty = True

    for region in retailers.regions:
        for index, store in enumerate(region.stores):
            height = _card_height(store, theme, width)
            opens_region = index == 0
            # The header travels with the card below it, so it is never orphaned.
            needed = height + (REGION_HEIGHT if opens_region else 0.0)
            if top + needed > CONTENT_BOTTOM:
                if column_is_empty:
                    raise LayoutError(f"Il negozio «{store.name}» non entra in una colonna.")
                next_column()
            x = g.column_x(column, COLUMNS, COLUMN_GAP)
            if opens_region or column_is_empty:
                header = Box(x, top, width, REGION_HEIGHT)
                pages[-1].append(RegionHeader(region, header, continued=not opens_region))
                top += REGION_HEIGHT
            pages[-1].append(Card(store, Box(x, top, width, height)))
            top += height + CARD_GAP
            column_is_empty = False
        top += REGION_GAP
    return pages


def store_count_label(count: int) -> str:
    return "1 negozio" if count == 1 else f"{count} negozi"


# -- measurement ----------------------------------------------------------------


def _wrap(text: str, style: TextStyle, width: float) -> list[str]:
    return wrap_text(text, lambda s: text_width(s, style), width)


def _first_content_top(retailers: Retailers, theme: Theme) -> float:
    t, g = theme.type, theme.grid
    heading_lines = _wrap(retailers.title, t.heading, g.content_width)
    end = HEADING_BASELINE + (len(heading_lines) - 1) * t.heading.leading
    if retailers.intro:
        intro_lines = _wrap(retailers.intro, t.body, INTRO_WIDTH)
        end += INTRO_OFFSET + (len(intro_lines) - 1) * t.body.leading
    return end + CONTENT_OFFSET


def _column_width(theme: Theme) -> float:
    return theme.grid.column_width(COLUMNS, COLUMN_GAP)


def _text_width(card_width: float) -> float:
    return card_width - CARD_PAD_LEFT - CARD_PAD_RIGHT


def _text_lines(store: Store, theme: Theme, card_width: float) -> tuple[list[str], list[str]]:
    """Wrapped lines of the name and of the details (address, then phone)."""
    t, width = theme.type, _text_width(card_width)
    details = _wrap(store.address, t.store_text, width)
    if store.phone:
        details.append(f"Tel. {store.phone}")
    return _wrap(store.name, t.store_name, width), details


def _card_height(store: Store, theme: Theme, card_width: float) -> float:
    t = theme.type
    name, details = _text_lines(store, theme, card_width)
    return (
        CARD_PAD_TOP
        + len(name) * t.store_name.leading
        + NAME_TO_TEXT
        + len(details) * t.store_text.leading
        + TEXT_TO_BUTTONS
        + BUTTON_HEIGHT
        + CARD_PAD_BOTTOM
    )


# -- drawing --------------------------------------------------------------------


def _draw_region_header(surface: Surface, ctx: RenderContext, header: RegionHeader) -> None:
    p, t = ctx.theme.palette, ctx.theme.type
    box = header.box
    surface.hline(box.x, box.right, box.top, p.rule)
    surface.text(header.region.region, box.x, box.top + REGION_NAME_OFFSET, t.region)
    count = store_count_label(len(header.region.stores))
    if header.continued:
        count = f"{count} · {CONTINUED_LABEL}"
    surface.text(count, box.x, box.top + REGION_COUNT_OFFSET, t.region_count)


def _draw_card(surface: Surface, ctx: RenderContext, card: Card) -> None:
    p, t = ctx.theme.palette, ctx.theme.type
    box, store = card.box, card.store
    surface.rect(box, fill=p.card)
    surface.rect(Box(box.x, box.top, CARD_BORDER, box.height), fill=p.accent)

    x = box.x + CARD_PAD_LEFT
    name, details = _text_lines(store, ctx.theme, box.width)
    top = box.top + CARD_PAD_TOP
    top = _draw_lines(surface, name, x, top, t.store_name)
    top = _draw_lines(surface, details, x, top + NAME_TO_TEXT, t.store_text)

    buttons = [(MAP_LABEL, store.maps_url, False)]
    if store.shop:
        buttons.append((SHOP_LABEL, store.shop, True))
    _draw_buttons(surface, ctx, buttons, x, top + TEXT_TO_BUTTONS)


def _draw_lines(surface: Surface, lines: Sequence[str], x: float, top: float, style: TextStyle) -> float:
    """Draw ``lines`` in a block starting at ``top``; returns the bottom of the block."""
    # Baseline sits about three quarters down the line: matches the type's ascent.
    offset = style.leading * 0.78
    for index, line in enumerate(lines):
        surface.text(line, x, top + offset + index * style.leading, style)
    return top + len(lines) * style.leading


def _draw_buttons(
    surface: Surface, ctx: RenderContext, buttons: Sequence[tuple[str, str, bool]], x: float, top: float
) -> None:
    """Pill buttons, outlined or filled, each a link to its URL."""
    p, style = ctx.theme.palette, ctx.theme.type.store_button
    radius = BUTTON_HEIGHT / 2
    for label, url, filled in buttons:
        pill = Box(x, top, text_width(label, style) + 2 * BUTTON_PAD_X, BUTTON_HEIGHT)
        if filled:
            surface.rect(pill, fill=p.button, radius=radius)
            label_style = style.with_color(p.card)
        else:
            surface.rect(pill, stroke=p.rule, stroke_width=0.8, radius=radius)
            label_style = style
        surface.text(label, pill.x + BUTTON_PAD_X, top + BUTTON_BASELINE, label_style)
        surface.link(url, pill)
        x = pill.right + BUTTON_GAP
