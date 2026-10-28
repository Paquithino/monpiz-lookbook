"""What the templates need beyond the content itself.

Anchors for every section, model and product, the contents menu, the
retailers map projected to SVG coordinates and the cover's mountain edge:
plain data computed in Python, so the templates only lay it out.
"""

from __future__ import annotations

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

RIDGE_DEPTH = 0.26  # share of the banner height taken by the mountain edge


def ridge_points() -> list[tuple[float, float]]:
    """The skyline in a 100 x 100 box: x across the banner, the peaks in its lowest band."""
    high = min(y for _, y in SKYLINE)
    low = max(y for _, y in SKYLINE)
    return [(x / BOX_WIDTH * 100, 100 - RIDGE_DEPTH * 100 * (low - y) / (low - high)) for x, y in SKYLINE]


def ridge_clip() -> str:
    """CSS ``clip-path`` of the cover banner: its lower edge follows the mountains."""
    points = ridge_points()
    edge = ", ".join(f"{x:.2f}% {y:.2f}%" for x, y in reversed(points))
    return f"polygon(0 0, 100% 0, {edge})"


def ridge_path() -> str:
    """SVG path of the same edge, in the 100 x 100 viewBox of the ridge line."""
    points = ridge_points()
    return "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in points)


# --- retailers map ------------------------------------------------------------------------------

MAP_WIDTH = 600.0
MAP_HEIGHT = MAP_WIDTH * 304 / 511  # proportions of the printed map
SKY_BAND = 46.0  # room above the map for the mountain line
CITY_OFFSET = (7.0, 4.0)
REGION_DROP = 20.0
RIGHT_EDGE = 0.85  # share of the map width beyond which a city name goes left of its point


@dataclass(frozen=True, slots=True)
class Dot:
    x: float
    y: float
    store: Store


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
    regions: list[Label]
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

    dots, regions, outside = [], [], []
    for region in retailers.regions:
        placed = [Dot(*point(s.at), s) for s in region.stores if s.at is not None and _inside(area, s)]
        if len(placed) < len(region.stores):
            outside.append(region.region)
        if not placed:
            continue
        dots.extend(placed)
        cx = sum(d.x for d in placed) / len(placed)
        regions.append(Label(cx, max(d.y for d in placed) + REGION_DROP, region.region))
    if not dots:
        return None
    cities = [_city(c.name, *point(c.at)) for c in area.labels]
    sky = place(SKYLINE, -8.0, 4.0, (MAP_WIDTH + 16) / BOX_WIDTH, 0.09)
    skyline = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in sky)
    return MapView(MAP_WIDTH, SKY_BAND + MAP_HEIGHT + 30, skyline, dots, cities, regions, outside)


def _city(name: str, x: float, y: float) -> Label:
    """City names sit right of their point, or left of it near the right edge of the map."""
    if x > MAP_WIDTH * RIGHT_EDGE:
        return Label(x - CITY_OFFSET[0], y + CITY_OFFSET[1], name, "end")
    return Label(x + CITY_OFFSET[0], y + CITY_OFFSET[1], name)


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
