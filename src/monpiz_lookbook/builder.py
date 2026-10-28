"""Assembles the pages and renders the PDF.

The PDF is made for print: every page is the trimmed A4 plus a bleed on each
side (declared as TrimBox and BleedBox, so print software and the printer's
preflight read the trim correctly), with optional crop marks in a slug
around it. Saddle-stitched magazines need a page count multiple of four:
``BuildResult.blank_pages_needed`` says how many pages are missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from reportlab.pdfgen.canvas import Canvas

from . import __version__
from .content import load_lookbook
from .fonts import register_fonts
from .geometry import Box
from .images import ImageLibrary
from .models import Index, Lookbook
from .pages import (
    BrandPage,
    ClosingPage,
    CoverPage,
    FeaturePage,
    IndexEntry,
    IndexPage,
    ModelPage,
    Page,
    ProductPage,
    RenderContext,
    RetailersPage,
    SectionPage,
    retailer_pages,
)
from .pages.base import draw_logo
from .surface import Surface
from .theme import Font, Theme, default_theme

FOOTER_LABEL_OFFSET = 22.0  # page number -> section label
FOOTER_LOGO_WIDTH = 40.0
FOOTER_LOGO_DROP = 3.0  # the script letters sit slightly below the folio baseline
SLUG = 24.0  # room outside the bleed for the crop marks
MARK_LENGTH = 14.0
MARK_GAP = 3.0  # crop marks stop short of the bleed
MARK_WIDTH = 0.3
SIGNATURE = 4  # saddle stitching: pages come in sheets of four


@dataclass(frozen=True, slots=True)
class BuildOptions:
    content_file: Path
    assets_dir: Path
    output: Path
    dpi: int = 300
    bleed: bool = True
    crop_marks: bool = False


@dataclass(frozen=True, slots=True)
class BuildResult:
    output: Path
    pages: int
    size_bytes: int

    @property
    def blank_pages_needed(self) -> int:
        """Pages to add for a saddle-stitched print (a multiple of four)."""
        return -self.pages % SIGNATURE


def compose(lookbook: Lookbook, theme: Theme) -> list[Page]:
    """Cover, brand, contents, each section (opener, then per model: model page,
    optional feature page, one page per product), retailers and the back cover."""
    pages: list[Page] = [CoverPage(lookbook.cover), BrandPage(lookbook.brand)]
    index_at = len(pages)
    for number, section in enumerate(lookbook.sections, start=1):
        pages.append(SectionPage(section, number))
        total = len(section.products)
        position = 0
        for model_number, model in enumerate(section.models, start=1):
            pages.append(ModelPage(section.name, model, model_number))
            if model.feature is not None:
                pages.append(FeaturePage(model.feature, folio=model.name))
            for product in model.products:
                position += 1
                pages.append(ProductPage(section.name, model.name, product, position, total))
    if lookbook.retailers is not None:
        pages.extend(retailer_pages(lookbook.retailers, theme, folio=lookbook.retailers.eyebrow))
    if lookbook.closing is not None:
        pages.append(ClosingPage(lookbook.closing))

    index = lookbook.index or Index()
    # The contents page shifts everything after it by one: number accordingly.
    entries = _index_entries(pages, inserted_at=index_at)
    pages.insert(index_at, IndexPage(index, entries))
    return pages


def _index_entries(pages: list[Page], *, inserted_at: int) -> tuple[IndexEntry, ...]:
    """Sections with their models, and the retailers, with final 1-based page numbers.

    ``pages`` does not contain the contents page yet: it will be inserted at
    ``inserted_at``, pushing every later page one number further.
    """
    entries: list[IndexEntry] = []
    children: list[tuple[str, int]] = []
    section: tuple[str, int] | None = None

    def number(position: int) -> int:
        return position + (2 if position >= inserted_at else 1)

    for position, page in enumerate(pages):
        if isinstance(page, SectionPage):
            if section is not None:
                entries.append(IndexEntry(section[0], section[1], tuple(children)))
            section, children = (page.section.name, number(position)), []
        elif isinstance(page, ModelPage):
            children.append((page.model.name, number(position)))
        elif isinstance(page, RetailersPage) and page.first:
            if section is not None:
                entries.append(IndexEntry(section[0], section[1], tuple(children)))
                section = None
            entries.append(IndexEntry(page.retailers.eyebrow, number(position)))
    if section is not None:
        entries.append(IndexEntry(section[0], section[1], tuple(children)))
    return tuple(entries)


def _draw_footer(surface: Surface, ctx: RenderContext, page: Page, number: int) -> None:
    """Page number and section on the left, small logo on the right, on one baseline.

    Only pages with a folio get it: cover, contents, openers and back cover
    stand on their own. On a full-bleed feature page the footer turns light.
    """
    p, t, g = ctx.theme.palette, ctx.theme.type, ctx.theme.grid
    light = isinstance(page, FeaturePage)
    label = t.label.with_color(p.on_dark if light else p.faint)
    numeral = t.number.with_color(p.on_dark) if light else t.number
    surface.text(f"{number:02d}", g.margin_x, g.folio_baseline, numeral)
    surface.text(page.folio or "", g.margin_x + FOOTER_LABEL_OFFSET, g.folio_baseline, label)
    width = FOOTER_LOGO_WIDTH
    px_w, px_h = ctx.images.size(ctx.logo)
    height = width * px_h / px_w
    top = g.folio_baseline + FOOTER_LOGO_DROP - height
    x = g.width - g.margin_x - width
    if light:
        draw_logo(surface, ctx, x, top, width, p.on_dark)
    else:
        surface.image(ctx.images.fitted(ctx.logo, width, height), Box(x, top, width, height))


def _draw_crop_marks(canvas: Canvas, trim: tuple[float, float, float, float], bleed: float) -> None:
    """Hairline marks at the four corners of the trim, outside the bleed."""
    x0, y0, x1, y1 = trim
    start, end = bleed + MARK_GAP, bleed + MARK_GAP + MARK_LENGTH
    canvas.saveState()
    canvas.setLineWidth(MARK_WIDTH)
    for x, sx in ((x0, -1), (x1, 1)):
        for y, sy in ((y0, -1), (y1, 1)):
            canvas.line(x + sx * start, y, x + sx * end, y)
            canvas.line(x, y + sy * start, x, y + sy * end)
    canvas.restoreState()


def render(
    lookbook: Lookbook,
    output: Path,
    assets_dir: Path,
    *,
    dpi: int = 300,
    bleed: bool = True,
    crop_marks: bool = False,
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

    g = theme.grid
    bleed_width = g.bleed if bleed else 0.0
    margin = bleed_width + (SLUG if crop_marks else 0.0)  # trim edge -> sheet edge
    trim = (margin, margin, margin + g.width, margin + g.height)
    # One temporary file per process: a build and the watch can run at the same time.
    partial = output.with_name(f".{output.name}.{os.getpid()}.partial")

    canvas = Canvas(
        str(partial),
        pagesize=(g.width + 2 * margin, g.height + 2 * margin),
        invariant=True,
        initialFontName=Font.SANS.value,  # avoids a stray, non-embedded Helvetica
        trimBox=trim,
        bleedBox=(trim[0] - bleed_width, trim[1] - bleed_width, trim[2] + bleed_width, trim[3] + bleed_width),
    )
    canvas.setTitle(lookbook.meta.title)
    canvas.setAuthor(lookbook.meta.author)
    canvas.setSubject(lookbook.meta.subject)
    canvas.setCreator(f"monpiz-lookbook {__version__}")

    try:
        for number, page in enumerate(pages, start=1):
            canvas.saveState()
            canvas.translate(margin, margin)
            surface = Surface(canvas, g.height, page_width=g.width, bleed=bleed_width)
            page.draw(surface, ctx)
            if page.folio:
                _draw_footer(surface, ctx, page, number)
            canvas.restoreState()
            if crop_marks:
                _draw_crop_marks(canvas, trim, bleed_width)
            canvas.showPage()
        canvas.save()
        partial.replace(output)
    finally:
        partial.unlink(missing_ok=True)
    return len(pages)


def build(options: BuildOptions) -> BuildResult:
    lookbook = load_lookbook(options.content_file, options.assets_dir)
    pages = render(
        lookbook,
        options.output,
        options.assets_dir,
        dpi=options.dpi,
        bleed=options.bleed,
        crop_marks=options.crop_marks,
    )
    return BuildResult(options.output, pages, options.output.stat().st_size)
