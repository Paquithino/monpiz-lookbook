"""Assembles the pages and renders the PDF."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas

from . import __version__
from .content import load_lookbook
from .fonts import register_fonts
from .geometry import Box
from .images import ImageLibrary
from .models import Lookbook
from .pages import (
    BrandPage,
    ClosingPage,
    CoverPage,
    ModelPage,
    Page,
    ProductPage,
    RenderContext,
    SectionPage,
    retailer_pages,
)
from .surface import Surface
from .theme import Font, Theme, default_theme

FOLIO_SEPARATOR = " · "
FOOTER_LOGO_WIDTH = 40.0
FOOTER_LOGO_DROP = 3.0  # the script letters sit slightly below the folio baseline


@dataclass(frozen=True, slots=True)
class BuildOptions:
    content_file: Path
    assets_dir: Path
    output: Path
    dpi: int = 300


@dataclass(frozen=True, slots=True)
class BuildResult:
    output: Path
    pages: int
    size_bytes: int


def compose(lookbook: Lookbook, theme: Theme) -> list[Page]:
    """Cover, brand, each section (divider, then per model: intro + one page per product),
    retailers (as many pages as needed) and the back cover."""
    pages: list[Page] = [CoverPage(lookbook.cover), BrandPage(lookbook.brand)]
    for section in lookbook.sections:
        pages.append(SectionPage(section))
        total = len(section.products)
        index = 0
        for model in section.models:
            pages.append(ModelPage(section.name, model))
            for product in model.products:
                index += 1
                pages.append(ProductPage(section.name, model.name, product, index, total))
    if lookbook.retailers is not None:
        pages.extend(retailer_pages(lookbook.retailers, theme, folio=lookbook.brand.folio))
    if lookbook.closing is not None:
        pages.append(ClosingPage(lookbook.closing))
    return pages


def _draw_footer(surface: Surface, ctx: RenderContext, label: str, number: int) -> None:
    """Folio on the left, small logo on the right, on the same baseline.

    Only pages with a folio get it: cover, dividers and back cover already
    show the logo large.
    """
    g = ctx.theme.grid
    surface.text(f"{label}{FOLIO_SEPARATOR}{number:02d}", g.margin_x, g.folio_baseline, ctx.theme.type.folio)
    width = FOOTER_LOGO_WIDTH
    px_w, px_h = ctx.images.size(ctx.logo)
    height = width * px_h / px_w
    logo = Box(g.width - g.margin_x - width, g.folio_baseline + FOOTER_LOGO_DROP - height, width, height)
    surface.image(ctx.images.fitted(ctx.logo, width, height), logo)


def render(
    lookbook: Lookbook,
    output: Path,
    assets_dir: Path,
    *,
    dpi: int = 300,
    theme: Theme | None = None,
) -> int:
    """Render ``lookbook`` to ``output``; returns the number of pages.

    The PDF is written to a temporary file and moved into place only when
    rendering succeeds, so a failed build never leaves a truncated file.
    The output is byte-for-byte reproducible (``invariant`` mode), which
    keeps diffs and CI artifacts meaningful.
    """
    theme = theme or default_theme()
    register_fonts(assets_dir / "fonts")
    identity = lookbook.identity
    ctx = RenderContext(theme, ImageLibrary(assets_dir, dpi), identity.logo, identity.logo_mask)
    pages = compose(lookbook, theme)

    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(f".{output.name}.partial")
    canvas = Canvas(
        str(partial),
        pagesize=(theme.grid.width, theme.grid.height),
        invariant=True,
        initialFontName=Font.SANS.value,  # avoids a stray, non-embedded Helvetica
    )
    canvas.setTitle(lookbook.meta.title)
    canvas.setAuthor(lookbook.meta.author)
    canvas.setSubject(lookbook.meta.subject)
    canvas.setCreator(f"monpiz-lookbook {__version__}")

    try:
        for number, page in enumerate(pages, start=1):
            surface = Surface(canvas, theme.grid.height)
            page.draw(surface, ctx)
            if page.folio:
                _draw_footer(surface, ctx, page.folio, number)
            canvas.showPage()
        canvas.save()
        partial.replace(output)
    finally:
        partial.unlink(missing_ok=True)
    return len(pages)


def build(options: BuildOptions) -> BuildResult:
    lookbook = load_lookbook(options.content_file, options.assets_dir)
    pages = render(lookbook, options.output, options.assets_dir, dpi=options.dpi)
    return BuildResult(options.output, pages, options.output.stat().st_size)
