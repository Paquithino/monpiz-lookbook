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
    card: Color
    card_border: Color
    # Dark pages (cover and retailers)
    forest: Color
    olive: Color
    on_dark: Color
    on_dark_muted: Color
    on_dark_accent: Color
    cover_accent: Color
    cover_highlight: Color
    olive_rule: Color
    tree_shadow: Color
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


@dataclass(frozen=True, slots=True)
class Typography:
    eyebrow: TextStyle
    heading: TextStyle
    body: TextStyle
    detail_title: TextStyle
    detail_text: TextStyle
    folio: TextStyle
    cover_title: TextStyle
    cover_claim: TextStyle
    cover_label: TextStyle
    region: TextStyle
    store: TextStyle
    lead: TextStyle
    contact: TextStyle
    closing_title: TextStyle
    section_title: TextStyle
    product_name: TextStyle
    photo_label: TextStyle
    spec_value: TextStyle


@dataclass(frozen=True, slots=True)
class Grid:
    """Page geometry shared by every page."""

    width: float = A4[0]
    height: float = A4[1]
    margin_x: float = 42.0
    margin_top: float = 36.0
    folio_baseline: float = 799.5
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
        card=HexColor("#FFFDF8"),
        card_border=HexColor("#DDD8C6"),
        forest=HexColor("#24291F"),
        olive=HexColor("#52541F"),
        on_dark=HexColor("#FFFDF8"),
        on_dark_muted=HexColor("#E2E0C6"),
        on_dark_accent=HexColor("#CDD08A"),
        cover_accent=HexColor("#A8AB5C"),
        cover_highlight=HexColor("#C9C6AC"),
        olive_rule=HexColor("#82835B"),
        tree_shadow=HexColor("#10130D"),
        studio=HexColor("#C9C8C5"),  # photo backdrop, used for placeholders
    )
    t = Typography(
        eyebrow=TextStyle(Font.SANS, 8.25, 10.0, p.accent, tracking=2.3, uppercase=True),
        heading=TextStyle(Font.DISPLAY, 29.25, 33.0, p.ink),
        body=TextStyle(Font.SANS, 10.85, 17.8, p.body),
        detail_title=TextStyle(Font.SERIF, 12.0, 15.0, p.ink),
        detail_text=TextStyle(Font.SANS, 9.7, 14.3, p.muted),
        folio=TextStyle(Font.SANS, 8.0, 10.0, p.faint, tracking=1.6, uppercase=True),
        cover_title=TextStyle(Font.DISPLAY, 44.0, 48.0, p.on_dark),
        cover_claim=TextStyle(Font.SERIF, 16.8, 24.0, p.on_dark),
        cover_label=TextStyle(Font.SANS, 8.25, 10.0, p.cover_highlight, tracking=2.85, uppercase=True),
        region=TextStyle(Font.SERIF, 10.5, 12.0, p.on_dark_accent),
        store=TextStyle(Font.SANS, 8.55, 14.5, p.on_dark),
        lead=TextStyle(Font.SANS, 10.05, 15.7, p.on_dark_muted),
        contact=TextStyle(Font.SANS, 10.05, 18.0, p.on_dark),
        closing_title=TextStyle(Font.DISPLAY, 18.4, 22.0, p.on_dark),
        section_title=TextStyle(Font.DISPLAY, 112.0, 112.0, p.on_dark),
        product_name=TextStyle(Font.DISPLAY, 34.0, 38.0, p.ink),
        photo_label=TextStyle(Font.SANS, 8.25, 10.0, p.ink, tracking=2.3, uppercase=True),
        spec_value=TextStyle(Font.SANS, 10.85, 16.0, p.ink),
    )
    return Theme(palette=p, type=t, grid=Grid())
