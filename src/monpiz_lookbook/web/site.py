"""Build of the digital edition: one static HTML page plus images, fonts and icons.

The site is generated from the same content as the printed lookbook and
needs no server: the ``site/`` folder can be published as it is (GitHub
Pages, any static host). Images are rendered incrementally, so a rebuild
after a text edit takes a couple of seconds.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from PIL import Image

from ..content import load_lookbook
from ..images import ImageLibrary, whitened
from ..models import Lookbook
from ..pages.model import SWATCH_GAP, SWATCH_HEIGHT
from ..pages.product import short_name
from ..pages.section import models_label
from ..theme import default_theme
from .book import book_pages
from .fonts import build_fonts
from .media import Picture, WebImages
from .text import phone_href
from .view import (
    RIDGE_DEPTH_WIDE,
    anchors,
    contact,
    contents,
    retailers_map,
    ridge_clip,
    ridge_path,
    store_id,
)

HERE = Path(__file__).resolve().parent
SHARE_SIZE = (1200, 630)  # Open Graph preview
ICON_SIZES = {"apple-touch-icon.png": 180, "icon-192.png": 192, "favicon-32.png": 32}
SMALL = (240, 480)  # swatches and materials
MEDIUM = (480, 800, 1200)
COVER_MARGIN = 0.06  # photo kept around the boots on the cover


@dataclass(frozen=True, slots=True)
class SiteOptions:
    content_file: Path
    assets_dir: Path
    output_dir: Path


@dataclass(frozen=True, slots=True)
class SiteResult:
    output_dir: Path
    pages: int  # pages of the digital edition
    images: int
    size_bytes: int


def build_site(options: SiteOptions) -> SiteResult:
    lookbook = load_lookbook(options.content_file, options.assets_dir)
    out = options.output_dir
    out.mkdir(parents=True, exist_ok=True)
    images = WebImages(options.assets_dir, out)

    static = _publish_static(out)
    html = render(lookbook, images, options.assets_dir, out, static)
    partial = out / ".index.html.partial"  # never serve a half-written page
    partial.write_text(html, encoding="utf-8")
    partial.replace(out / "index.html")
    (out / ".nojekyll").write_text("")  # GitHub Pages: publish the files as they are
    if lookbook.web.url:
        host = lookbook.web.url.split("://", 1)[-1].strip("/")
        (out / "CNAME").write_text(host + "\n")
    images.prune()

    size = sum(p.stat().st_size for p in out.rglob("*") if p.is_file())
    pages = len(book_pages(lookbook, anchors(lookbook)))
    return SiteResult(out, pages, len(images.written), size)


def render(lookbook: Lookbook, images: WebImages, assets_dir: Path, out: Path, static: dict[str, str]) -> str:
    env = Environment(
        loader=FileSystemLoader(HERE / "templates"),
        autoescape=select_autoescape(["j2", "html"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    ids = anchors(lookbook)
    palette = default_theme().palette
    colors = {
        name.replace("_", "-"): "#" + getattr(palette, name).hexval()[2:]
        for name in palette.__dataclass_fields__
    }
    pages = book_pages(lookbook, ids)
    template = env.get_template("index.html.j2")
    return template.render(
        lb=lookbook,
        ids=ids,
        pages=pages,
        static=static,
        total=len(pages),
        menu=contents(lookbook, ids),
        map=retailers_map(lookbook.retailers) if lookbook.retailers else None,
        colors=colors,
        fonts=build_fonts(assets_dir, out),
        ridge_clip=ridge_clip(),
        ridge_path=ridge_path(),
        ridge_clip_wide=ridge_clip(RIDGE_DEPTH_WIDE),
        ridge_path_wide=ridge_path(RIDGE_DEPTH_WIDE),
        logo=images.picture(lookbook.identity.logo, widths=(280, 560)),
        boots=_cover_boots(lookbook, images, assets_dir),
        share=_share_image(lookbook, assets_dir, out),
        icons=_icons(lookbook, assets_dir, out),
        year=date.today().year,
        pic=images.picture,
        SMALL=SMALL,
        MEDIUM=MEDIUM,
        material_ratio=material_ratio,
        short_name=short_name,
        models_label=models_label,
        contact=contact,
        phone_href=phone_href,
        store_id=store_id,
    )


def material_ratio(count: int) -> float:
    """Width / height of a material swatch on the printed model page with ``count`` materials.

    The web uses the same proportions, so the detail photos cropped for print
    (seams, rubber toe caps, soles) show exactly the same thing online.
    """
    grid = default_theme().grid
    return grid.column_width(count, SWATCH_GAP) / SWATCH_HEIGHT


def _publish_static(out: Path) -> dict[str, str]:
    """Copy CSS and JavaScript; return their URLs with a hash of the content (``site.css?v=3f2a91c0``).

    The query changes with the content, so browsers fetch a stylesheet or script
    as soon as it changes. The file name stays the same: a page still cached from
    an earlier build finds its files instead of a 404.
    """
    urls = {}
    for source in sorted((HERE / "static").iterdir()):
        data = source.read_bytes()
        (out / source.name).write_bytes(data)
        urls[source.name] = f"{source.name}?v={hashlib.sha1(data).hexdigest()[:8]}"
        for old in out.glob(f"{source.stem}.*{source.suffix}"):  # versioned names of earlier builds
            old.unlink()
    return urls


def _cover_boots(lookbook: Lookbook, images: WebImages, assets_dir: Path) -> Picture:
    """The cover shot cut to the boots plus a margin, its backdrop turned white for multiply blending."""
    left, top, right, bottom = ImageLibrary(assets_dir, dpi=72).subject_bounds(lookbook.cover.photo)
    m = COVER_MARGIN
    region = (max(0.0, left - m), max(0.0, top - m), min(1.0, right + m), min(1.0, bottom + m))

    def prepare(image: Image.Image) -> Image.Image:
        box = (
            round(region[0] * image.width),
            round(region[1] * image.height),
            round(region[2] * image.width),
            round(region[3] * image.height),
        )
        return whitened(image.crop(box))

    return images.picture(lookbook.cover.photo, widths=MEDIUM, prepare=(f"boots{region}", prepare))


def _share_image(lookbook: Lookbook, assets_dir: Path, out: Path) -> str:
    """Preview shown when the link is shared (Instagram, WhatsApp): a 1200 x 630 JPEG."""
    source = lookbook.web.share_image or lookbook.cover.banner or lookbook.cover.photo
    with Image.open(assets_dir / source) as opened:
        image = opened.convert("RGB")
    ratio = SHARE_SIZE[0] / SHARE_SIZE[1]
    if image.width / image.height > ratio:
        width = round(image.height * ratio)
        image = image.crop(((image.width - width) // 2, 0, (image.width + width) // 2, image.height))
    else:
        height = round(image.width / ratio)
        image = image.crop((0, (image.height - height) // 2, image.width, (image.height + height) // 2))
    image.resize(SHARE_SIZE, Image.Resampling.LANCZOS).save(out / "share.jpg", quality=86, optimize=True)
    base = (lookbook.web.url or "").rstrip("/")
    return f"{base}/share.jpg" if base else "share.jpg"


def _icons(lookbook: Lookbook, assets_dir: Path, out: Path) -> dict[str, str]:
    """Home-screen and browser icons: the logo on the paper colour."""
    paper = "#" + default_theme().palette.paper.hexval()[2:]
    with Image.open(assets_dir / lookbook.identity.logo) as opened:
        logo = opened.convert("RGBA")
    for name, size in ICON_SIZES.items():
        icon = Image.new("RGBA", (size, size), paper)
        width = round(size * 0.84)
        height = round(logo.height * width / logo.width)
        mark = logo.resize((width, height), Image.Resampling.LANCZOS)
        icon.alpha_composite(mark, ((size - width) // 2, (size - height) // 2))
        icon.convert("RGB").save(out / name, optimize=True)
    return {name: name for name in ICON_SIZES}
