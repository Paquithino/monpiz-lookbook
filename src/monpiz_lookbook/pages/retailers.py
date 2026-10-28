"""Retailers pages: a dot map of the stores, then a quiet list in three columns.

The map draws every store that has coordinates (``at``) inside the mapped
area, with the cover's mountain line along its top edge, region names at the
centre of their stores and a few labelled towns. Stores outside the area are
mentioned under the map ("Anche in: Lazio, Estero").

The list gives one line per store, "Name — Town", grouped by region; the name
links to the store on Google Maps for the online edition. ``paginate`` flows
the regions down the columns, then onto a further page if needed; a region
broken across columns repeats its header.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..errors import LayoutError
from ..geometry import Box, wrap_text
from ..models import Retailers, RetailersMap, Store
from ..mountain import BOX_WIDTH, SKYLINE, place
from ..surface import Align, Surface, text_width
from ..theme import Theme
from .base import RenderContext

EYEBROW_BASELINE = 74.0
TITLE_BASELINE = 116.0
INTRO_OFFSET = 22.0  # title baseline -> intro
MAP = Box(42.0, 176.0, 511.0, 304.0)
SKYLINE_LIFT = 30.0  # mountain line above the map's top edge
SKYLINE_FLATTEN = 0.16
DOT_RADIUS = 3.0
CITY_OFFSET = (6.0, 3.0)
OUTSIDE_PREFIX = "Anche in: "

RULE_BELOW_MAP = 18.0
LIST_TOP_BELOW_MAP = 40.0  # map bottom -> first region header
LIST_TOP_NO_MAP = 70.0  # intro (or title) -> first header, when there is no map
CONTINUED_TOP = 110.0  # first header on a continuation page
LIST_BOTTOM = 790.0
COLUMNS = 3
COLUMN_GAP = 20.0
HEAD_TO_FIRST = 18.0
LINE_PITCH = 12.2
REGION_GAP = 16.0
DASH = " — "
CONTINUED = " (segue)"


@dataclass(frozen=True, slots=True)
class Line:
    text: str
    x: float
    baseline: float
    head: bool  # a region header, not a store line
    url: str | None = None


def town_line(store: Store) -> str:
    return f"{store.name}{DASH}{store.town}"


def _column_width(theme: Theme) -> float:
    return theme.grid.column_width(COLUMNS, COLUMN_GAP)


def _store_lines(store: Store, theme: Theme) -> list[str]:
    style = theme.type.store_line
    return wrap_text(town_line(store), lambda s: text_width(s, style), _column_width(theme))


def has_map(retailers: Retailers) -> bool:
    return any(_inside(retailers.map, s) for r in retailers.regions for s in r.stores)


def _inside(area: RetailersMap, store: Store) -> bool:
    if store.at is None:
        return False
    lat, lon = store.at
    return area.south <= lat <= area.north and area.west <= lon <= area.east


def _list_top(retailers: Retailers, theme: Theme) -> float:
    if has_map(retailers):
        return MAP.bottom + LIST_TOP_BELOW_MAP
    top = TITLE_BASELINE
    if retailers.intro:
        style = theme.type.text
        lines = wrap_text(retailers.intro, lambda s: text_width(s, style), theme.grid.content_width)
        top += INTRO_OFFSET + (len(lines) - 1) * style.leading
    return top + LIST_TOP_NO_MAP


def paginate(retailers: Retailers, theme: Theme) -> list[list[Line]]:
    """Place headers and store lines down the columns, then onto further pages."""
    g = theme.grid
    pages: list[list[Line]] = [[]]
    first_top = _list_top(retailers, theme)
    column, y = 0, first_top

    def next_column() -> None:
        nonlocal column, y
        column += 1
        if column == COLUMNS:
            pages.append([])
            column = 0
        y = first_top if len(pages) == 1 else CONTINUED_TOP

    def x() -> float:
        return g.column_x(column, COLUMNS, COLUMN_GAP)

    for region in retailers.regions:
        header_due = True
        for index, store in enumerate(region.stores):
            lines = _store_lines(store, theme)
            needed = len(lines) * LINE_PITCH + (HEAD_TO_FIRST if header_due else 0.0)
            if y + needed > LIST_BOTTOM:
                if y == (first_top if len(pages) == 1 else CONTINUED_TOP):
                    raise LayoutError(f"Il negozio «{store.name}» non entra in una colonna.")
                next_column()
                header_due = True
            if header_due:
                name = region.region + (CONTINUED if index else "")
                pages[-1].append(Line(name, x(), y, head=True))
                y += HEAD_TO_FIRST
                header_due = False
            for number, text in enumerate(lines):
                url = store.maps_url if number == 0 else None
                pages[-1].append(Line(text, x(), y, head=False, url=url))
                y += LINE_PITCH
        y += REGION_GAP
    return pages


@dataclass(frozen=True, slots=True)
class RetailersPage:
    retailers: Retailers
    lines: tuple[Line, ...]
    first: bool
    folio: str | None = None

    def draw(self, surface: Surface, ctx: RenderContext) -> None:
        p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
        surface.fill_page(p.paper, g.width)
        x = g.margin_x
        surface.text(self.retailers.eyebrow, x, EYEBROW_BASELINE, t.label.with_color(p.faint))
        if self.first:
            surface.text(self.retailers.title, x - 1, TITLE_BASELINE, t.heading)
            if has_map(self.retailers):
                self._draw_map(surface, ctx)
            elif self.retailers.intro:
                surface.paragraph(
                    self.retailers.intro, x, TITLE_BASELINE + INTRO_OFFSET, g.content_width, t.text
                )
        for line in self.lines:
            style = t.region if line.head else t.store_line
            width = surface.text(line.text, line.x, line.baseline, style)
            if line.url:
                surface.link(line.url, Box(line.x, line.baseline - style.size, width, style.leading))

    def _draw_map(self, surface: Surface, ctx: RenderContext) -> None:
        p, t = ctx.theme.palette, ctx.theme.type
        area = self.retailers.map

        def point(at: tuple[float, float]) -> tuple[float, float]:
            lat, lon = at
            return (
                MAP.x + (lon - area.west) / (area.east - area.west) * MAP.width,
                MAP.top + (area.north - lat) / (area.north - area.south) * MAP.height,
            )

        scale = MAP.width / BOX_WIDTH * 1.02
        sky = place(SKYLINE, MAP.x - 10, MAP.top - SKYLINE_LIFT, scale, SKYLINE_FLATTEN)
        surface.polyline(sky, p.rule, 0.8)

        outside: list[str] = []
        for region in self.retailers.regions:
            placed = [point(s.at) for s in region.stores if s.at is not None and _inside(area, s)]
            if len(placed) < len(region.stores) and region.region not in outside:
                outside.append(region.region)
            if not placed:
                continue
            cx = sum(px for px, _ in placed) / len(placed)
            cy = sum(py for _, py in placed) / len(placed)
            label = t.label.with_color(p.faint)
            half = text_width(region.region, label) / 2
            lx = min(max(cx - half, MAP.x), MAP.right - 2 * half)
            surface.text(region.region, lx, cy + _label_drop(placed, cy), label)
            for centre in placed:
                surface.dot(centre, DOT_RADIUS, p.accent)
        for city in area.labels:
            cx, cy = point(city.at)
            surface.text(city.name, cx + CITY_OFFSET[0], cy + CITY_OFFSET[1], t.map_city)
        if outside:
            note = OUTSIDE_PREFIX + ", ".join(outside)
            surface.text(note, MAP.right, MAP.bottom - 4, t.small, Align.RIGHT)
        surface.hline(MAP.x, MAP.right, MAP.bottom + RULE_BELOW_MAP, p.ink, 0.6)


def _label_drop(placed: list[tuple[float, float]], centre_y: float) -> float:
    """Region names go just below their lowest store, so they never cover a dot."""
    return max(py for _, py in placed) - centre_y + 18.0


def retailer_pages(retailers: Retailers, theme: Theme, folio: str | None = None) -> list[RetailersPage]:
    """The retailers section, split into pages."""
    pages = paginate(retailers, theme)
    return [RetailersPage(retailers, tuple(lines), index == 0, folio) for index, lines in enumerate(pages)]
