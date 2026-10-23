"""Content schema of the lookbook.

The YAML files in ``content/`` are validated against these models. They are
strict (unknown keys are rejected) so that a typo in the content fails loudly
instead of silently disappearing from the printed catalogue.
Image paths are kept relative to the assets directory; :mod:`content`
checks that they exist.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Meta(_Model):
    title: Text
    author: Text
    subject: Text = ""


class Identity(_Model):
    logo: Path  # full-colour logo, for light backgrounds
    logo_mask: Path  # single-colour silhouette, tinted for dark backgrounds


class Cover(_Model):
    tagline: Text
    claim: Text
    highlights: list[Text] = Field(default_factory=list, max_length=4)
    photo: Path  # product shot on a white backdrop


class ImageRef(_Model):
    path: Path
    focus_y: float = Field(0.5, ge=0.0, le=1.0, description="Vertical focal point for cropping")


class Detail(_Model):
    name: Text
    description: Text
    image: Path


class Brand(_Model):
    eyebrow: Text
    title: Text
    folio: Text
    paragraphs: list[Text] = Field(min_length=1, max_length=2)
    banner: ImageRef
    details_title: Text
    details: list[Detail] = Field(min_length=1, max_length=4)


class Variant(_Model):
    """A colourway of a product. Without ``image`` the page shows a placeholder."""

    color: Text
    image: Path | None = None


class Product(_Model):
    name: Text
    description: Text
    sizes: Text | None = None
    variants: list[Variant] = Field(min_length=1, max_length=4)


class Material(_Model):
    """A material a model is offered in. Without ``image`` the page shows a placeholder."""

    name: Text
    image: Path | None = None


class ShoeModel(_Model):
    """A shoe model (Cortina, Falcade): an introduction page, then its products."""

    name: Text
    description: Text
    image: Path | None = Field(None, description="Hero photo; a placeholder until provided")
    materials: list[Material] = Field(default_factory=list, max_length=4)
    products: list[Product] = Field(default_factory=list)


class Section(_Model):
    """A part of the lookbook (Donna, Uomo): a divider page, then its models."""

    name: Text
    eyebrow: Text = "Collezione"
    intro: str = ""
    models: list[ShoeModel] = Field(min_length=1)

    @property
    def products(self) -> list[Product]:
        """Every product of the section, in page order."""
        return [product for model in self.models for product in model.products]


class Store(_Model):
    name: Text
    address: Text  # full postal address, or just the country for stores abroad
    phone: Text | None = None
    shop: Text | None = None  # URL of the store's online shop

    @property
    def maps_url(self) -> str:
        query = quote(f"{self.name} {self.address}")
        return f"https://www.google.com/maps/search/?api=1&query={query}"


class Region(_Model):
    region: Text
    stores: list[Store] = Field(min_length=1)


class Retailers(_Model):
    eyebrow: Text
    title: Text
    intro: str = ""
    regions: list[Region] = Field(min_length=1)


class Closing(_Model):
    title: Text
    text: Text
    contacts: list[list[Text]] = Field(default_factory=list)


class Lookbook(_Model):
    meta: Meta
    identity: Identity
    cover: Cover
    brand: Brand
    sections: list[Section] = Field(min_length=1)
    retailers: Retailers | None = None
    closing: Closing | None = None

    def asset_paths(self) -> Iterator[Path]:
        """Yield every asset referenced by the content (relative paths)."""
        yield self.identity.logo
        yield self.identity.logo_mask
        yield self.cover.photo
        yield self.brand.banner.path
        yield from (detail.image for detail in self.brand.details)
        for section in self.sections:
            for model in section.models:
                if model.image is not None:
                    yield model.image
                yield from (m.image for m in model.materials if m.image is not None)
                for product in model.products:
                    yield from (v.image for v in product.variants if v.image is not None)
