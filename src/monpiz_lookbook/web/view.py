"""What the templates need beyond the content itself.

Anchors for every section, model and product, the contents menu, the
retailers map projected to SVG coordinates and the cover's mountain edge:
plain data computed in Python, so the templates only lay it out.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from ..models import Lookbook, Retailers, RetailersMap, Store
from ..mountain import BOX_WIDTH, SKYLINE, place
from .text import phone_href, slugify, unique_slugs

# --- anchors and contents -------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Entry:
    title: str
    anchor: str
    children: list[Entry] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Anchors:
    sections: dict[int, str]  # section index -> id
    models: dict[tuple[int, int], str]  # (section, model) -> id
    products: dict[tuple[int, int, int], str]  # (section, model, product) -> id


def anchors(lookbook: Lookbook) -> Anchors:
    make = unique_slugs()
    for reserved in ("top", "marchio", "indice", "rivenditori", "contatti"):
        make(reserved)
    sections, models, products = {}, {}, {}
    for s, section in enumerate(lookbook.sections):
        sections[s] = make(section.name)
        for m, model in enumerate(section.models):
            models[s, m] = make(f"{section.name} {model.name}")
            for p, product in enumerate(model.products):
                products[s, m, p] = make(f"{section.name} {product.name}")
    return Anchors(sections, models, products)


def contents(lookbook: Lookbook, ids: Anchors) -> list[Entry]:
    entries = [Entry(lookbook.brand.eyebrow, "marchio")]
    for s, section in enumerate(lookbook.sections):
        children = [Entry(model.name, ids.models[s, m]) for m, model in enumerate(section.models)]
        entries.append(Entry(section.name, ids.sections[s], children))
    if lookbook.retailers is not None:
        entries.append(Entry(lookbook.retailers.eyebrow, "rivenditori"))
    return entries


# --- cover --------------------------------------------------------------------------------------

RIDGE_DEPTH = 0.26  # share of the banner height taken by the mountain edge (phone)
RIDGE_DEPTH_WIDE = 0.55  # on a computer the banner is wider than tall: deeper peaks keep the same profile


def ridge_points(depth: float = RIDGE_DEPTH) -> list[tuple[float, float]]:
    """The skyline in a 100 x 100 box: x across the banner, the peaks in its lowest band."""
    high = min(y for _, y in SKYLINE)
    low = max(y for _, y in SKYLINE)
    return [(x / BOX_WIDTH * 100, 100 - depth * 100 * (low - y) / (low - high)) for x, y in SKYLINE]


def ridge_clip(depth: float = RIDGE_DEPTH) -> str:
    """CSS ``clip-path`` of the cover banner: its lower edge follows the mountains."""
    points = ridge_points(depth)
    edge = ", ".join(f"{x:.2f}% {y:.2f}%" for x, y in reversed(points))
    return f"polygon(0 0, 100% 0, {edge})"


def ridge_path(depth: float = RIDGE_DEPTH) -> str:
    """SVG path of the same edge, in the 100 x 100 viewBox of the ridge line."""
    points = ridge_points(depth)
    return "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in points)


# --- retailers map ------------------------------------------------------------------------------

MAP_WIDTH = 600.0
MAP_HEIGHT = MAP_WIDTH * 304 / 511  # proportions of the printed map
SKY_BAND = 46.0  # room above the map for the mountain line
CITY_OFFSET = (7.0, 4.0)
CLUSTER = 30.0  # map units: closer stores share one point
DOT_RADIUS = 6.0
GROUP_RADIUS = 11.0
CHAR_WIDTH = 8.6  # average width of a city name character at the map's label size
LABEL_HEIGHT = 16.0
CITY_REACH = 24.0  # a city name is shown only with a store point this close


@dataclass(frozen=True, slots=True)
class Dot:
    """A point of the map: one store, or several stores too close to tell apart."""

    x: float
    y: float
    stores: list[Store]


@dataclass(frozen=True, slots=True)
class Label:
    x: float
    y: float
    text: str
    anchor: str = "start"  # SVG text-anchor


@dataclass(frozen=True, slots=True)
class MapView:
    width: float
    height: float
    skyline: str
    dots: list[Dot]
    cities: list[Label]
    outside: list[str]  # regions with stores outside the drawn area


def _inside(area: RetailersMap, store: Store) -> bool:
    if store.at is None:
        return False
    lat, lon = store.at
    return area.south <= lat <= area.north and area.west <= lon <= area.east


def retailers_map(retailers: Retailers) -> MapView | None:
    area = retailers.map

    def point(at: tuple[float, float]) -> tuple[float, float]:
        lat, lon = at
        return (
            (lon - area.west) / (area.east - area.west) * MAP_WIDTH,
            SKY_BAND + (area.north - lat) / (area.north - area.south) * MAP_HEIGHT,
        )

    singles: list[Dot] = []
    outside: list[str] = []
    for region in retailers.regions:
        placed = [Dot(*point(s.at), [s]) for s in region.stores if s.at is not None and _inside(area, s)]
        if len(placed) < len(region.stores):
            outside.append(region.region)
        if not placed:
            continue
        singles.extend(placed)
    if not singles:
        return None
    dots = _clusters(singles)
    # Only the names of places with a store nearby: a name alone reads as a missing store.
    cities: list[Label] = []
    taken: list[Box] = [_dot_box(d) for d in dots]
    for c in area.labels:
        x, y = point(c.at)
        if any(math.dist((x, y), (d.x, d.y)) <= CITY_REACH for d in dots):
            label = _place_city(c.name, x, y, taken)
            if label is not None:
                cities.append(label)
    sky = place(SKYLINE, -8.0, 4.0, (MAP_WIDTH + 16) / BOX_WIDTH, 0.09)
    skyline = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in sky)
    return MapView(MAP_WIDTH, SKY_BAND + MAP_HEIGHT + 30, skyline, dots, cities, outside)


def _clusters(dots: list[Dot]) -> list[Dot]:
    """Merge points closer than ``CLUSTER`` into one, placed at their centre (shown with a count)."""
    groups: list[list[Dot]] = []
    for dot in dots:
        for group in groups:
            cx = sum(d.x for d in group) / len(group)
            cy = sum(d.y for d in group) / len(group)
            if math.dist((dot.x, dot.y), (cx, cy)) < CLUSTER:
                group.append(dot)
                break
        else:
            groups.append([dot])
    return [
        Dot(
            sum(d.x for d in group) / len(group),
            sum(d.y for d in group) / len(group),
            [store for d in group for store in d.stores],
        )
        for group in groups
    ]


Box = tuple[float, float, float, float]  # left, top, right, bottom in map units


def _dot_box(dot: Dot) -> Box:
    r = DOT_RADIUS if len(dot.stores) == 1 else GROUP_RADIUS
    return (dot.x - r, dot.y - r, dot.x + r, dot.y + r)


def _place_city(name: str, x: float, y: float, taken: list[Box]) -> Label | None:
    """The first free spot around the point (right, left, above, below), or None when all overlap."""
    width, height = len(name) * CHAR_WIDTH, LABEL_HEIGHT
    gap = CITY_OFFSET[0]
    half = height / 2
    w2 = width / 2
    spots = [
        (Label(x + gap, y + height / 3, name), (x + gap, y - half, x + gap + width, y + half)),
        (Label(x - gap, y + height / 3, name, "end"), (x - gap - width, y - half, x - gap, y + half)),
        (Label(x, y - gap - 2, name, "middle"), (x - w2, y - gap - height, x + w2, y - gap)),
        (Label(x, y + gap + height, name, "middle"), (x - w2, y + gap, x + w2, y + gap + height)),
    ]
    for label, box in spots:
        inside = box[0] >= 0 and box[2] <= MAP_WIDTH
        if inside and not any(_overlap(box, other) for other in taken):
            taken.append(box)
            return label
    return None


def _overlap(a: Box, b: Box) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


# --- contacts -----------------------------------------------------------------------------------

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)
_PHONE = re.compile(r"^\+?[\d\s]{6,}$")
_WEB = re.compile(r"^(https?://)?[\w-]+(\.[\w-]+)+(/\S*)?$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Contact:
    text: str
    href: str | None


def contact(text: str) -> Contact:
    """A contact line made clickable: e-mail, phone number or web address."""
    if _EMAIL.match(text):
        return Contact(text, f"mailto:{text}")
    if _PHONE.match(text):
        return Contact(text, phone_href(text))
    if _WEB.match(text):
        return Contact(text, text if text.startswith("http") else f"https://{text}")
    return Contact(text, None)


def store_id(store: Store) -> str:
    return "negozio-" + slugify(store.name)
