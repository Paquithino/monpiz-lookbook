"""Small text helpers of the digital edition."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable

_NON_WORD = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """``"Grostè Uomo"`` -> ``"groste-uomo"``: ASCII, lower case, words joined by dashes."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return _NON_WORD.sub("-", ascii_text.lower()).strip("-") or "x"


def unique_slugs() -> Callable[[str], str]:
    """A slugify that never returns the same value twice (``falcade-cavallino-2`` ...)."""
    seen: dict[str, int] = {}

    def make(text: str) -> str:
        slug = slugify(text)
        seen[slug] = seen.get(slug, 0) + 1
        return slug if seen[slug] == 1 else f"{slug}-{seen[slug]}"

    return make


def phone_href(phone: str) -> str:
    """A ``tel:`` link for an Italian number written with spaces: ``0436 3320`` -> ``tel:+3904363320``."""
    digits = re.sub(r"[^\d+]", "", phone)
    if not digits.startswith("+"):
        digits = "+39" + digits
    return f"tel:{digits}"
