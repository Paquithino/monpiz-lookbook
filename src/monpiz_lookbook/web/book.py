"""The digital edition as a book: the sequence of pages and how they pair into spreads.

Every page fills the screen and the reader turns them one by one. On a phone
(or any portrait screen) one page is shown at a time; on a landscape screen two
pages sit side by side like an open magazine, and some pages (the cover, the
section openers) take the whole spread.

Pairing is decided here, not in the browser: when a full spread would start on
the right-hand page, a blank "filler" page closes the previous spread, as in
a printed magazine. Fillers exist only for wide screens and are hidden on
phones.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..models import Lookbook, Region, Store
from .view import Anchors

STORES_PER_PAGE = 8  # retailer list: rows that fit a phone screen with the page header


@dataclass(slots=True)
class Page:
    kind: str  # template macro that draws the page
    id: str  # anchor, for links and the contents
    title: str  # shown in the page overview
    section: str  # running head
    thumb: Path | None = None  # photo of the page overview
    span: int = 1  # 2: takes a whole spread on wide screens
    data: dict[str, Any] = field(default_factory=dict)
    number: int = 0  # 1-based, counting only real pages
    spread_start: bool = False  # first page of a spread on wide screens
    filler: bool = False


@dataclass(frozen=True, slots=True)
class RegionChunk:
    """Part of a region's stores on one page; ``continued`` when the region began on an earlier one."""

    region: Region
    stores: list[Store]
    continued: bool


def book_pages(lookbook: Lookbook, ids: Anchors) -> list[Page]:
    pages = list(_sequence(lookbook, ids))
    for number, page in enumerate(pages, start=1):
        page.number = number
    return _pair(pages)


def _sequence(lb: Lookbook, ids: Anchors) -> Iterator[Page]:
    brand = lb.brand
    yield Page("cover", "top", "Copertina", "", thumb=lb.cover.banner or lb.cover.photo, span=2)
    yield Page("brand", "marchio", brand.eyebrow, brand.eyebrow)
    yield Page("details", "dettagli", brand.details_title, brand.eyebrow, thumb=brand.banner.path)
    yield Page("contents", "indice", lb.index.title if lb.index else "Indice", "Indice")
    if lb.index and lb.index.photo:
        yield Page("photo", "indice-foto", "", "", thumb=lb.index.photo, data={"photo": lb.index.photo})

    for s, section in enumerate(lb.sections):
        yield Page(
            "opener",
            ids.sections[s],
            section.name,
            section.name,
            thumb=section.photo,
            span=2,
            data={"section": section, "number": s + 1},
        )
        for m, model in enumerate(section.models):
            yield Page(
                "model",
                ids.models[s, m],
                model.name,
                section.name,
                thumb=model.image,
                data={"model": model, "index": m + 1, "count": len(section.models), "section": section},
            )
            if model.feature is not None:
                yield Page(
                    "feature",
                    f"{ids.models[s, m]}-dettaglio",
                    model.feature.title,
                    section.name,
                    thumb=model.feature.image,
                    data={"feature": model.feature},
                )
            for p, product in enumerate(model.products):
                yield Page(
                    "product",
                    ids.products[s, m, p],
                    product.name,
                    f"{section.name} — {model.name}",
                    thumb=product.master.image,
                    data={"product": product, "model": model},
                )

    if lb.retailers is not None:
        r = lb.retailers
        yield Page("retailers_map", "rivenditori", r.eyebrow, r.eyebrow, data={"retailers": r})
        for n, chunk in enumerate(_chunks(r.regions)):
            yield Page("retailers_list", f"rivenditori-{n + 1}", r.eyebrow, r.eyebrow, data={"chunks": chunk})

    if lb.closing is not None:
        if lb.closing.photo is not None:
            yield Page(
                "photo", "chiusura-foto", "", "", thumb=lb.closing.photo, data={"photo": lb.closing.photo}
            )
        yield Page("closing", "contatti", lb.closing.title, "")


def _chunks(regions: list[Region]) -> Iterator[list[RegionChunk]]:
    """Stores split into pages of ``STORES_PER_PAGE`` rows, regions broken where needed."""
    page: list[RegionChunk] = []
    room = STORES_PER_PAGE
    for region in regions:
        stores, continued = list(region.stores), False
        while stores:
            if room == 0:
                yield page
                page, room = [], STORES_PER_PAGE
            taken, stores = stores[:room], stores[room:]
            page.append(RegionChunk(region, taken, continued))
            room -= len(taken)
            continued = True
    if page:
        yield page


def _pair(pages: list[Page]) -> list[Page]:
    """Insert fillers so that full spreads start on the left, and mark where spreads begin."""
    paired: list[Page] = []
    left_open = False  # a left-hand page waits for its right-hand neighbour
    for page in pages:
        if page.span == 2:
            if left_open:
                paired.append(_filler(len(paired)))
            page.spread_start, left_open = True, False
        elif left_open:
            left_open = False
        else:
            page.spread_start, left_open = True, True
        paired.append(page)
    if left_open:
        paired.append(_filler(len(paired)))
    return paired


def _filler(position: int) -> Page:
    return Page("filler", f"vuota-{position}", "", "", filler=True)
