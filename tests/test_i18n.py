from collections.abc import Iterator
from pathlib import Path

import pytest

from monpiz_lookbook import i18n
from monpiz_lookbook.content import load_lookbook, untranslated

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def italian_afterwards() -> Iterator[None]:
    yield
    i18n.set_language(i18n.DEFAULT)


def test_fixed_words_follow_the_language() -> None:
    assert i18n.tr("Colori") == "Colori"
    i18n.set_language("en")
    assert i18n.tr("Colori") == "Colours"
    assert i18n.tr("%d colori") % 12 == "12 colours"
    assert i18n.tr("una parola sconosciuta") == "una parola sconosciuta"


def test_texts_are_matched_ignoring_spaces_and_line_breaks() -> None:
    dictionary = i18n.Dictionary({"una pedula bassa": "a low boot"}, frozenset({"Cortina"}))
    data = {"name": "Cortina", "description": "Una  pedula\n bassa".lower(), "url": "una pedula bassa"}
    assert i18n.translate(data, dictionary) == {
        "name": "Cortina",
        "description": "a low boot",
        "url": "una pedula bassa",  # links are never translated
    }


def test_untranslated_texts_are_listed_once() -> None:
    dictionary = i18n.Dictionary({"Donna": "Women"})
    data = {
        "sections": [{"name": "Donna", "eyebrow": "Collezione"}, {"name": "Uomo", "eyebrow": "Collezione"}]
    }
    assert i18n.missing(data, dictionary) == ["Collezione", "Uomo"]


def test_store_names_and_addresses_stay_as_they_are() -> None:
    dictionary = i18n.Dictionary({"Lombardia": "Lombardy", "Bulli e Pupe": "x"})
    region = {"region": "Lombardia", "stores": [{"name": "Bulli e Pupe", "address": "Malé"}]}
    assert i18n.translate({"regions": [region]}, dictionary)["regions"][0] == {**region, "region": "Lombardy"}


def test_unknown_language_is_refused() -> None:
    with pytest.raises(Exception, match="Lingua sconosciuta"):
        i18n.set_language("xx")


@pytest.mark.skipif(not (ROOT / "content" / "en.yaml").is_file(), reason="no English dictionary")
def test_the_english_dictionary_covers_the_lookbook() -> None:
    content, assets = ROOT / "content" / "lookbook.yaml", ROOT / "assets"
    assert untranslated(content, assets, "en") == []
    english = load_lookbook(content, assets, "en")
    assert english.sections[0].name == "Women"
