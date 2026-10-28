from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PIL import Image

from monpiz_lookbook.models import Region, Retailers, RetailersMap, Store
from monpiz_lookbook.web import SiteOptions, build_site
from monpiz_lookbook.web.text import phone_href, slugify, unique_slugs
from monpiz_lookbook.web.view import contact, retailers_map, ridge_points

FONTS = Path(__file__).parents[1] / "assets" / "fonts"


def test_slugify_makes_ascii_anchors() -> None:
    assert slugify("Grostè Uomo") == "groste-uomo"
    assert slugify("Lui & Lei Abbigliamento") == "lui-lei-abbigliamento"


def test_unique_slugs_number_repeated_names() -> None:
    make = unique_slugs()
    names = [make("Falcade Cavallino"), make("Falcade Cavallino")]
    assert names == ["falcade-cavallino", "falcade-cavallino-2"]


@pytest.mark.parametrize(
    ("text", "href"),
    [
        ("monpiz@monpiz.it", "mailto:monpiz@monpiz.it"),
        ("+39 335 760 4522", "tel:+393357604522"),
        ("monpiz.it", "https://monpiz.it"),
        ("instagram.com/monpiz_", "https://instagram.com/monpiz_"),
        ("Montebelluna", None),
    ],
)
def test_contacts_become_links(text: str, href: str | None) -> None:
    assert contact(text).href == href


def test_landline_numbers_get_the_italian_prefix() -> None:
    assert phone_href("0436 3320") == "tel:+3904363320"


def test_the_cover_ridge_stays_in_the_lower_band_of_the_banner() -> None:
    points = ridge_points()
    assert points[0][0] == 0 and points[-1][0] == 100
    assert all(70 <= y <= 100 for _, y in points)


def test_the_map_places_only_the_stores_inside_its_area() -> None:
    retailers = Retailers(
        eyebrow="Dove trovarci",
        title="Rivenditori",
        map=RetailersMap(),
        regions=[
            Region(region="Veneto", stores=[Store(name="A", address="Belluno", at=(46.14, 12.22))]),
            Region(region="Lazio", stores=[Store(name="B", address="Roma", at=(41.9, 12.5))]),
        ],
    )
    view = retailers_map(retailers)
    assert view is not None
    assert [d.store.name for d in view.dots] == ["A"]
    assert view.outside == ["Lazio"]


# --- the whole site, from a small lookbook ---------------------------------------------------------


def _photo(path: Path, size: tuple[int, int] = (900, 600), color: str = "#c8c6c0") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


@pytest.fixture
def lookbook(tmp_path: Path) -> SiteOptions:
    assets = tmp_path / "assets"
    shutil.copytree(FONTS, assets / "fonts")
    for name in ("banner", "boots", "heritage", "detail", "section", "model", "variant", "swatch"):
        _photo(assets / "images" / f"{name}.jpg")
    logo = Image.new("RGBA", (560, 240), (0, 0, 0, 0))
    logo.save(assets / "images" / "logo.png")
    Image.new("L", (150, 66), 0).save(assets / "images" / "logo-mask.png")
    content = tmp_path / "content"
    content.mkdir()
    (content / "retailers.yaml").write_text(
        '- region: Veneto\n  stores:\n    - {name: "Negozio", address: "Via Roma 1, 32043 Cortina BL", '
        'at: [46.54, 12.14], shop: "https://example.com/monpiz", phone: "0436 3320"}\n'
    )
    (content / "lookbook.yaml").write_text(
        """
meta: {title: Lookbook di prova, author: MonPiz}
identity: {logo: images/logo.png, logo_mask: images/logo-mask.png}
cover: {tagline: Pedule, claim: Una storia italiana., photo: images/boots.jpg, banner: images/banner.jpg}
brand:
  eyebrow: Il marchio
  title: Tra tradizione e innovazione
  folio: MonPiz
  paragraphs: [Testo.]
  banner: {path: images/heritage.jpg}
  details_title: Dettagli
  details: [{name: Suola, description: Vibram, image: images/detail.jpg}]
sections:
  - name: Donna
    photo: images/section.jpg
    models:
      - name: Cortina
        description: La pedula classica.
        image: images/model.jpg
        products:
          - name: Cortina Suede
            description: Suede morbido.
            sizes: 35-42
            variants: [{color: Aneto, image: images/variant.jpg}]
            colors: [{name: Aneto, image: images/swatch.jpg}, {name: Palm}]
retailers: {eyebrow: Dove trovarci, title: Rivenditori, source: retailers.yaml}
closing: {title: "Sei pronto?", text: Scopri MonPiz., contacts: [[monpiz@monpiz.it]]}
web: {url: "https://lookbook.monpiz.it"}
"""
    )
    return SiteOptions(content / "lookbook.yaml", assets, tmp_path / "site")


def test_the_site_is_built_from_the_content(lookbook: SiteOptions) -> None:
    result = build_site(lookbook)
    html = (result.output_dir / "index.html").read_text()
    assert 'id="donna-cortina"' in html
    assert 'id="donna-cortina-suede"' in html
    assert 'href="https://example.com/monpiz"' in html  # the store name opens its online shop
    assert 'href="tel:+3904363320"' in html
    assert 'href="mailto:monpiz@monpiz.it"' in html
    assert 'content="https://lookbook.monpiz.it/share.jpg"' in html
    assert (result.output_dir / "CNAME").read_text().strip() == "lookbook.monpiz.it"
    for name in ("site.css", "site.js", "share.jpg", "apple-touch-icon.png", ".nojekyll"):
        assert (result.output_dir / name).is_file()


def test_a_rebuild_reuses_the_images_and_drops_the_unused_ones(lookbook: SiteOptions) -> None:
    build_site(lookbook)
    images = lookbook.output_dir / "img"
    stale = images / "old-photo-0000000000-480.webp"
    stale.write_bytes(b"")
    before = {p.name: p.stat().st_mtime_ns for p in images.glob("*.webp") if p != stale}
    build_site(lookbook)
    after = {p.name: p.stat().st_mtime_ns for p in images.glob("*.webp")}
    assert after == before


def test_full_spreads_always_start_on_a_left_hand_page(lookbook: SiteOptions) -> None:
    from monpiz_lookbook.content import load_lookbook
    from monpiz_lookbook.web.book import book_pages
    from monpiz_lookbook.web.view import anchors

    lb = load_lookbook(lookbook.content_file, lookbook.assets_dir)
    pages = book_pages(lb, anchors(lb))
    position = 0  # 0: left-hand page, 1: right-hand page
    for page in pages:
        if page.span == 2:
            assert position == 0 and page.spread_start
            continue
        assert page.spread_start == (position == 0)
        position = 1 - position
    assert position == 0  # the book ends with a complete spread
    real = [p.number for p in pages if not p.filler]
    assert real == list(range(1, len(real) + 1))
