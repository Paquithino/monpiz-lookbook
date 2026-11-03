"""Loading and validation of the lookbook content."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from . import i18n
from .errors import ContentError
from .models import Lookbook


def _read_yaml(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except FileNotFoundError as exc:
        raise ContentError(f"File di contenuto non trovato: {path}") from exc
    except yaml.YAMLError as exc:
        raise ContentError(f"YAML non valido in {path}:\n{exc}") from exc


def _format_validation_error(path: Path, error: ValidationError) -> str:
    lines = [f"Contenuto non valido in {path}:"]
    for issue in error.errors():
        location = ".".join(str(part) for part in issue["loc"])
        lines.append(f"  - {location}: {issue['msg']}")
    return "\n".join(lines)


def load_lookbook(content_file: Path, assets_dir: Path, lang: str = i18n.DEFAULT) -> Lookbook:
    """Load ``content_file``, resolve the retailers source and validate everything.

    The ``retailers.source`` key is a loading concern: it names a YAML file,
    relative to ``content_file``, whose regions are merged into the model.
    In a language other than Italian the texts are translated with the
    dictionary next to ``content_file`` (``en.yaml``): see :mod:`i18n`.
    """
    raw = _read_yaml(content_file)
    if not isinstance(raw, dict):
        raise ContentError(f"{content_file} deve contenere una mappa YAML al livello radice")

    retailers = raw.get("retailers")
    if isinstance(retailers, dict) and "source" in retailers:
        source = content_file.parent / retailers.pop("source")
        retailers["regions"] = _read_yaml(source)

    try:
        lookbook = Lookbook.model_validate(raw)
    except ValidationError as exc:
        raise ContentError(_format_validation_error(content_file, exc)) from exc

    missing = sorted({str(p) for p in lookbook.asset_paths() if not (assets_dir / p).is_file()})
    if missing:
        listing = "\n".join(f"  - {name}" for name in missing)
        raise ContentError(f"Asset mancanti in {assets_dir}:\n{listing}")

    if lang == i18n.DEFAULT:
        return lookbook
    dictionary = i18n.load_dictionary(i18n.dictionary_path(content_file, lang))
    return Lookbook.model_validate(i18n.translate(lookbook.model_dump(), dictionary))


def untranslated(content_file: Path, assets_dir: Path, lang: str) -> list[str]:
    """Italian texts of the content with no translation in ``lang``'s dictionary."""
    lookbook = load_lookbook(content_file, assets_dir)
    dictionary = i18n.load_dictionary(i18n.dictionary_path(content_file, lang))
    return i18n.missing(lookbook.model_dump(), dictionary)
