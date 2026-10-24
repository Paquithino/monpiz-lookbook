from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from monpiz_lookbook.images import ImageLibrary


@pytest.fixture
def studio_photo(tmp_path: Path) -> Path:
    """A 300x200 'studio shot': grey backdrop with a dark subject in the middle."""
    image = Image.new("RGB", (300, 200), (200, 200, 200))
    image.paste((20, 20, 20), (100, 60, 200, 180))
    image.save(tmp_path / "shot.png")
    return Path("shot.png")


@pytest.mark.parametrize(("width_pt", "height_pt"), [(600.0, 200.0), (300.0, 600.0)])
def test_bled_fills_slots_wider_or_taller_than_the_photo(
    tmp_path: Path, studio_photo: Path, width_pt: float, height_pt: float
) -> None:
    library = ImageLibrary(tmp_path, dpi=72)
    width, height = library.bled(studio_photo, width_pt, height_pt).getSize()
    assert width / height == pytest.approx(width_pt / height_pt, rel=0.01)


def test_bled_keeps_the_subject_whole_in_a_tall_slot(tmp_path: Path, studio_photo: Path) -> None:
    # The photo keeps its full width and sits at the bottom: the subject stays
    # intact and the new space above it is backdrop only.
    reader = ImageLibrary(tmp_path, dpi=72).bled(studio_photo, 300.0, 600.0)
    width, height = reader.getSize()
    image = Image.frombytes("RGB", (width, height), reader.getRGBData())
    assert image.getpixel((150, height - 80)) == (20, 20, 20)  # subject, near the bottom
    backdrop = image.getpixel((150, 50))
    assert isinstance(backdrop, tuple)
    assert backdrop[0] > 150  # extended backdrop above


def test_on_white_turns_a_grey_backdrop_white_and_keeps_the_subject(tmp_path: Path) -> None:
    # A studio shot whose backdrop is not quite white (as a studio floor often is).
    image = Image.new("RGB", (300, 200), (232, 232, 232))
    image.paste((20, 20, 20), (100, 60, 200, 180))
    image.save(tmp_path / "grey.png")

    reader = ImageLibrary(tmp_path, dpi=72).on_white(Path("grey.png"), 300.0, 200.0)
    width, height = reader.getSize()
    result = Image.frombytes("RGB", (width, height), reader.getRGBData())
    corner, subject = result.getpixel((2, 2)), result.getpixel((150, 120))
    assert isinstance(corner, tuple) and isinstance(subject, tuple)
    assert min(corner) >= 253  # backdrop and borders vanish in multiply mode
    assert max(subject) <= 40  # the product itself is untouched


def test_a_studio_shot_has_a_plain_backdrop(tmp_path: Path, studio_photo: Path) -> None:
    assert ImageLibrary(tmp_path, dpi=72).has_plain_backdrop(studio_photo)


def test_a_photo_taken_outdoors_is_cropped_not_extended(tmp_path: Path) -> None:
    # Random grain all the way to the edges, like rock or grass.
    noise = Image.effect_noise((300, 200), 60).convert("RGB")
    noise.save(tmp_path / "outdoor.png")
    library = ImageLibrary(tmp_path, dpi=72)
    assert not library.has_plain_backdrop(Path("outdoor.png"))
    width, height = library.filled(Path("outdoor.png"), 600.0, 200.0).getSize()
    assert width / height == pytest.approx(3.0, rel=0.01)


def test_only_the_edges_that_grow_are_inspected(tmp_path: Path) -> None:
    # Studio shot whose subject touches the right edge: fine when only the top is extended.
    image = Image.new("RGB", (300, 200), (200, 200, 200))
    image.paste(Image.effect_noise((60, 120), 60).convert("RGB"), (240, 80))
    image.save(tmp_path / "wide.png")
    library = ImageLibrary(tmp_path, dpi=72)
    assert not library.has_plain_backdrop(Path("wide.png"))  # all edges: the right one is busy
    width, height = library.filled(Path("wide.png"), 300.0, 300.0).getSize()  # taller slot: top grows
    assert width / height == pytest.approx(1.0, rel=0.01)
    assert (width, height) == (300, 300)  # extended (bled), not cropped down to 200 x 200
