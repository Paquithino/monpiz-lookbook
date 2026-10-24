from __future__ import annotations

import pytest
from pydantic import ValidationError

from monpiz_lookbook.models import MAX_COLORS, Product


def _product(variants: int, colors: int) -> Product:
    return Product.model_validate(
        {
            "name": "Cortina Suede",
            "description": "Suede morbido.",
            "variants": [{"color": f"Colore {i}"} for i in range(variants)],
            "colors": [{"name": f"Colore {i}"} for i in range(colors)],
        }
    )


def test_a_colour_card_goes_with_one_master_photo() -> None:
    product = _product(variants=1, colors=13)
    assert product.master.color == "Colore 0"


def test_a_colour_card_rejects_several_photos() -> None:
    with pytest.raises(ValidationError, match="foto master"):
        _product(variants=2, colors=3)


def test_the_colour_card_has_a_maximum() -> None:
    with pytest.raises(ValidationError):
        _product(variants=1, colors=MAX_COLORS + 1)
