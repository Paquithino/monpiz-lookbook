from __future__ import annotations

from pathlib import Path

import pytest

from monpiz_lookbook.fonts import register_fonts
from monpiz_lookbook.models import Region, Retailers, Store
from monpiz_lookbook.pages.retailers import (
    CONTINUED,
    LIST_BOTTOM,
    Line,
    has_map,
    paginate,
    retailer_pages,
)
from monpiz_lookbook.theme import default_theme

FONTS = Path(__file__).parents[1] / "assets" / "fonts"
DOLOMITES = (46.5, 11.9)


@pytest.fixture(autouse=True, scope="module")
def fonts() -> None:
    register_fonts(FONTS)  # pagination measures text with the real fonts


def _retailers(*counts: int, at: tuple[float, float] | None = DOLOMITES) -> Retailers:
    regions = [
        Region(
            region=f"Regione {r}",
            stores=[
                Store(name=f"Negozio {r}.{s}", address="Via Roma, 1, 31044 Montebelluna TV", at=at)
                for s in range(n)
            ],
        )
        for r, n in enumerate(counts)
    ]
    return Retailers(eyebrow="Dove trovarci", title="Dove trovare MonPiz", regions=regions)


def _store_lines(pages: list[list[Line]]) -> list[Line]:
    return [line for page in pages for line in page if line.url is not None]


def test_every_store_is_listed_once_and_inside_the_page() -> None:
    pages = paginate(_retailers(10, 11, 9, 3, 1, 1, 1), default_theme())
    linked = _store_lines(pages)
    assert len(linked) == 36
    assert len({line.url for line in linked}) == 36
    assert all(line.baseline <= LIST_BOTTOM for page in pages for line in page)


def test_a_long_list_flows_onto_a_further_page() -> None:
    pages = paginate(_retailers(60, 60), default_theme())
    assert len(pages) > 1
    assert len(_store_lines(pages)) == 120


def test_a_region_broken_over_columns_repeats_its_header_as_continued() -> None:
    pages = paginate(_retailers(40), default_theme())
    headers = [line for page in pages for line in page if line.head]
    assert len(headers) > 1
    assert not headers[0].text.endswith(CONTINUED)
    assert all(header.text.endswith(CONTINUED) for header in headers[1:])


def test_a_header_is_never_the_last_line_of_a_column() -> None:
    for page in paginate(_retailers(10, 11, 9, 3, 1, 1, 1), default_theme()):
        for line, after in zip(page, [*page[1:], None], strict=True):
            if line.head:
                assert after is not None and not after.head and after.x == line.x


def test_the_map_is_drawn_only_when_a_store_falls_inside_it() -> None:
    assert has_map(_retailers(2))
    assert not has_map(_retailers(2, at=None))
    assert not has_map(_retailers(2, at=(41.9, 12.5)))  # Roma, outside the north-east


def test_retailer_pages_mark_only_the_first_page() -> None:
    pages = retailer_pages(_retailers(60, 60), default_theme(), folio="Dove trovarci")
    assert [page.first for page in pages] == [True] + [False] * (len(pages) - 1)


@pytest.mark.parametrize(
    ("address", "town"),
    [
        ("Via Roma, 1, 31044 Montebelluna TV", "Montebelluna"),
        ("Corso Italia 12, 32043 Cortina d'Ampezzo BL", "Cortina d'Ampezzo"),
        ("Via Postumia 5, Castrette, TV", "Castrette"),
        ("Borgata Bach 22, Sappada", "Sappada"),
    ],
)
def test_store_town_comes_from_the_address(address: str, town: str) -> None:
    assert Store(name="Negozio", address=address).town == town


def test_maps_url_encodes_name_and_address() -> None:
    store = Store(name="Lui & Lei", address="Borgata Bach 22, Sappada")
    assert store.maps_url.endswith("query=Lui%20%26%20Lei%20Borgata%20Bach%2022%2C%20Sappada")
