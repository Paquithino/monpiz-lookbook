"""Shared page infrastructure: render context, page protocol, common header."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from reportlab.lib.colors import Color

from ..geometry import Box
from ..images import ImageLibrary
from ..surface import Align, Surface
from ..theme import TextStyle, Theme

EYEBROW_BASELINE = 48.5
PLACEHOLDER_TEXT = "Foto in arrivo"
HEADING_BASELINE = 90.0
LABEL_PROBE = (0.0, 0.0, 0.35, 0.15)  # top-left corner of a photo, where labels sit
DARK_PHOTO = 120.0  # mean grey level below which labels on a photo turn light


@dataclass(frozen=True, slots=True)
class RenderContext:
    theme: Theme
    images: ImageLibrary
    logo: Path
    logo_mask: Path


class Page(Protocol):
    @property
    def folio(self) -> str | None:
        """Running footer label, or ``None`` for pages without a footer."""
        ...

    def draw(self, surface: Surface, ctx: RenderContext) -> None: ...


def draw_header(
    surface: Surface,
    ctx: RenderContext,
    eyebrow: str,
    title: str,
    *,
    eyebrow_color: Color | None = None,
    title_color: Color | None = None,
) -> float:
    """Eyebrow label plus (possibly multi-line) heading. Returns the last baseline."""
    t, g = ctx.theme.type, ctx.theme.grid
    eyebrow_style = t.eyebrow.with_color(eyebrow_color) if eyebrow_color else t.eyebrow
    heading_style = t.heading.with_color(title_color) if title_color else t.heading
    surface.text(eyebrow, g.margin_x, EYEBROW_BASELINE, eyebrow_style)
    return surface.paragraph(title, g.margin_x, HEADING_BASELINE, g.content_width, heading_style)


def photo_label_style(
    ctx: RenderContext, photo: Path | None, probe: tuple[float, float, float, float] = LABEL_PROBE
) -> TextStyle:
    """Label style for text over the ``probe`` region of ``photo``: dark, or light on dark photos.

    Studio shots are light, but a photo taken outdoors can be dark there.
    By default the probe is the top-left corner, where labels usually sit.
    """
    style = ctx.theme.type.photo_label
    if photo is not None and ctx.images.luminance(photo, probe) < DARK_PHOTO:
        return style.with_color(ctx.theme.palette.on_dark)
    return style


def logo_height(ctx: RenderContext, width: float) -> float:
    px_w, px_h = ctx.images.size(ctx.logo_mask)
    return width * px_h / px_w


def draw_logo(surface: Surface, ctx: RenderContext, x: float, top: float, width: float, color: Color) -> None:
    """Draw the logo, ``width`` points wide, tinted with ``color``."""
    height = logo_height(ctx, width)
    surface.image(ctx.images.tinted(ctx.logo_mask, color, width, height), Box(x, top, width, height))


def draw_placeholder(surface: Surface, ctx: RenderContext, slot: Box) -> None:
    """Studio-grey box standing in for a photo that has not arrived yet."""
    t = ctx.theme.type
    surface.rect(slot, fill=ctx.theme.palette.studio)
    middle = slot.top + slot.height / 2
    surface.text(PLACEHOLDER_TEXT, slot.x + slot.width / 2, middle, t.photo_label, Align.CENTER)
