from __future__ import annotations

from pathlib import Path

import pytest

from monpiz_lookbook.fonts import register_fonts
from monpiz_lookbook.models import Region, Retailers, Store
from monpiz_lookbook.pages.retailers import CONTENT_BOTTOM, Card, RegionHeader, paginate, store_count_label
from monpiz_lookbook.theme import default_theme

FONTS = Path(__file__).parents[1] / "assets" / "fonts"


@pytest.fixture(autouse=True, scope="module")
def fonts() -> None:
    register_fonts(FONTS)  # pagination measures text with the real fonts


def _retailers(*counts: int) -> Retailers:
    regions = [
        Region(
            region=f"Regione {r}",
            stores=[
                Store(name=f"Negozio {r}.{s}", address="Via Roma, 1, 31044 Montebelluna TV") for s in range(n)
            ],
        )
        for r, n in enumerate(counts)
    ]
    return Retailers(eyebrow="Dove trovarci", title="Dove trovare MonPiz", regions=regions)


def test_every_store_is_placed_once_and_inside_the_page() -> None:
    pages = paginate(_retailers(10, 11, 9, 3, 1, 1, 1), default_theme())
    cards = [block for page in pages for block in page if isinstance(block, Card)]
    assert len(cards) == 36
    assert all(card.box.bottom <= CONTENT_BOTTOM for card in cards)


def test_a_header_is_always_followed_by_a_card_of_its_region() -> None:
    for page in paginate(_retailers(10, 11, 9, 3, 1, 1, 1), default_theme()):
        for block, after in zip(page, [*page[1:], None], strict=True):
            if isinstance(block, RegionHeader):
                assert isinstance(after, Card)
                assert after.store in block.region.stores
                assert after.box.x == block.box.x


def test_a_region_broken_over_columns_repeats_its_header_as_continued() -> None:
    pages = paginate(_retailers(30), default_theme())
    headers = [block for page in pages for block in page if isinstance(block, RegionHeader)]
    assert len(headers) > 1
    assert not headers[0].continued
    assert all(header.continued for header in headers[1:])


def test_store_count_label_is_singular_for_one_store() -> None:
    assert store_count_label(1) == "1 negozio"
    assert store_count_label(4) == "4 negozi"


def test_maps_url_encodes_name_and_address() -> None:
    store = Store(name="Lui & Lei", address="Borgata Bach 22, Sappada")
    assert store.maps_url.endswith("query=Lui%20%26%20Lei%20Borgata%20Bach%2022%2C%20Sappada")
