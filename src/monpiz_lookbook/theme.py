"""Design tokens: palette, typography and page grid.

Every visual constant of the lookbook lives here, so the page modules only
describe *where* things go and never hard-code colours or font sizes.
All measurements are in PostScript points (1 pt = 1/72 in).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import A4


class Font(StrEnum):
    """Font names as registered in ReportLab (see :mod:`fonts`)."""

    DISPLAY = "Fraunces-Display"
    DISPLAY_ITALIC = "Fraunces-DisplayItalic"  # material variant of a model (Cortina *Dakar*)
    SERIF = "Fraunces-Text"
    SANS = "Inter-Regular"


@dataclass(frozen=True, slots=True)
class Palette:
    ink: Color
    body: Color
    muted: Color
    faint: Color
    accent: Color
    paper: Color
    rule: Color
    # Dark pages
    forest: Color
    olive: Color
    on_dark: Color
    on_dark_muted: Color
    on_dark_accent: Color
    cover_accent: Color
    cover_highlight: Color
    olive_rule: Color
    studio: Color


@dataclass(frozen=True, slots=True)
class TextStyle:
    font: Font
    size: float
    leading: float
    color: Color
    tracking: float = 0.0
    uppercase: bool = False

    def with_color(self, color: Color) -> TextStyle:
        return replace(self, color=color)

    def scaled(self, factor: float) -> TextStyle:
        return replace(self, size=self.size * factor, leading=self.leading * factor)


@dataclass(frozen=True, slots=True)
class Typography:
    eyebrow: TextStyle
    heading: TextStyle
    body: TextStyle
    detail_title: TextStyle
    detail_text: TextStyle
    folio: TextStyle
    cover_claim: TextStyle
    cover_label: TextStyle
    region: TextStyle
    lead: TextStyle
    contact: TextStyle
    closing_title: TextStyle
    section_title: TextStyle
    product_name: TextStyle
    model_title: TextStyle
    photo_label: TextStyle
    spec_value: TextStyle
    swatch_name: TextStyle
    # Magazine layer: few sizes, strong contrast between them
    running_head: TextStyle  # spaced capitals at the top of the page: model name, page counter
    label: TextStyle  # small spaced capitals: captions, table keys
    number: TextStyle  # olive figures: page numbers, material numbers
    small: TextStyle  # table values, swatch names, store lines
    text: TextStyle  # running text of model and product pages
    display_xl: TextStyle  # section openers
    feature_title: TextStyle  # title over a full-bleed photo
    index_section: TextStyle
    index_entry: TextStyle
    map_city: TextStyle
    store_line: TextStyle


@dataclass(frozen=True, slots=True)
class Grid:
    """Page geometry shared by every page."""

    width: float = A4[0]
    height: float = A4[1]
    margin_x: float = 42.0
    margin_top: float = 36.0
    folio_baseline: float = 810.0
    bleed: float = 8.5  # 3 mm, the printers' standard
    gutter: float = 20.0
    radius: float = 6.0

    @property
    def content_width(self) -> float:
        return self.width - 2 * self.margin_x

    def column_width(self, columns: int, gutter: float | None = None) -> float:
        gap = self.gutter if gutter is None else gutter
        return (self.content_width - (columns - 1) * gap) / columns

    def column_x(self, index: int, columns: int, gutter: float | None = None) -> float:
        gap = self.gutter if gutter is None else gutter
        return self.margin_x + index * (self.column_width(columns, gap) + gap)


@dataclass(frozen=True, slots=True)
class Theme:
    palette: Palette
    type: Typography
    grid: Grid


def default_theme() -> Theme:
    p = Palette(
        ink=HexColor("#24291F"),
        body=HexColor("#4B5245"),
        muted=HexColor("#565B4C"),
        faint=HexColor("#8B8A76"),
        accent=HexColor("#6D6F2E"),
        paper=HexColor("#EFECE2"),
        rule=HexColor("#CFC9B6"),
        forest=HexColor("#24291F"),
        olive=HexColor("#52541F"),
        on_dark=HexColor("#FFFDF8"),
        on_dark_muted=HexColor("#E2E0C6"),
        on_dark_accent=HexColor("#CDD08A"),
        cover_accent=HexColor("#A8AB5C"),
        cover_highlight=HexColor("#C9C6AC"),
        olive_rule=HexColor("#82835B"),
        studio=HexColor("#C9C8C5"),  # photo backdrop, used for placeholders
    )
    t = Typography(
        eyebrow=TextStyle(Font.SANS, 8.25, 10.0, p.accent, tracking=2.3, uppercase=True),
        heading=TextStyle(Font.DISPLAY, 29.25, 33.0, p.ink),
        body=TextStyle(Font.SANS, 10.85, 17.8, p.body),
        detail_title=TextStyle(Font.SERIF, 12.0, 15.0, p.ink),
        detail_text=TextStyle(Font.SANS, 9.7, 14.3, p.muted),
        folio=TextStyle(Font.SANS, 8.0, 10.0, p.faint, tracking=1.6, uppercase=True),
        cover_claim=TextStyle(Font.SERIF, 16.8, 24.0, p.on_dark),
        cover_label=TextStyle(Font.SANS, 8.25, 10.0, p.cover_highlight, tracking=2.85, uppercase=True),
        region=TextStyle(Font.SANS, 7.2, 9.0, p.ink, tracking=2.2, uppercase=True),
        lead=TextStyle(Font.SANS, 10.05, 15.7, p.on_dark_muted),
        contact=TextStyle(Font.SANS, 10.05, 18.0, p.on_dark),
        closing_title=TextStyle(Font.DISPLAY, 18.4, 22.0, p.on_dark),
        section_title=TextStyle(Font.DISPLAY, 112.0, 112.0, p.on_dark),
        product_name=TextStyle(Font.DISPLAY, 40.0, 42.0, p.ink),
        model_title=TextStyle(Font.DISPLAY, 72.0, 70.0, p.ink),
        photo_label=TextStyle(Font.SANS, 8.25, 10.0, p.ink, tracking=2.3, uppercase=True),
        spec_value=TextStyle(Font.SANS, 10.85, 16.0, p.ink),
        swatch_name=TextStyle(Font.SANS, 7.0, 9.0, p.muted),
        running_head=TextStyle(Font.SANS, 9.5, 11.0, p.ink, tracking=2.8, uppercase=True),
        label=TextStyle(Font.SANS, 7.2, 9.0, p.ink, tracking=2.2, uppercase=True),
        number=TextStyle(Font.DISPLAY, 11.0, 14.0, p.accent),
        small=TextStyle(Font.SANS, 7.8, 11.0, p.muted),
        text=TextStyle(Font.SANS, 9.6, 15.4, p.body),
        display_xl=TextStyle(Font.DISPLAY, 150.0, 140.0, p.on_dark),
        feature_title=TextStyle(Font.DISPLAY, 40.0, 42.0, p.on_dark),
        index_section=TextStyle(Font.DISPLAY, 22.0, 26.0, p.ink),
        index_entry=TextStyle(Font.SERIF, 11.5, 15.0, p.ink),
        map_city=TextStyle(Font.SERIF, 8.5, 10.0, p.ink),
        store_line=TextStyle(Font.SANS, 6.9, 9.0, p.body),
    )
    return Theme(palette=p, type=t, grid=Grid())
