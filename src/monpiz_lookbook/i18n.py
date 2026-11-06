"""Languages of the lookbook: the fixed words of the layout and the content translations.

The lookbook is written in Italian. For another language two things change:

* the fixed words of the layout ("Colori", "Taglie", "Indice" ...), translated
  here in ``UI``;
* the content of ``lookbook.yaml``, translated by a dictionary next to it
  (``content/en.yaml``): pairs of Italian text and its translation, plus the
  texts that stay the same (model names, colour names such as "Alabama").

Photos, colours, sizes and retailers stay in ``lookbook.yaml`` only, so the
two editions never drift apart. A text with no translation stays in Italian
and ``monpiz-lookbook check --lang en`` lists it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .errors import ContentError

DEFAULT = "it"
LANGUAGES = {"it": "Italiano", "en": "English"}
LOCALES = {"it": "it_IT", "en": "en_GB"}

UI: dict[str, dict[str, str]] = {
    "en": {
        # print and web
        "Colori": "Colours",
        "%d colori": "%d colours",
        "Taglie": "Sizes",
        "Materiali": "Materials",
        "Indice": "Contents",
        "Collezione": "Collection",
        "Il modello": "The model",
        "modello": "model",
        "modelli": "models",
        "Dettaglio": "Detail",
        "Foto in arrivo": "Photo coming soon",
        "Anche in: ": "Also in: ",
        "Email": "Email",
        "Telefono": "Phone",
        "Telefono e WhatsApp": "Phone & WhatsApp",
        "Tel. · WhatsApp": "Tel. · WhatsApp",
        "Chiama": "Call",
        "Scrivi su WhatsApp": "Message on WhatsApp",
        "Sito": "Website",
        "Instagram": "Instagram",
        # web only
        "Seguici su Instagram": "Follow us on Instagram",
        "Scorri per sfogliare": "Scroll to browse",
        "Copertina": "Cover",
        "Pagina": "Page",
        "Pagine": "Pages",
        "Pagina precedente": "Previous page",
        "Pagina successiva": "Next page",
        "Tutte le pagine": "All pages",
        "Chiudi": "Close",
        "Lingua": "Language",
        "modello %d di %d": "model %d of %d",
        "Mappa dei rivenditori": "Map of the retailers",
        "Tocca un punto per aprire il negozio; i numeri raccolgono i negozi vicini. "
        "L'elenco completo è qui sotto.": "Tap a dot to open the store; numbers group stores close "
        "to each other. The full list is below.",
        "%d negozi": "%d stores",
        "Mappa": "Map",
        "(segue)": "(cont.)",
        "Acquista online": "Shop online",
        "(in foto)": "(pictured)",
    }
}

_current = [DEFAULT]


def set_language(lang: str) -> None:
    """Language of the fixed words for the rest of the build."""
    if lang not in LANGUAGES:
        raise ContentError(f"Lingua sconosciuta: {lang} (disponibili: {', '.join(LANGUAGES)})")
    _current[0] = lang


def language() -> str:
    return _current[0]


def tr(text: str) -> str:
    """A fixed word of the layout in the current language (the Italian text is the key)."""
    return UI.get(_current[0], {}).get(text, text)


# --- content -------------------------------------------------------------------------------------


def _norm(text: str) -> str:
    return " ".join(text.split())


@dataclass(frozen=True, slots=True)
class Dictionary:
    """Italian text -> translation, plus the texts that stay as they are."""

    pairs: dict[str, str] = field(default_factory=dict)
    keep: frozenset[str] = frozenset()

    def get(self, text: str) -> str | None:
        key = _norm(text)
        if key in self.pairs:
            return self.pairs[key]
        return text if key in self.keep else None


def dictionary_path(content_file: Path, lang: str) -> Path:
    return content_file.parent / f"{lang}.yaml"


def load_dictionary(path: Path) -> Dictionary:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except FileNotFoundError as exc:
        raise ContentError(f"File delle traduzioni non trovato: {path}") from exc
    except yaml.YAMLError as exc:
        raise ContentError(f"YAML non valido in {path}:\n{exc}") from exc
    if not isinstance(raw, dict):
        raise ContentError(f"{path} deve contenere le chiavi 'keep' e 'translations'")
    pairs: dict[str, str] = {}
    for number, item in enumerate(raw.get("translations") or [], start=1):
        if not isinstance(item, dict) or not item.get("it") or not item.get("en"):
            raise ContentError(f"{path}, traduzione n. {number}: servono sia 'it' sia 'en'")
        pairs[_norm(str(item["it"]))] = _norm(str(item["en"]))
    keep = frozenset(_norm(str(text)) for text in raw.get("keep") or [])
    return Dictionary(pairs, keep)


# Texts never translated: addresses, links and the contacts of the back cover.
_UNTRANSLATED = ("author", "address", "phone", "shop", "url", "contacts", "path", "image", "photo")


def _walk(value: Any, key: str, visit: Any) -> Any:
    if isinstance(value, dict):
        if "stores" in value:  # retailers: only the region name is translated
            return {**value, "region": _walk(value.get("region"), "region", visit)}
        return {k: _walk(v, k, visit) for k, v in value.items()}
    if isinstance(value, list):
        return [_walk(v, key, visit) for v in value]
    if isinstance(value, str) and value.strip() and key not in _UNTRANSLATED:
        return visit(value)
    return value


def translate(data: dict[str, Any], dictionary: Dictionary) -> dict[str, Any]:
    """The content (as plain data) with every known text translated; the rest unchanged."""
    return _walk(data, "", lambda text: dictionary.get(text) or text)  # type: ignore[no-any-return]


def missing(data: dict[str, Any], dictionary: Dictionary) -> list[str]:
    """Texts of the content with neither a translation nor a place in ``keep``, in order."""
    found: list[str] = []

    def visit(text: str) -> str:
        if dictionary.get(text) is None and _norm(text) not in found:
            found.append(_norm(text))
        return text

    _walk(data, "", visit)
    return found
