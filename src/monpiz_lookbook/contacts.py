"""Contacts of the back cover, recognised from how they are written.

``monpiz@monpiz.it`` is an e-mail, ``+39 335 ...`` a phone number,
also reachable on WhatsApp, ``instagram.com/monpiz_official`` the Instagram profile (shown as
``@monpiz_official``), any other address the web site. Print and web lay them
out the same way: a small label above each value.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from .i18n import tr

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)
_PHONE = re.compile(r"^\+?[\d\s]{6,}$")
_WEB = re.compile(r"^(https?://)?[\w-]+(\.[\w-]+)+(/\S*)?$", re.IGNORECASE)


def phone_href(phone: str) -> str:
    """A ``tel:`` link for an Italian number written with spaces: ``0436 3320`` -> ``tel:+3904363320``."""
    digits = re.sub(r"[^\d+]", "", phone)
    if not digits.startswith("+"):
        digits = "+39" + digits
    return f"tel:{digits}"


def whatsapp_href(phone: str) -> str:
    """A WhatsApp chat with the number: ``+39 335 760 4522`` -> ``https://wa.me/393357604522``."""
    return "https://wa.me/" + phone_href(phone).removeprefix("tel:+")


@dataclass(frozen=True, slots=True)
class Contact:
    text: str  # as shown: "@monpiz_official", "monpiz.it"
    href: str | None
    kind: str = "text"  # email, phone, instagram, web, text
    label: str = ""  # "Email", "Telefono e WhatsApp", "Instagram", "Sito"
    whatsapp: str | None = None  # phone numbers: the same number on WhatsApp


def contact(text: str) -> Contact:
    """A contact line with its kind, label and link."""
    text = text.strip()
    if _EMAIL.match(text):
        return Contact(text, f"mailto:{text}", "email", tr("Email"))
    if _PHONE.match(text):
        return Contact(text, phone_href(text), "phone", tr("Telefono e WhatsApp"), whatsapp_href(text))
    if _WEB.match(text):
        href = text if text.startswith("http") else f"https://{text}"
        parts = urlsplit(href)
        host = parts.netloc.removeprefix("www.")
        path = parts.path.strip("/")
        if host == "instagram.com" and path:
            return Contact(f"@{path.split('/')[0]}", href, "instagram", tr("Instagram"))
        shown = host + (f"/{path}" if path else "")
        return Contact(shown, href, "web", tr("Sito"))
    return Contact(text, None)


def contact_list(rows: list[list[str]]) -> list[Contact]:
    """All the contacts of the back cover, in reading order, rows flattened."""
    return [contact(item) for row in rows for item in row if item.strip()]
