"""Web fonts: the print fonts, subset to the characters of Italian text.

The TrueType files of ``assets/fonts`` are trimmed to Latin characters and
compressed as WOFF2 (WOFF when the ``brotli`` package is missing), from about
490 KB to well under 100 KB in total.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path

from fontTools import subset

from ..theme import Font

FONT_DIR = "fonts"
UNICODES = [
    *range(0x20, 0x7F),  # ASCII
    *range(0xA0, 0x180),  # Latin-1 and Latin Extended-A (à è é ì ò ù ß ö ...)
    0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x20AC, 0x2192,
]  # fmt: skip


@dataclass(frozen=True, slots=True)
class WebFont:
    family: str  # CSS font-family
    url: str
    format: str  # "woff2" or "woff"
    style: str = "normal"  # CSS font-style


FAMILIES = {
    Font.DISPLAY: ("Fraunces Display", "normal"),
    Font.DISPLAY_ITALIC: ("Fraunces Display", "italic"),
    Font.SERIF: ("Fraunces Text", "normal"),
    Font.SANS: ("Inter", "normal"),
}


def build_fonts(assets_dir: Path, site_dir: Path) -> list[WebFont]:
    flavor = "woff2" if importlib.util.find_spec("brotli") else "woff"
    out_dir = site_dir / FONT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    fonts = []
    for font, (family, style) in FAMILIES.items():
        source = assets_dir / "fonts" / f"{font.value}.ttf"
        target = out_dir / f"{font.value}.{flavor}"
        if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
            options = subset.Options()
            options.flavor = flavor
            options.layout_features = ["*"]
            options.name_IDs = ["*"]
            loaded = subset.load_font(str(source), options)
            subsetter = subset.Subsetter(options)
            subsetter.populate(unicodes=UNICODES)
            subsetter.subset(loaded)
            subset.save_font(loaded, str(target), options)
        fonts.append(WebFont(family, f"{FONT_DIR}/{target.name}", flavor, style))
    return fonts
