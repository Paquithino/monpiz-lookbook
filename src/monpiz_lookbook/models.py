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

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Meta(_Model):
    title: Text
    author: Text
    subject: Text = ""


class Identity(_Model):
    logo_mask: Path


class Cover(_Model):
    tagline: Text
    title: Text
    claim: Text
    highlights: list[Text] = Field(default_factory=list, max_length=4)
    background_mask: Path


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
    line: Text | None = Field(None, description="Model family, e.g. Cortina")
    description: Text
    sizes: Text | None = None
    variants: list[Variant] = Field(min_length=1, max_length=2)


class Section(_Model):
    """A part of the lookbook (Donna, Uomo): a divider page, then one page per product."""

    name: Text
    eyebrow: Text = "Collezione"
    intro: str = ""
    products: list[Product] = Field(min_length=1)


class Store(_Model):
    name: Text
    city: Text
    province: Text | None = None

    @property
    def label(self) -> str:
        place = f"{self.city} {self.province}" if self.province else self.city
        return f"{self.name} — {place}"


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

    @model_validator(mode="after")
    def _retailers_and_closing_together(self) -> Lookbook:
        # They share the last page: one without the other has nowhere to go.
        if (self.retailers is None) != (self.closing is None):
            raise ValueError("retailers e closing vanno indicati insieme (stessa pagina)")
        return self

    def asset_paths(self) -> Iterator[Path]:
        """Yield every asset referenced by the content (relative paths)."""
        yield self.identity.logo_mask
        yield self.cover.background_mask
        yield self.brand.banner.path
        yield from (detail.image for detail in self.brand.details)
        for section in self.sections:
            for product in section.products:
                yield from (v.image for v in product.variants if v.image is not None)
